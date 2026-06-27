from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import torch
from omegaconf import OmegaConf
from torch_geometric.loader import DataLoader

from evaluate_guided_solver import (
    DERIVED_SELECTOR_FEATURES,
    EXTERNAL_SELECTOR_FEATURES,
    MODEL_SELECTOR_FEATURES,
    _attach_derived_selector_stage_features,
    _attach_selector_feature_overrides,
    _extract_selector_feature_frame,
    _feedback_intervention_conflicts,
    _load_local_reopen_candidate_ids,
    _selector_base_feature_name,
    _selector_feature_value,
    _selector_stage_probability,
    _stats_selector_feature_frame,
)
from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit online selector decisions and generated variable guidance for one eval context."
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--eval-path", required=True)
    parser.add_argument("--save-file", required=True)
    parser.add_argument("--focus-keys", default="")
    parser.add_argument("--include-selector-features", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--cpu-lim", type=float, default=60.0)
    parser.add_argument("--k", type=float, default=0.1)
    parser.add_argument("--rollout-conflicts", type=int, default=500)
    parser.add_argument("--warmup-cpu-lim", type=float, default=10.0)
    parser.add_argument("--state-momentum", type=float, default=0.5)
    parser.add_argument("--event-state-features", default="enhanced")
    parser.add_argument("--local-reopen-candidate-manifest", default="")
    return parser.parse_args()


def cnf_id_value(data) -> int:
    value = data.cnf_id
    return int(value.item() if hasattr(value, "item") else value)


def file_key(path: object) -> str:
    return Path(str(path)).name


def dimacs_guidance_hash(var_params: torch.Tensor) -> tuple[str, float, float, float, float, int]:
    params = var_params.detach().cpu()
    if params.dim() == 3:
        params = params[:, 0, :]
    phase = params[:, 0]
    weight = params[:, 1]
    encoded = []
    for phase_value, weight_value in zip(phase.tolist(), weight.tolist()):
        sign = 1 if float(phase_value) > 0.0 else -1
        encoded.append(f"{sign * float(weight_value):.4f}")
    digest = hashlib.sha256(" ".join(encoded).encode("utf-8")).hexdigest()
    return (
        digest,
        float(weight.mean().item()),
        float(weight.std(unbiased=False).item()),
        float(weight.min().item()),
        float(weight.max().item()),
        int((phase > 0.0).sum().item()),
    )


def stage_probs(model, features: pd.DataFrame, stage: str) -> pd.Series:
    if stage == "risk":
        names = list(model.event_adapter_risk_selector_feature_names)
        weights = list(model.event_adapter_risk_selector_weights)
        bias = float(model.event_adapter_risk_selector_bias)
        mean = list(model.event_adapter_risk_selector_feature_mean)
        std = list(model.event_adapter_risk_selector_feature_std)
    elif stage == "recovery":
        names = list(model.event_adapter_recovery_selector_feature_names)
        weights = list(model.event_adapter_recovery_selector_weights)
        bias = float(model.event_adapter_recovery_selector_bias)
        mean = list(model.event_adapter_recovery_selector_feature_mean)
        std = list(model.event_adapter_recovery_selector_feature_std)
    elif stage == "slowdown":
        names = list(model.event_adapter_slowdown_selector_feature_names)
        weights = list(model.event_adapter_slowdown_selector_weights)
        bias = float(model.event_adapter_slowdown_selector_bias)
        mean = list(model.event_adapter_slowdown_selector_feature_mean)
        std = list(model.event_adapter_slowdown_selector_feature_std)
    else:
        raise ValueError(f"Unknown selector stage {stage}")
    if not names:
        return pd.Series([0.0] * len(features), index=features.index)
    return _selector_stage_probability(
        features,
        feature_names=names,
        weights=weights,
        bias=bias,
        mean=mean,
        std=std,
    )


def expanded_selector_feature_frame(
    selector_feature_names: list[str],
    final_point: int,
    feature_by_point: dict[int, pd.DataFrame],
    local_reopen_candidate_ids: set[int] | None = None,
) -> pd.DataFrame:
    rows = []
    for cnf_id in feature_by_point[final_point].index:
        row = {"cnf_id": int(cnf_id)}
        for name in selector_feature_names:
            row[name] = _selector_feature_value(
                name,
                cnf_id=int(cnf_id),
                final_point=final_point,
                feature_by_point=feature_by_point,
                local_reopen_candidate_ids=local_reopen_candidate_ids,
            )
        rows.append(row)
    return pd.DataFrame(rows).set_index("cnf_id")


def build_online_guidance(args: argparse.Namespace) -> pd.DataFrame:
    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    dataset = DimacsCNFDataset(path=args.eval_path, transform=transform, lazy=True)
    local_reopen_candidate_ids = _load_local_reopen_candidate_ids(
        args.local_reopen_candidate_manifest,
        dataset,
    )
    if local_reopen_candidate_ids:
        print(f"Loaded {len(local_reopen_candidate_ids)} local reopen candidates")
    loader = DataLoader(dataset=dataset, batch_size=args.batch_size, num_workers=0, shuffle=False)
    base_data_list = sample_var_params(
        model=model,
        loader=loader,
        device=device,
        use_mode=True,
        num_samples=1,
        scale_sigma=model_cfg.scale_sigma,
        add_timing=False,
        cache_var_features=bool(getattr(model, "event_adapter_enabled", False)),
    )

    selector_feature_names = list(getattr(model, "event_adapter_selector_feature_names", []))
    points = _feedback_intervention_conflicts(
        OmegaConf.create(
            {
                "intervention_conflicts": None,
                "rollout_conflicts": int(args.rollout_conflicts),
            }
        ),
        selector_feature_names=selector_feature_names,
    )
    base_feature_names = sorted({_selector_base_feature_name(name) for name in selector_feature_names})
    model_feature_names = [name for name in base_feature_names if name in MODEL_SELECTOR_FEATURES]
    var_state_dim = int(getattr(model, "var_state_dim", 0))
    solver_params = {"cpu-lim": args.cpu_lim, "rnd-freq": 0.0, "K": args.k}
    refined_by_point = {}
    feature_by_point = {}
    for point in points:
        point_params = apply_rollout_budget(
            solver_params,
            budget_type="conflicts",
            cpu_lim=args.warmup_cpu_lim,
            conflicts=point,
        )
        point_params["collect-events"] = True
        warmup_stats = compute_solver_stats(
            dataset=dataset,
            data_list=base_data_list,
            num_workers=args.num_workers,
            solver=model_cfg.solver.solver,
            **point_params,
        )
        refined_graphs = attach_var_event_state_batch(
            base_data_list,
            warmup_stats,
            var_state_dim=var_state_dim,
            momentum=float(args.state_momentum),
            feature_mode=str(args.event_state_features),
        )
        refined_by_point[point] = refined_graphs
        point_feature = _stats_selector_feature_frame(warmup_stats)
        if model_feature_names:
            model_feature = _extract_selector_feature_frame(
                model=model,
                graphs=refined_graphs,
                feature_names=model_feature_names,
                batch_size=args.batch_size,
                device=device,
            )
            point_feature = point_feature.merge(model_feature, on="cnf_id", how="left")
        missing = sorted(set(base_feature_names).difference(point_feature.columns))
        missing = [
            name
            for name in missing
            if name not in DERIVED_SELECTOR_FEATURES and name not in EXTERNAL_SELECTOR_FEATURES
        ]
        if missing:
            raise ValueError("Missing selector features: " + ", ".join(missing))
        feature_by_point[point] = point_feature.set_index("cnf_id")

    final_point = points[-1]
    feature_by_point = _attach_derived_selector_stage_features(
        model=model,
        selector_feature_names=selector_feature_names,
        final_point=final_point,
        feature_by_point=feature_by_point,
    )
    refined_graphs = _attach_selector_feature_overrides(
        refined_by_point[final_point],
        selector_feature_names=selector_feature_names,
        final_point=final_point,
        feature_by_point=feature_by_point,
        local_reopen_candidate_ids=local_reopen_candidate_ids,
    )
    refined_loader = DataLoader(dataset=refined_graphs, batch_size=args.batch_size, num_workers=0, shuffle=False)
    final_data_list = sample_var_params(
        model=model,
        loader=refined_loader,
        device=device,
        use_mode=True,
        num_samples=1,
        scale_sigma=model_cfg.scale_sigma,
        add_timing=False,
        cache_var_features=bool(getattr(model, "event_adapter_enabled", False)),
    )

    features = expanded_selector_feature_frame(
        selector_feature_names=selector_feature_names,
        final_point=final_point,
        feature_by_point=feature_by_point,
        local_reopen_candidate_ids=local_reopen_candidate_ids,
    )
    features["risk_prob"] = stage_probs(model, features, "risk")
    features["recovery_prob"] = stage_probs(model, features, "recovery")
    features["slowdown_prob"] = stage_probs(model, features, "slowdown")
    features["use_before_veto"] = (
        (features["risk_prob"] < float(model.event_adapter_risk_selector_threshold))
        & (features["recovery_prob"] >= float(model.event_adapter_recovery_selector_threshold))
    )
    if list(getattr(model, "event_adapter_slowdown_selector_feature_names", [])):
        features["slowdown_veto"] = (
            features["use_before_veto"]
            & (features["slowdown_prob"] >= float(model.event_adapter_slowdown_selector_threshold))
        )
    else:
        features["slowdown_veto"] = False
    features["use_adapter"] = features["use_before_veto"] & ~features["slowdown_veto"]
    if "local_reopen_candidate" in features.columns:
        features["local_reopen_rule_open"] = (
            (features["local_reopen_candidate"] >= 1.0)
            & (features["warmup_c1000_minus_warmup_c750_decisions"] >= 294.0)
            & (features["warmup_c2000_rho_event_corr"] >= 0.0365)
        )
        features["use_adapter_with_local_reopen"] = features["use_adapter"] | (
            (~features["use_adapter"]) & features["local_reopen_rule_open"]
        )
    else:
        features["local_reopen_rule_open"] = False
        features["use_adapter_with_local_reopen"] = features["use_adapter"]

    rows = []
    data_by_id = {cnf_id_value(data): data for data in final_data_list}
    focus = {key.strip() for key in args.focus_keys.split(",") if key.strip()}
    for cnf_id, path in dataset.id_to_file.items():
        key = file_key(path)
        if focus and key not in focus:
            continue
        data = data_by_id[int(cnf_id)]
        digest, weight_mean, weight_std, weight_min, weight_max, phase_true = dimacs_guidance_hash(
            data["var"].var_params
        )
        row = {
            "eval_path": args.eval_path,
            "checkpoint": args.checkpoint,
            "cnf_id": int(cnf_id),
            "file": path,
            "file_key": key,
            "guidance_hash": digest,
            "weight_mean": weight_mean,
            "weight_std": weight_std,
            "weight_min": weight_min,
            "weight_max": weight_max,
            "phase_true": phase_true,
        }
        if int(cnf_id) in features.index:
            for column in [
                "risk_prob",
                "recovery_prob",
                "slowdown_prob",
                "use_before_veto",
                "slowdown_veto",
                "use_adapter",
                "local_reopen_rule_open",
                "use_adapter_with_local_reopen",
            ]:
                value = features.loc[int(cnf_id), column]
                row[column] = bool(value) if column.startswith("use") or column.endswith("veto") else float(value)
            if args.include_selector_features:
                for name in selector_feature_names:
                    row[name] = float(features.loc[int(cnf_id), name])
        rows.append(row)
    return pd.DataFrame(rows).sort_values("file_key")


def main() -> None:
    args = parse_args()
    frame = build_online_guidance(args)
    out = Path(args.save_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    print(f"wrote {out}")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
