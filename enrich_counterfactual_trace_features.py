from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import torch
from torch_geometric.data import HeteroData
from torch_geometric.loader import DataLoader

from generate_counterfactual_outcome_traces import _multi_point_frame, intervention_conflict_points
from src.model.model import load_checkpoint
from train_counterfactual_risk_selector import load_trace_payload


DEFAULT_FEATURES = [
    "base_rho_mean",
    "base_rho_std",
    "base_rho_range",
    "delta_abs_mean",
    "delta_abs_max",
    "delta_mu_abs_mean",
    "delta_mu_abs_max",
    "event_gate_mean",
    "event_entropy_norm",
    "event_top05_mass",
    "event_top10_mass",
    "rho_event_corr",
    "rho_event_top10_overlap",
    "event_conf_learnt_log_mean",
    "event_conf_learnt_log_max",
    "event_conf_learnt_rate_mean",
    "event_conf_learnt_rate_max",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill deployable multi-point selector features into a counterfactual trace payload."
    )
    parser.add_argument("--trace", required=True, help="Input counterfactual trace .pt payload.")
    parser.add_argument("--checkpoint", default="runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt")
    parser.add_argument("--output", required=True, help="Output enriched trace .pt payload.")
    parser.add_argument("--output-csv", default="", help="Optional enriched outcome CSV path.")
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--batch-size", type=int, default=20)
    return parser.parse_args()


def cnf_id(data: HeteroData) -> int:
    value = data.cnf_id
    return int(value.item() if hasattr(value, "item") else value)


def batch_cnf_ids(batch: HeteroData) -> list[int]:
    value = batch.cnf_id
    if hasattr(value, "view"):
        return [int(item) for item in value.view(-1).tolist()]
    if isinstance(value, list):
        return [int(item.item() if hasattr(item, "item") else item) for item in value]
    return [int(value.item() if hasattr(value, "item") else value)]


def extract_point_features(
    model: torch.nn.Module,
    graphs: list[HeteroData],
    feature_names: list[str],
    batch_size: int,
) -> pd.DataFrame:
    rows = []
    if not feature_names:
        return pd.DataFrame({"cnf_id": [cnf_id(graph) for graph in graphs]})
    loader = DataLoader(dataset=graphs, batch_size=batch_size, num_workers=0, shuffle=False)
    model.eval()
    with torch.no_grad():
        for batch in loader:
            y = model(batch)
            base_y = batch["var"].base_y.to(dtype=torch.float32)
            var_state = batch["var"].event_state.to(dtype=torch.float32)
            delta = y.to(dtype=torch.float32) - base_y
            var_batch = batch["var"].batch if hasattr(batch["var"], "batch") else batch["lit"].batch[0::2]
            var_batch = var_batch.to(device=base_y.device)
            num_graphs = int(var_batch.max().item()) + 1 if var_batch.numel() > 0 else 1
            values = torch.stack(
                [
                    model._event_adapter_selector_feature(
                        name,
                        base_y=base_y,
                        var_state=var_state,
                        delta=delta,
                        var_batch=var_batch,
                        num_graphs=num_graphs,
                    )
                    for name in feature_names
                ],
                dim=1,
            )
            for graph_id, graph_values in zip(batch_cnf_ids(batch), values.detach().cpu()):
                row = {"cnf_id": int(graph_id)}
                row.update({name: float(value) for name, value in zip(feature_names, graph_values.tolist())})
                rows.append(row)
    return pd.DataFrame(rows)


def point_prefix(point: int) -> str:
    return f"warmup_c{int(point)}"


def rebuild_outcome_with_features(payload: dict, multi_point: pd.DataFrame) -> pd.DataFrame:
    outcome = payload["outcome_frame"].copy()
    if "file" in multi_point.columns:
        feature_frame = multi_point.drop(columns=["file"], errors="ignore")
    else:
        feature_frame = multi_point
    replace_columns = [
        column
        for column in feature_frame.columns
        if column not in {"cnf_id", "sample_id"}
    ]
    outcome = outcome.drop(columns=replace_columns, errors="ignore")
    return outcome.merge(feature_frame, on=["cnf_id", "sample_id"], how="left")


def main() -> None:
    args = parse_args()
    feature_names = [name.strip() for name in args.features.split(",") if name.strip()]
    if not feature_names:
        raise ValueError("At least one feature is required")

    _, outcome = load_trace_payload(args.trace)
    payload = torch.load(args.trace, map_location="cpu", weights_only=False)
    model, _, _ = load_checkpoint(args.checkpoint, var_output=True)
    model.event_adapter_selector_feature_names = []
    model.event_adapter_base_rho_gate_threshold = None
    model.event_adapter_graph_gate_indices = []
    model.event_adapter_graph_gate_threshold = None

    config = payload.get("config", {})
    if payload.get("intervention_conflicts"):
        points = [int(point) for point in payload["intervention_conflicts"]]
    elif config and "counterfactual" in config:
        points = intervention_conflict_points(config["counterfactual"])
    else:
        raise ValueError("Trace payload does not contain intervention conflict points")
    points = sorted(points)

    stats_by_point = payload.get("warmup_stats_by_point")
    graphs_by_point = payload.get("refined_graphs_by_point")
    if not isinstance(stats_by_point, dict) or not isinstance(graphs_by_point, dict):
        raise ValueError("Trace payload must contain warmup_stats_by_point and refined_graphs_by_point")

    feature_frames_by_point = {}
    for point in points:
        print(f"Extracting selector features at {point} conflicts")
        feature_frames_by_point[point] = extract_point_features(
            model=model,
            graphs=graphs_by_point[point],
            feature_names=feature_names,
            batch_size=args.batch_size,
        )

    multi_point = _multi_point_frame(
        points=points,
        stats_by_point=stats_by_point,
        graphs_by_point=graphs_by_point,
        feature_frames_by_point=feature_frames_by_point,
        feature_names=feature_names,
    )
    enriched_outcome = rebuild_outcome_with_features(payload, multi_point)
    payload["outcome_frame"] = enriched_outcome
    payload["multi_point_feature_frame"] = multi_point
    payload["multi_point_feature_names"] = feature_names
    payload["feature_enrichment"] = {
        "source_trace": args.trace,
        "checkpoint": args.checkpoint,
        "features": feature_names,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, output)
    if args.output_csv:
        os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
        enriched_outcome.to_csv(args.output_csv, index=False)
    print(f"Saved enriched trace to {output}")
    if args.output_csv:
        print(f"Saved enriched outcome CSV to {args.output_csv}")
    print(f"Rows: {len(enriched_outcome)}; feature count: {len(feature_names)}")


if __name__ == "__main__":
    main()
