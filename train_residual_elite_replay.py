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
    required = {"cnf_path", "sample_seed", "num_samples_generated", "sample_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Elite manifest is missing columns: {sorted(missing)}")
    if limit_rows > 0:
        frame = frame.head(limit_rows).copy()
    if frame.empty:
        raise ValueError(f"Elite manifest has no rows: {path}")
    return frame


def positive_instance_count(manifest: pd.DataFrame) -> int:
    if manifest.empty:
        return 0
    return manifest[["family", "size", "file_key"]].drop_duplicates().shape[0]


def enforce_positive_floor(manifest: pd.DataFrame, min_positive_instances: int, label: str) -> None:
    if min_positive_instances <= 0:
        return
    positive_instances = positive_instance_count(manifest)
    if positive_instances < min_positive_instances:
        raise ValueError(
            f"{label} elite replay manifest has too few positive instances: "
            f"{positive_instances} < {min_positive_instances}. "
            "Do not train formal elite replay from sparse mining artifacts."
        )


def enforce_full_manifest_training(args: argparse.Namespace) -> None:
    uses_row_limits = int(args.limit_train_rows) > 0 or int(args.limit_dev_rows) > 0
    if uses_row_limits and not bool(args.allow_partial_manifest_training):
        raise ValueError(
            "Partial manifest training is disabled for formal replay training. "
            "Set --allow-partial-manifest-training only for smoke/debug runs, "
            "and do not gate checkpoints trained with row-limited manifests."
        )


def enforce_manifest_provenance(
    manifest: pd.DataFrame,
    checkpoint: Path,
    expected_split: str,
    label: str,
) -> None:
    split_values = set(manifest["split"].astype(str)) if "split" in manifest.columns else set()
    if split_values != {expected_split}:
        raise ValueError(
            f"{label} elite replay manifest split mismatch: "
            f"observed={sorted(split_values)} expected={expected_split}. "
            "Do not train replay from the wrong residual split."
        )

    if "source_checkpoint_sha256" not in manifest.columns:
        raise ValueError(
            f"{label} elite replay manifest is missing source_checkpoint_sha256. "
            "Build the formal manifest with build_residual_elite_replay_manifest.py."
        )
    expected_hash = file_sha256(checkpoint)
    observed_hashes = set(manifest["source_checkpoint_sha256"].astype(str))
    if observed_hashes != {expected_hash}:
        raise ValueError(
            f"{label} elite replay manifest checkpoint hash mismatch: "
            f"observed={sorted(observed_hashes)} expected={expected_hash}. "
            "Do not train replay from elites mined by a different checkpoint."
        )


def load_sampling_protocol_frame(manifest: pd.DataFrame, label: str) -> pd.DataFrame:
    if "source_raw_csv" not in manifest.columns:
        return manifest
    raw_paths = [str(value) for value in manifest["source_raw_csv"].dropna().astype(str).unique()]
    raw_paths = [value for value in raw_paths if value.strip()]
    if not raw_paths:
        return manifest

    frames = []
    for raw_path in sorted(raw_paths):
        path = Path(raw_path)
        if not path.exists():
            raise FileNotFoundError(f"{label} elite replay manifest raw source is missing: {path}")
        if "source_raw_sha256" in manifest.columns:
            expected_hashes = set(
                manifest.loc[manifest["source_raw_csv"].astype(str).eq(raw_path), "source_raw_sha256"].astype(str)
            )
            if len(expected_hashes) != 1:
                raise ValueError(f"{label} elite replay manifest has inconsistent raw hashes for {path}")
            expected_hash = next(iter(expected_hashes))
            actual_hash = file_sha256(path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"{label} elite replay manifest raw hash mismatch for {path}: "
                    f"observed={actual_hash} expected={expected_hash}"
                )
        frames.append(pd.read_csv(path))
    if not frames:
        return manifest
    return pd.concat(frames, ignore_index=True)


def parse_expected_sample_seeds(raw: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if raw.strip() and not seeds:
        raise ValueError("Expected sample seed list cannot be empty.")
    return seeds


def enforce_manifest_sampling_protocol(
    manifest: pd.DataFrame,
    expected_sample_seeds: tuple[int, ...],
    expected_num_samples: int,
    label: str,
) -> None:
    frame = load_sampling_protocol_frame(manifest, label=label)
    required = {"sample_seed", "num_samples_generated"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} elite replay manifest is missing sampling columns: {missing}")

    sample_seeds = pd.to_numeric(frame["sample_seed"], errors="coerce")
    num_samples = pd.to_numeric(frame["num_samples_generated"], errors="coerce")
    if sample_seeds.isna().any() or num_samples.isna().any():
        invalid = int((sample_seeds.isna() | num_samples.isna()).sum())
        raise ValueError(f"{label} elite replay manifest has non-numeric sampling values: invalid_rows={invalid}")

    if expected_sample_seeds:
        observed_seeds = tuple(sorted(set(sample_seeds.astype(int))))
        expected_seeds = tuple(sorted(set(expected_sample_seeds)))
        if observed_seeds != expected_seeds:
            raise ValueError(
                f"{label} elite replay manifest sample seed mismatch: "
                f"observed={observed_seeds} expected={expected_seeds}."
            )

    if expected_num_samples > 0:
        observed_num_samples = tuple(sorted(set(num_samples.astype(int))))
        if observed_num_samples != (int(expected_num_samples),):
            raise ValueError(
                f"{label} elite replay manifest num_samples_generated mismatch: "
                f"observed={observed_num_samples} expected={expected_num_samples}."
            )


def reconstruct_elite_data(
    manifest: pd.DataFrame,
    model: torch.nn.Module,
    transform,
    scale_sigma: float,
    device: str,
) -> list:
    data_list = []
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
            data.elite_cpu_time = torch.tensor([float(row.get("CPU time", float("nan")))], dtype=torch.float32)
            data.elite_rank = torch.tensor([int(row.get("elite_rank_in_instance", 1))], dtype=torch.long)
            data_list.append(data)
    if not data_list:
        raise ValueError("No elite samples reconstructed.")
    return data_list


def graph_counts(var_batch: torch.Tensor, expected_graphs: int) -> torch.Tensor:
    counts = torch.bincount(var_batch, minlength=expected_graphs).float()
    return counts.clamp_min(1.0)


def batch_metrics(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    data,
    scale_sigma: float,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    data = data.to(device)
    y_var = model(data)
    with torch.no_grad():
        y_var_ref = ref_model(data)

    var_params = data["var"].var_params.transpose(0, 1).float()
    var_batch = data["lit"].batch[0::2]
    log_prob = policy.log_prob(y_var.float(), var_params, var_batch, scale_sigma=scale_sigma).squeeze(0)
    counts = graph_counts(var_batch, expected_graphs=log_prob.shape[0]).to(log_prob.device)
    log_prob_per_var = log_prob / counts

    kl_div = policy.kl_div(y_var.float(), y_var_ref.float(), var_batch, scale_sigma=scale_sigma)
    kl_per_var = kl_div / counts
    objective = log_prob_per_var.mean()
    return objective, log_prob_per_var.mean(), kl_per_var.mean()


def evaluate(
    model: torch.nn.Module,
    ref_model: torch.nn.Module,
    data_list: list,
    batch_size: int,
    scale_sigma: float,
    device: str,
    kl_penalty: float,
) -> dict[str, float]:
    loader = DataLoader(dataset=data_list, batch_size=batch_size, num_workers=0, shuffle=False)
    model.eval()
    values = []
    with torch.no_grad():
        for data in loader:
            objective, log_prob, kl = batch_metrics(
                model=model,
                ref_model=ref_model,
                data=data,
                scale_sigma=scale_sigma,
                device=device,
            )
            values.append(
                {
                    "elite_log_prob_per_var": float(log_prob.detach().cpu()),
                    "kl_per_var": float(kl.detach().cpu()),
                    "objective": float((objective - kl_penalty * kl).detach().cpu()),
                }
            )
    return {
        key: float(np.mean([row[key] for row in values]))
        for key in ["elite_log_prob_per_var", "kl_per_var", "objective"]
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
    cfg.elite_replay = {
        "train_manifest": str(args.train_manifest),
        "train_manifest_sha256": file_sha256(args.train_manifest),
        "dev_manifest": str(args.dev_manifest) if args.dev_manifest else "",
        "dev_manifest_sha256": file_sha256(args.dev_manifest) if args.dev_manifest else "",
        "source_checkpoint_sha256": file_sha256(args.checkpoint),
        "train_elite_rows": int(len(train_manifest)),
        "train_positive_instances": int(positive_instance_count(train_manifest)),
        "dev_elite_rows": int(len(dev_manifest)) if dev_manifest is not None else 0,
        "dev_positive_instances": int(positive_instance_count(dev_manifest)) if dev_manifest is not None else 0,
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
        "scale_sigma": float(args.scale_sigma),
        "seed": int(args.seed),
    }
    OmegaConf.save(cfg, model_dir / "config.yaml")


def save_model(model: torch.nn.Module, model_dir: Path, name: str) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_dir / f"{name}.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finetune March policy with residual elite replay.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--dev-manifest", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--kl-penalty", type=float, default=0.05)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--scale-sigma", type=float, default=-1.0)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=1741)
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
    dev_manifest = (
        load_manifest(args.dev_manifest, limit_rows=args.limit_dev_rows)
        if args.dev_manifest is not None
        else None
    )
    enforce_positive_floor(
        train_manifest,
        min_positive_instances=int(args.min_train_positive_instances),
        label="train",
    )
    enforce_manifest_provenance(
        train_manifest,
        checkpoint=args.checkpoint,
        expected_split=str(args.expected_train_split),
        label="train",
    )
    enforce_manifest_sampling_protocol(
        train_manifest,
        expected_sample_seeds=parse_expected_sample_seeds(str(args.expected_train_sample_seeds)),
        expected_num_samples=int(args.expected_train_num_samples),
        label="train",
    )
    if dev_manifest is not None:
        enforce_positive_floor(
            dev_manifest,
            min_positive_instances=int(args.min_dev_positive_instances),
            label="dev",
        )
        enforce_manifest_provenance(
            dev_manifest,
            checkpoint=args.checkpoint,
            expected_split=str(args.expected_dev_split),
            label="dev",
        )
        enforce_manifest_sampling_protocol(
            dev_manifest,
            expected_sample_seeds=parse_expected_sample_seeds(str(args.expected_dev_sample_seeds)),
            expected_num_samples=int(args.expected_dev_num_samples),
            label="dev",
        )
    print(f"Reconstructing train elites: rows={len(train_manifest)}", flush=True)
    train_data = reconstruct_elite_data(
        manifest=train_manifest,
        model=ref_model,
        transform=transform,
        scale_sigma=scale_sigma,
        device=args.device,
    )
    dev_data = None
    if dev_manifest is not None:
        print(f"Reconstructing dev elites: rows={len(dev_manifest)}", flush=True)
        dev_data = reconstruct_elite_data(
            manifest=dev_manifest,
            model=ref_model,
            transform=transform,
            scale_sigma=scale_sigma,
            device=args.device,
        )

    save_training_config(
        args,
        model_cfg=model_cfg,
        model_dir=args.model_dir,
        train_manifest=train_manifest,
        dev_manifest=dev_manifest,
    )
    save_model(model, args.model_dir, "iter=0")

    model.to(args.device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    train_loader = DataLoader(dataset=train_data, batch_size=args.batch_size, num_workers=0, shuffle=True)
    metrics_rows = []
    best_score = -float("inf")

    for epoch in range(args.epochs):
        model.train()
        epoch_values = []
        start = time.time()
        for data in train_loader:
            optim.zero_grad()
            objective, log_prob, kl = batch_metrics(
                model=model,
                ref_model=ref_model,
                data=data,
                scale_sigma=scale_sigma,
                device=args.device,
            )
            objective_total = objective - float(args.kl_penalty) * kl
            loss = -objective_total
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(args.max_grad_norm))
            optim.step()
            epoch_values.append(
                {
                    "elite_log_prob_per_var": float(log_prob.detach().cpu()),
                    "kl_per_var": float(kl.detach().cpu()),
                    "objective": float(objective_total.detach().cpu()),
                }
            )

        train_metrics = {
            key: float(np.mean([row[key] for row in epoch_values]))
            for key in ["elite_log_prob_per_var", "kl_per_var", "objective"]
        }
        row = {
            "epoch": epoch,
            "elapsed_sec": time.time() - start,
            "train_elite_log_prob_per_var": train_metrics["elite_log_prob_per_var"],
            "train_kl_per_var": train_metrics["kl_per_var"],
            "train_objective": train_metrics["objective"],
        }
        if dev_data is not None:
            dev_metrics = evaluate(
                model=model,
                ref_model=ref_model,
                data_list=dev_data,
                batch_size=args.batch_size,
                scale_sigma=scale_sigma,
                device=args.device,
                kl_penalty=float(args.kl_penalty),
            )
            row.update(
                {
                    "dev_elite_log_prob_per_var": dev_metrics["elite_log_prob_per_var"],
                    "dev_kl_per_var": dev_metrics["kl_per_var"],
                    "dev_objective": dev_metrics["objective"],
                }
            )
            score = dev_metrics["objective"]
        else:
            score = train_metrics["objective"]
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
