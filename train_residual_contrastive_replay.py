from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from torch_geometric.loader import DataLoader

from build_residual_contrastive_replay_manifest import contrastive_group_count, positive_instance_count
from train_residual_elite_replay import (
    enforce_full_manifest_training,
    enforce_manifest_provenance,
    enforce_manifest_sampling_protocol,
    enforce_positive_floor,
    parse_expected_sample_seeds,
)
from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
import src.policy.policy as policy
from src.policy.evaluate import sample_var_params


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_manifest(path: Path, limit_rows: int = 0) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"cnf_path", "sample_seed", "num_samples_generated", "sample_id", "target_label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Contrastive manifest is missing columns: {sorted(missing)}")
    if limit_rows > 0:
        frame = frame.head(limit_rows).copy()
    if frame.empty:
        raise ValueError(f"Contrastive manifest has no rows: {path}")
    labels = set(pd.to_numeric(frame["target_label"], errors="coerce").dropna().astype(int))
    if not labels <= {0, 1}:
        raise ValueError(f"Contrastive manifest has invalid target labels: {sorted(labels)}")
    return frame


def enforce_contrastive_floor(manifest: pd.DataFrame, min_positive_instances: int, label: str) -> None:
    enforce_positive_floor(manifest[manifest["target_label"].astype(int).eq(1)], min_positive_instances, label)
    groups = contrastive_group_count(manifest)
    if groups < min_positive_instances:
        raise ValueError(
            f"{label} contrastive replay manifest has too few contrastive groups: "
            f"{groups} < {min_positive_instances}."
        )


def reconstruct_manifest_data(
    manifest: pd.DataFrame,
    model: torch.nn.Module,
    transform,
    scale_sigma: float,
    device: str,
) -> list:
    data_list = []
    instance_keys = sorted(
        {
            (str(row.family), int(row.size), str(row.file_key))
            for row in manifest[["family", "size", "file_key"]].drop_duplicates().itertuples(index=False)
        }
    )
    group_ids = {key: idx for idx, key in enumerate(instance_keys)}
    group_columns = ["cnf_path", "sample_seed", "num_samples_generated"]
    for (_, sample_seed, num_samples), group in manifest.groupby(group_columns, sort=False):
        cnf_path = Path(str(group.iloc[0]["cnf_path"]))
        if not cnf_path.exists():
            raise FileNotFoundError(cnf_path)
        set_seed(int(sample_seed))
        dataset = DimacsCNFDataset(str(cnf_path), transform=transform, lazy=True)
        loader = DataLoader(dataset=dataset, batch_size=1, num_workers=0, shuffle=False)
        sampled = sample_var_params(
            model=model,
            loader=loader,
            num_samples=int(num_samples),
            device=device,
            use_mode=False,
            scale_sigma=scale_sigma,
        )
        if len(sampled) != 1:
            raise RuntimeError(f"Expected one reconstructed graph for {cnf_path}, got {len(sampled)}")
        base = sampled[0]
        for _, row in group.iterrows():
            sample_id = int(row["sample_id"])
            if sample_id < 0 or sample_id >= int(num_samples):
                raise ValueError(f"sample_id={sample_id} outside reconstructed sample count {num_samples}")
            data = copy.deepcopy(base)
            data["var"].var_params = base["var"].var_params[:, sample_id : sample_id + 1, :].contiguous()
            data.source_log_prob = base.log_prob[sample_id : sample_id + 1].contiguous()
            data.target_label = torch.tensor([float(row["target_label"])], dtype=torch.float32)
            instance_key = (str(row["family"]), int(row["size"]), str(row["file_key"]))
            data.contrastive_group_id = torch.tensor([group_ids[instance_key]], dtype=torch.long)
            data.instance_key = f"{instance_key[0]}/{instance_key[1]}/{instance_key[2]}"
            data.sample_role = str(row.get("sample_role", ""))
            data.sample_cpu_time = torch.tensor([float(row.get("CPU time", float("nan")))], dtype=torch.float32)
            data_list.append(data)
    if not data_list:
        raise ValueError("No contrastive samples reconstructed.")
    return data_list


def graph_counts(var_batch: torch.Tensor, expected_graphs: int) -> torch.Tensor:
    counts = torch.bincount(var_batch, minlength=expected_graphs).float()
    return counts.clamp_min(1.0)


def batch_log_prob_and_kl(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    data,
    scale_sigma: float,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    data = data.to(device)
    y_var = model(data)
    with torch.no_grad():
        y_var_ref = ref_model(data)
    var_params = data["var"].var_params.transpose(0, 1).float()
    var_batch = data["lit"].batch[0::2]
    log_prob = policy.log_prob(y_var.float(), var_params, var_batch, scale_sigma=scale_sigma).squeeze(0)
    counts = graph_counts(var_batch, expected_graphs=log_prob.shape[0]).to(log_prob.device)
    log_prob_per_var = log_prob / counts
    if not hasattr(data, "source_log_prob"):
        raise ValueError("Contrastive replay batch is missing source_log_prob.")
    source_log_prob = data.source_log_prob.float().to(log_prob_per_var.device).view(-1)
    source_log_prob_per_var = source_log_prob / counts
    delta_log_prob_per_var = log_prob_per_var - source_log_prob_per_var
    kl_div = policy.kl_div(y_var.float(), y_var_ref.float(), var_batch, scale_sigma=scale_sigma)
    kl_per_var = kl_div / counts
    labels = data.target_label.float().to(log_prob_per_var.device).view(-1)
    if hasattr(data, "contrastive_group_id"):
        group_ids = data.contrastive_group_id.long().to(log_prob_per_var.device).view(-1)
    else:
        group_ids = torch.arange(labels.numel(), dtype=torch.long, device=log_prob_per_var.device)
    return log_prob_per_var, delta_log_prob_per_var, kl_per_var, labels, group_ids


def pairwise_margin_stats(
    score: torch.Tensor,
    labels: torch.Tensor,
    margin: float,
    group_ids: torch.Tensor | None = None,
) -> tuple[torch.Tensor, int]:
    if group_ids is None:
        group_ids = torch.zeros_like(labels, dtype=torch.long)
    losses = []
    active_groups = 0
    for group_id in torch.unique(group_ids):
        mask = group_ids == group_id
        positives = score[mask & (labels > 0.5)]
        negatives = score[mask & (labels <= 0.5)]
        if positives.numel() == 0 or negatives.numel() == 0:
            continue
        diffs = positives.view(-1, 1) - negatives.view(1, -1)
        losses.append(torch.nn.functional.softplus(float(margin) - diffs).mean())
        active_groups += 1
    if not losses:
        return score.new_tensor(0.0), 0
    return torch.stack(losses).mean(), active_groups


def pairwise_margin_loss(
    log_prob: torch.Tensor,
    labels: torch.Tensor,
    margin: float,
    group_ids: torch.Tensor | None = None,
) -> torch.Tensor:
    loss, _ = pairwise_margin_stats(log_prob, labels, margin=margin, group_ids=group_ids)
    return loss


def contrastive_score(
    log_prob_per_var: torch.Tensor,
    delta_log_prob_per_var: torch.Tensor,
    score_mode: str,
) -> torch.Tensor:
    if score_mode == "delta_log_prob":
        return delta_log_prob_per_var
    if score_mode == "log_prob":
        return log_prob_per_var
    raise ValueError(f"Unknown contrastive score mode: {score_mode}")


def batch_objective(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    data,
    scale_sigma: float,
    device: str,
    kl_penalty: float,
    bce_weight: float,
    pairwise_weight: float,
    margin: float,
    score_mode: str,
) -> tuple[torch.Tensor, dict[str, float]]:
    log_prob, delta_log_prob, kl, labels, group_ids = batch_log_prob_and_kl(
        model=model,
        ref_model=ref_model,
        data=data,
        scale_sigma=scale_sigma,
        device=device,
    )
    score = contrastive_score(log_prob, delta_log_prob, score_mode=score_mode)
    signed = (labels * 2.0) - 1.0
    bce_like = -(signed * score).mean()
    ranking, active_groups = pairwise_margin_stats(score, labels, margin=margin, group_ids=group_ids)
    kl_mean = kl.mean()
    loss = float(bce_weight) * bce_like + float(pairwise_weight) * ranking + float(kl_penalty) * kl_mean
    metrics = {
        "loss": float(loss.detach().cpu()),
        "bce_like": float(bce_like.detach().cpu()),
        "pairwise": float(ranking.detach().cpu()),
        "active_pairwise_groups": float(active_groups),
        "kl_per_var": float(kl_mean.detach().cpu()),
        "positive_log_prob": float(log_prob[labels > 0.5].mean().detach().cpu()) if (labels > 0.5).any() else float("nan"),
        "negative_log_prob": float(log_prob[labels <= 0.5].mean().detach().cpu()) if (labels <= 0.5).any() else float("nan"),
        "positive_score": float(score[labels > 0.5].mean().detach().cpu()) if (labels > 0.5).any() else float("nan"),
        "negative_score": float(score[labels <= 0.5].mean().detach().cpu()) if (labels <= 0.5).any() else float("nan"),
    }
    return loss, metrics


def group_data(data_list: list) -> list[list]:
    groups: dict[int, list] = {}
    for data in data_list:
        if not hasattr(data, "contrastive_group_id"):
            raise ValueError("Contrastive replay data is missing contrastive_group_id.")
        group_id = int(data.contrastive_group_id.view(-1)[0])
        groups.setdefault(group_id, []).append(data)
    return [groups[group_id] for group_id in sorted(groups)]


def grouped_batches(groups: list[list], max_samples: int, shuffle: bool, rng: random.Random) -> list[list]:
    if max_samples <= 0:
        raise ValueError("batch_size must be positive.")
    order = list(range(len(groups)))
    if shuffle:
        rng.shuffle(order)
    batches: list[list] = []
    current: list = []
    for idx in order:
        group = groups[idx]
        if current and len(current) + len(group) > max_samples:
            batches.append(current)
            current = []
        current.extend(group)
    if current:
        batches.append(current)
    return batches


def evaluate(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    data_list: list,
    batch_size: int,
    scale_sigma: float,
    device: str,
    kl_penalty: float,
    bce_weight: float,
    pairwise_weight: float,
    margin: float,
    score_mode: str,
) -> dict[str, float]:
    groups = group_data(data_list)
    batches = grouped_batches(groups, max_samples=batch_size, shuffle=False, rng=random.Random(0))
    model.eval()
    rows = []
    with torch.no_grad():
        for batch in batches:
            data = next(iter(DataLoader(dataset=batch, batch_size=len(batch), num_workers=0, shuffle=False)))
            _, metrics = batch_objective(
                model=model,
                ref_model=ref_model,
                data=data,
                scale_sigma=scale_sigma,
                device=device,
                kl_penalty=kl_penalty,
                bce_weight=bce_weight,
                pairwise_weight=pairwise_weight,
                margin=margin,
                score_mode=score_mode,
            )
            rows.append(metrics)
    return {
        key: float(np.nanmean([row[key] for row in rows]))
        for key in [
            "loss",
            "bce_like",
            "pairwise",
            "active_pairwise_groups",
            "kl_per_var",
            "positive_log_prob",
            "negative_log_prob",
            "positive_score",
            "negative_score",
        ]
    }


def save_training_config(
    args: argparse.Namespace,
    model_cfg,
    model_dir: Path,
    train_manifest: pd.DataFrame,
    dev_manifest: pd.DataFrame | None,
) -> None:
    cfg = OmegaConf.create(OmegaConf.to_container(model_cfg, resolve=True))
    cfg.model_name = model_dir.name
    cfg.model_dir = str(model_dir)
    cfg.from_checkpoint = str(args.checkpoint)
    cfg.contrastive_replay = {
        "train_manifest": str(args.train_manifest),
        "train_manifest_sha256": file_sha256(args.train_manifest),
        "dev_manifest": str(args.dev_manifest) if args.dev_manifest else "",
        "dev_manifest_sha256": file_sha256(args.dev_manifest) if args.dev_manifest else "",
        "source_checkpoint_sha256": file_sha256(args.checkpoint),
        "train_rows": int(len(train_manifest)),
        "train_positive_instances": int(positive_instance_count(train_manifest)),
        "train_contrastive_groups": int(contrastive_group_count(train_manifest)),
        "dev_rows": int(len(dev_manifest)) if dev_manifest is not None else 0,
        "dev_positive_instances": int(positive_instance_count(dev_manifest)) if dev_manifest is not None else 0,
        "dev_contrastive_groups": int(contrastive_group_count(dev_manifest)) if dev_manifest is not None else 0,
        "min_train_positive_instances": int(args.min_train_positive_instances),
        "min_dev_positive_instances": int(args.min_dev_positive_instances),
        "expected_train_split": str(args.expected_train_split),
        "expected_dev_split": str(args.expected_dev_split),
        "expected_train_sample_seeds": str(args.expected_train_sample_seeds),
        "expected_dev_sample_seeds": str(args.expected_dev_sample_seeds),
        "expected_train_num_samples": int(args.expected_train_num_samples),
        "expected_dev_num_samples": int(args.expected_dev_num_samples),
        "limit_train_rows": int(args.limit_train_rows),
        "limit_dev_rows": int(args.limit_dev_rows),
        "allow_partial_manifest_training": bool(args.allow_partial_manifest_training),
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
        "lr": float(args.lr),
        "weight_decay": float(args.weight_decay),
        "kl_penalty": float(args.kl_penalty),
        "bce_weight": float(args.bce_weight),
        "pairwise_weight": float(args.pairwise_weight),
        "margin": float(args.margin),
        "score_mode": str(args.score_mode),
        "scale_sigma": float(args.scale_sigma),
        "seed": int(args.seed),
    }
    OmegaConf.save(cfg, model_dir / "config.yaml")


def save_model(model: torch.nn.Module, model_dir: Path, name: str) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_dir / f"{name}.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finetune March policy with residual contrastive replay.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--dev-manifest", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--kl-penalty", type=float, default=0.05)
    parser.add_argument("--bce-weight", type=float, default=0.5)
    parser.add_argument("--pairwise-weight", type=float, default=1.0)
    parser.add_argument("--margin", type=float, default=0.02)
    parser.add_argument("--score-mode", choices=["delta_log_prob", "log_prob"], default="delta_log_prob")
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--scale-sigma", type=float, default=-1.0)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=1745)
    parser.add_argument("--limit-train-rows", type=int, default=0)
    parser.add_argument("--limit-dev-rows", type=int, default=0)
    parser.add_argument("--min-train-positive-instances", type=int, default=0)
    parser.add_argument("--min-dev-positive-instances", type=int, default=0)
    parser.add_argument("--expected-train-split", default="residual_train")
    parser.add_argument("--expected-dev-split", default="residual_dev")
    parser.add_argument("--expected-train-sample-seeds", default="")
    parser.add_argument("--expected-dev-sample-seeds", default="")
    parser.add_argument("--expected-train-num-samples", type=int, default=0)
    parser.add_argument("--expected-dev-num-samples", type=int, default=0)
    parser.add_argument("--allow-partial-manifest-training", action="store_true")
    parser.add_argument("--save-every-epoch", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.checkpoint = args.checkpoint.resolve()
    args.train_manifest = args.train_manifest.resolve()
    args.dev_manifest = args.dev_manifest.resolve() if args.dev_manifest else None
    args.model_dir = args.model_dir.resolve()
    enforce_full_manifest_training(args)
    args.model_dir.mkdir(parents=True, exist_ok=True)

    model, transform, model_cfg = load_checkpoint(str(args.checkpoint), var_output=True)
    ref_model, _, _ = load_checkpoint(str(args.checkpoint), var_output=True)
    scale_sigma = float(model_cfg.scale_sigma) if args.scale_sigma < 0 else float(args.scale_sigma)
    args.scale_sigma = scale_sigma

    ref_model.to(args.device)
    ref_model.eval()
    for parameter in ref_model.parameters():
        parameter.requires_grad_(False)

    train_manifest = load_manifest(args.train_manifest, limit_rows=args.limit_train_rows)
    dev_manifest = load_manifest(args.dev_manifest, limit_rows=args.limit_dev_rows) if args.dev_manifest else None
    enforce_contrastive_floor(train_manifest, int(args.min_train_positive_instances), label="train")
    enforce_manifest_provenance(train_manifest, args.checkpoint, str(args.expected_train_split), label="train")
    enforce_manifest_sampling_protocol(
        train_manifest,
        expected_sample_seeds=parse_expected_sample_seeds(str(args.expected_train_sample_seeds)),
        expected_num_samples=int(args.expected_train_num_samples),
        label="train",
    )
    if dev_manifest is not None:
        enforce_contrastive_floor(dev_manifest, int(args.min_dev_positive_instances), label="dev")
        enforce_manifest_provenance(dev_manifest, args.checkpoint, str(args.expected_dev_split), label="dev")
        enforce_manifest_sampling_protocol(
            dev_manifest,
            expected_sample_seeds=parse_expected_sample_seeds(str(args.expected_dev_sample_seeds)),
            expected_num_samples=int(args.expected_dev_num_samples),
            label="dev",
        )

    print(f"Reconstructing train contrastive samples: rows={len(train_manifest)}", flush=True)
    train_data = reconstruct_manifest_data(train_manifest, ref_model, transform, scale_sigma, args.device)
    dev_data = None
    if dev_manifest is not None:
        print(f"Reconstructing dev contrastive samples: rows={len(dev_manifest)}", flush=True)
        dev_data = reconstruct_manifest_data(dev_manifest, ref_model, transform, scale_sigma, args.device)

    save_training_config(args, model_cfg, args.model_dir, train_manifest, dev_manifest)
    save_model(model, args.model_dir, "iter=0")

    model.to(args.device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_groups = group_data(train_data)
    rng = random.Random(int(args.seed))
    metrics_rows = []
    best_score = -float("inf")

    for epoch in range(args.epochs):
        model.train()
        epoch_rows = []
        start = time.time()
        for batch in grouped_batches(train_groups, max_samples=int(args.batch_size), shuffle=True, rng=rng):
            data = next(iter(DataLoader(dataset=batch, batch_size=len(batch), num_workers=0, shuffle=False)))
            optim.zero_grad()
            loss, metrics = batch_objective(
                model=model,
                ref_model=ref_model,
                data=data,
                scale_sigma=scale_sigma,
                device=args.device,
                kl_penalty=float(args.kl_penalty),
                bce_weight=float(args.bce_weight),
                pairwise_weight=float(args.pairwise_weight),
                margin=float(args.margin),
                score_mode=str(args.score_mode),
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(args.max_grad_norm))
            optim.step()
            epoch_rows.append(metrics)

        train_metrics = {
            key: float(np.nanmean([row[key] for row in epoch_rows]))
            for key in [
                "loss",
                "bce_like",
                "pairwise",
                "active_pairwise_groups",
                "kl_per_var",
                "positive_log_prob",
                "negative_log_prob",
                "positive_score",
                "negative_score",
            ]
        }
        row = {
            "epoch": epoch,
            "elapsed_sec": time.time() - start,
            **{f"train_{key}": value for key, value in train_metrics.items()},
        }
        if dev_data is not None:
            dev_metrics = evaluate(
                model=model,
                ref_model=ref_model,
                data_list=dev_data,
                batch_size=int(args.batch_size),
                scale_sigma=scale_sigma,
                device=args.device,
                kl_penalty=float(args.kl_penalty),
                bce_weight=float(args.bce_weight),
                pairwise_weight=float(args.pairwise_weight),
                margin=float(args.margin),
                score_mode=str(args.score_mode),
            )
            row.update({f"dev_{key}": value for key, value in dev_metrics.items()})
            score = -dev_metrics["loss"]
        else:
            score = -train_metrics["loss"]

        metrics_rows.append(row)
        pd.DataFrame(metrics_rows).to_csv(args.model_dir / "metrics.csv", index=False)
        print(json.dumps(row, sort_keys=True), flush=True)
        save_model(model, args.model_dir, "last")
        if args.save_every_epoch:
            save_model(model, args.model_dir, f"iter={epoch + 1}")
        if score > best_score:
            best_score = score
            save_model(model, args.model_dir, "best")
            (args.model_dir / "best_score.json").write_text(
                json.dumps({"best_score": best_score, "epoch": epoch}, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
