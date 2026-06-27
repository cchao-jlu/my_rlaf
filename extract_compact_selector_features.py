from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import torch
from torch_geometric.loader import DataLoader

from evaluate_guided_solver import (
    DERIVED_SELECTOR_FEATURES,
    EXTERNAL_SELECTOR_FEATURES,
    MODEL_SELECTOR_FEATURES,
    _attach_derived_selector_stage_features,
    _attach_selector_feature_overrides,
    _extract_selector_feature_frame,
    _selector_base_feature_name,
    _selector_feature_points,
    _selector_feature_value,
    _stats_selector_feature_frame,
)
from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract deployed compact selector evidence and probabilities.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--cpu-lim", type=float, default=60.0)
    parser.add_argument("--warmup-cpu-lim", type=float, default=10.0)
    parser.add_argument("--state-momentum", type=float, default=0.5)
    parser.add_argument("--event-state-features", default="enhanced")
    return parser.parse_args()


def cnf_ids_from_batch(data_list: list) -> list[int]:
    result = []
    for data in data_list:
        value = data.cnf_id
        result.append(int(value.item() if hasattr(value, "item") else value))
    return result


def stage_probability(
    features: pd.DataFrame,
    feature_names: list[str],
    weights: list[float],
    bias: float,
    mean: list[float],
    std: list[float],
) -> torch.Tensor:
    values = torch.tensor(features[feature_names].to_numpy(dtype="float32"), dtype=torch.float32)
    center = torch.tensor(mean, dtype=torch.float32)
    scale = torch.tensor(std, dtype=torch.float32).clamp_min(1.0e-6)
    weights_t = torch.tensor(weights, dtype=torch.float32)
    logits = ((values - center) / scale).matmul(weights_t) + float(bias)
    return torch.sigmoid(logits)


def main() -> None:
    args = parse_args()
    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)
    if not getattr(model, "event_adapter_enabled", False):
        raise ValueError("checkpoint must contain an event adapter")
    selector_feature_names = list(getattr(model, "event_adapter_selector_feature_names", []))
    if not selector_feature_names:
        raise ValueError("checkpoint does not contain selector_feature_names")

    points = sorted(_selector_feature_points(selector_feature_names))
    if not points:
        raise ValueError("selector_feature_names do not reference any warmup conflict points")

    dataset = DimacsCNFDataset(path=args.dataset, transform=transform, lazy=True)
    loader = DataLoader(dataset=dataset, batch_size=args.batch_size, num_workers=0, shuffle=False)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    warmup_data_list = sample_var_params(
        model=model,
        loader=loader,
        device=device,
        use_mode=True,
        num_samples=1,
        scale_sigma=model_cfg.scale_sigma,
        add_timing=True,
        cache_var_features=True,
    )
    base_feature_names = sorted({_selector_base_feature_name(name) for name in selector_feature_names})
    model_feature_names = [name for name in base_feature_names if name in MODEL_SELECTOR_FEATURES]

    feature_by_point = {}
    refined_by_point = {}
    solver = model_cfg.solver.solver
    for point in points:
        print(f"Collecting selector evidence at {point} conflicts")
        point_params = apply_rollout_budget(
            {"cpu-lim": float(args.cpu_lim), "rnd-freq": 0.0, "K": 0.1},
            budget_type="conflicts",
            cpu_lim=float(args.warmup_cpu_lim),
            conflicts=int(point),
        )
        point_params["collect-events"] = True
        warmup_stats = compute_solver_stats(
            dataset=dataset,
            data_list=warmup_data_list,
            num_workers=int(args.num_workers),
            solver=solver,
            **point_params,
        )
        refined_graphs = attach_var_event_state_batch(
            warmup_data_list,
            warmup_stats,
            var_state_dim=int(model.var_state_dim),
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
                batch_size=int(args.batch_size),
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
            raise ValueError("Missing selector base features: " + ", ".join(missing))
        feature_by_point[point] = point_feature.set_index("cnf_id")

    final_point = points[-1]
    feature_by_point = _attach_derived_selector_stage_features(
        model,
        selector_feature_names=selector_feature_names,
        final_point=final_point,
        feature_by_point=feature_by_point,
    )
    rows = []
    for graph in refined_by_point[final_point]:
        value = graph.cnf_id
        cnf_id = int(value.item() if hasattr(value, "item") else value)
        row = {"cnf_id": cnf_id}
        for name in selector_feature_names:
            row[name] = _selector_feature_value(
                name,
                cnf_id=cnf_id,
                final_point=final_point,
                feature_by_point=feature_by_point,
            )
        for point, frame in feature_by_point.items():
            for column in ["solved", "decisions", "conflicts", "propagations", "cpu_time"]:
                if column in frame.columns:
                    row[f"warmup_c{point}_{column}"] = float(frame.loc[cnf_id, column])
        rows.append(row)
    features = pd.DataFrame(rows).sort_values("cnf_id").reset_index(drop=True)

    risk_probs = stage_probability(
        features,
        feature_names=list(model.event_adapter_risk_selector_feature_names),
        weights=list(model.event_adapter_risk_selector_weights),
        bias=float(model.event_adapter_risk_selector_bias),
        mean=list(model.event_adapter_risk_selector_feature_mean),
        std=list(model.event_adapter_risk_selector_feature_std),
    )
    recovery_probs = stage_probability(
        features,
        feature_names=list(model.event_adapter_recovery_selector_feature_names),
        weights=list(model.event_adapter_recovery_selector_weights),
        bias=float(model.event_adapter_recovery_selector_bias),
        mean=list(model.event_adapter_recovery_selector_feature_mean),
        std=list(model.event_adapter_recovery_selector_feature_std),
    )
    features["risk_prob"] = risk_probs.numpy()
    features["recovery_prob"] = recovery_probs.numpy()
    use_adapter = (
        (features["risk_prob"] < float(model.event_adapter_risk_selector_threshold))
        & (features["recovery_prob"] >= float(model.event_adapter_recovery_selector_threshold))
    )
    if getattr(model, "event_adapter_slowdown_selector_feature_names", []):
        slowdown_probs = stage_probability(
            features,
            feature_names=list(model.event_adapter_slowdown_selector_feature_names),
            weights=list(model.event_adapter_slowdown_selector_weights),
            bias=float(model.event_adapter_slowdown_selector_bias),
            mean=list(model.event_adapter_slowdown_selector_feature_mean),
            std=list(model.event_adapter_slowdown_selector_feature_std),
        )
        features["slowdown_prob"] = slowdown_probs.numpy()
        use_adapter = use_adapter & (
            features["slowdown_prob"] < float(model.event_adapter_slowdown_selector_threshold)
        )
    features["selector_use_adapter"] = use_adapter.astype("int64")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(output, index=False)
    print(f"wrote {output}")
    print(
        features[
            [
                name
                for name in ["selector_use_adapter", "risk_prob", "recovery_prob", "slowdown_prob"]
                if name in features.columns
            ]
        ]
        .mean(numeric_only=True)
        .to_string()
    )


if __name__ == "__main__":
    main()
