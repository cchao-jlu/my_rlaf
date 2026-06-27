from __future__ import annotations

import argparse
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from torch_geometric.loader import DataLoader

from src.model.model import load_checkpoint
from summarize_risk_controller_selector import (
    fit_weighted_linear_selector,
    markdown_table,
    selector_prob,
)
from train_adapter_selector import extract_selector_features


DEFAULT_FEATURES = [
    "base_rho_mean",
    "delta_mu_abs_mean",
    "event_gate_mean",
    "event_top10_mass",
    "rho_event_corr",
]
DRIFT_SELECTOR_FEATURE_RE = re.compile(r"^warmup_c(\d+)_minus_warmup_c(\d+)_(.+)$")
POINT_SELECTOR_FEATURE_RE = re.compile(r"^warmup_c(\d+)_(.+)$")
MODEL_SELECTOR_FEATURE_BASES = {
    "base_rho_mean",
    "base_rho_std",
    "base_rho_min",
    "base_rho_max",
    "base_rho_range",
    "num_vars",
    "num_vars_log",
    "base_mu_abs_mean",
    "base_mu_abs_max",
    "base_mu_std",
    "delta_mu_abs_mean",
    "delta_mu_abs_max",
    "delta_rho_abs_mean",
    "delta_rho_abs_max",
    "delta_abs_mean",
    "delta_abs_std",
    "delta_abs_max",
    "event_gate_mean",
    "event_entropy_norm",
    "event_top05_mass",
    "event_top10_mass",
    "rho_event_corr",
    "rho_event_top10_overlap",
    "event_conf_learnt_log_mean",
    "event_conf_learnt_rate_mean",
    "event_conf_learnt_rank_mean",
    "event_conf_learnt_log_max",
    "event_conf_learnt_rate_max",
    "event_conf_learnt_rank_max",
}


@dataclass(frozen=True)
class SelectorMetrics:
    threshold: float
    selected_fraction: float
    base_solved: int
    adapter_solved: int
    selector_solved: int
    lost_solution: int
    recovered_timeout: int
    base_mean: float
    adapter_mean: float
    selector_mean: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a conservative selector from same-evidence counterfactual traces."
    )
    parser.add_argument(
        "--trace",
        action="append",
        required=True,
        help="Counterfactual trace .pt payload. May be passed multiple times.",
    )
    parser.add_argument(
        "--checkpoint",
        default="runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt",
    )
    parser.add_argument(
        "--output-dir",
        default="runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350",
    )
    parser.add_argument(
        "--doc-path",
        default="docs/counterfactual_risk_selector_small300350.md",
    )
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=1.0e-3)
    parser.add_argument(
        "--negative-weight-scale",
        type=float,
        default=2.0,
        help="Extra conservative multiplier for negative counterfactual labels.",
    )
    parser.add_argument("--split-seeds", type=int, default=50)
    parser.add_argument("--train-fraction", type=float, default=0.5)
    parser.add_argument(
        "--max-selected-fraction",
        type=float,
        default=0.25,
        help="Conservative threshold cap; candidates above this train selection rate are ignored when possible.",
    )
    return parser.parse_args()


def load_trace_payload(path: str) -> tuple[list, pd.DataFrame]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "graphs" not in payload or "outcome_frame" not in payload:
        raise ValueError(f"{path} must contain keys 'graphs' and 'outcome_frame'")
    frame = payload["outcome_frame"]
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    return payload["graphs"], frame.copy()


def load_full_trace_payload(path: str) -> dict:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "graphs" not in payload or "outcome_frame" not in payload:
        raise ValueError(f"{path} must contain keys 'graphs' and 'outcome_frame'")
    return payload


def size_from_frame(frame: pd.DataFrame) -> int | str:
    if "size" not in frame or frame["size"].dropna().empty:
        return "unknown"
    values = sorted(set(frame["size"].dropna().tolist()))
    return int(values[0]) if len(values) == 1 and str(values[0]).isdigit() else str(values[0])


def normalise_size_column(outcome: pd.DataFrame) -> pd.Series:
    if "size" not in outcome or outcome["size"].dropna().empty:
        return pd.Series(["unknown"] * len(outcome), index=outcome.index)
    size = outcome["size"].copy()
    numeric = pd.to_numeric(size, errors="coerce")
    if numeric.notna().all():
        return numeric.astype("int64")
    return size.astype(str)


def feature_tensor(frame: pd.DataFrame, feature_names: list[str]) -> torch.Tensor:
    values = frame[feature_names].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any():
        missing = values.columns[values.isna().any()].tolist()
        raise ValueError("Selector features contain NaN values: " + ", ".join(missing))
    return torch.tensor(values.to_numpy(dtype=np.float32), dtype=torch.float32)


def column_tensor(frame: pd.DataFrame, column: str) -> torch.Tensor:
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"Column {column!r} contains NaN values")
    return torch.tensor(values.to_numpy(dtype=np.float32), dtype=torch.float32)


def _add_derived_feature_columns(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for name in feature_names:
        if name in frame.columns:
            continue
        drift = DRIFT_SELECTOR_FEATURE_RE.match(name)
        if drift is None:
            continue
        next_point = int(drift.group(1))
        prev_point = int(drift.group(2))
        base_name = drift.group(3)
        next_col = f"warmup_c{next_point}_{base_name}"
        prev_col = f"warmup_c{prev_point}_{base_name}"
        if next_col in frame.columns and prev_col in frame.columns:
            frame[name] = pd.to_numeric(frame[next_col], errors="coerce").fillna(0.0) - pd.to_numeric(
                frame[prev_col],
                errors="coerce",
            ).fillna(0.0)
    return frame


def _point_feature_groups(frame: pd.DataFrame, feature_names: list[str]) -> dict[int, list[str]]:
    groups: dict[int, list[str]] = {}
    for name in feature_names:
        if name in frame.columns:
            continue
        drift = DRIFT_SELECTOR_FEATURE_RE.match(name)
        if drift is not None:
            next_point = int(drift.group(1))
            prev_point = int(drift.group(2))
            base_name = drift.group(3)
            if base_name not in MODEL_SELECTOR_FEATURE_BASES:
                continue
            for conflicts in [prev_point, next_point]:
                point_col = f"warmup_c{conflicts}_{base_name}"
                if point_col not in frame.columns:
                    groups.setdefault(conflicts, []).append(base_name)
            continue
        point = POINT_SELECTOR_FEATURE_RE.match(name)
        if point is not None:
            conflicts = int(point.group(1))
            base_name = point.group(2)
            if base_name in MODEL_SELECTOR_FEATURE_BASES:
                groups.setdefault(conflicts, []).append(base_name)
    return {point: sorted(set(names)) for point, names in groups.items()}


def _merge_point_model_features(
    *,
    model,
    payload: dict,
    frame: pd.DataFrame,
    feature_names: list[str],
    batch_size: int,
) -> pd.DataFrame:
    groups = _point_feature_groups(frame, feature_names)
    if not groups:
        return frame
    refined_by_point = payload.get("refined_graphs_by_point")
    if not isinstance(refined_by_point, dict):
        raise ValueError("Trace payload is missing refined_graphs_by_point for point selector features")
    merged = frame.copy()
    for point, base_names in sorted(groups.items()):
        if point not in refined_by_point:
            raise ValueError(f"Trace payload does not contain refined graphs for {point} conflicts")
        feature_loader = DataLoader(dataset=refined_by_point[point], batch_size=batch_size, num_workers=0, shuffle=False)
        feature_frame = extract_selector_features(model, feature_loader, base_names)
        rename = {name: f"warmup_c{point}_{name}" for name in base_names}
        feature_frame = feature_frame.rename(columns=rename)
        merged = merged.drop(columns=list(rename.values()), errors="ignore").merge(feature_frame, on="cnf_id", how="left")
    return merged


def load_counterfactual_frame(
    model,
    trace_paths: list[str],
    feature_names: list[str],
    batch_size: int,
    negative_weight_scale: float,
) -> pd.DataFrame:
    frames = []
    for trace_id, path in enumerate(trace_paths):
        payload = load_full_trace_payload(path)
        graphs = payload["graphs"]
        outcome = payload["outcome_frame"]
        if not isinstance(outcome, pd.DataFrame):
            outcome = pd.DataFrame(outcome)
        outcome = outcome.copy()
        outcome = _add_derived_feature_columns(outcome, feature_names)
        outcome = _merge_point_model_features(
            model=model,
            payload=payload,
            frame=outcome,
            feature_names=feature_names,
            batch_size=batch_size,
        )
        outcome = _add_derived_feature_columns(outcome, feature_names)
        missing_features = [name for name in feature_names if name not in outcome.columns]
        if missing_features:
            unsupported = [
                name
                for name in missing_features
                if POINT_SELECTOR_FEATURE_RE.match(name) is not None
                or DRIFT_SELECTOR_FEATURE_RE.match(name) is not None
            ]
            if unsupported:
                raise ValueError(
                    "Point/drift selector features are missing from trace evidence: "
                    + ", ".join(unsupported)
                )
            feature_loader = DataLoader(dataset=graphs, batch_size=batch_size, num_workers=0, shuffle=False)
            feature_frame = extract_selector_features(model, feature_loader, missing_features)
            merged = outcome.merge(feature_frame, on="cnf_id", how="inner")
        else:
            merged = outcome
        outcome["size"] = normalise_size_column(outcome)
        merged["size"] = normalise_size_column(merged)
        for name in feature_names:
            if name not in merged.columns:
                raise ValueError(f"Selector feature {name!r} is not available in trace outcome or model extraction")
            merged[name] = pd.to_numeric(merged[name], errors="coerce")
            if merged[name].isna().any():
                raise ValueError(f"Selector feature {name!r} contains NaN values")
        merged["trace_path"] = path
        merged["trace_id"] = trace_id
        merged["eligible"] = ~merged["warmup_solved"].astype(bool)
        merged["labelled"] = merged["counterfactual_class"].isin(["positive", "negative"])
        merged["selector_label"] = merged["counterfactual_label"].astype("float32")
        merged["selector_weight"] = merged["counterfactual_weight"].astype("float32")
        is_negative = merged["counterfactual_class"] == "negative"
        merged.loc[is_negative, "selector_weight"] *= float(negative_weight_scale)
        frames.append(merged)
    frame = pd.concat(frames, ignore_index=True)
    return frame


def apply_selector(frame: pd.DataFrame, probs: torch.Tensor, threshold: float) -> pd.DataFrame:
    selected = frame.copy()
    selected["selector_prob"] = probs.detach().cpu().numpy()
    selected["selector_use_adapter"] = (
        selected["eligible"].astype(bool) & (selected["selector_prob"] >= float(threshold))
    ).astype("int64")
    use_adapter = selected["selector_use_adapter"].astype(bool)
    selected["selector_time"] = np.where(use_adapter, selected["adapter_time"], selected["base_time"])
    selected["selector_solved"] = np.where(use_adapter, selected["adapter_solved"], selected["base_solved"])
    selected["selector_lost_solution"] = (
        selected["base_solved"].astype(bool) & use_adapter & ~selected["adapter_solved"].astype(bool)
    )
    selected["selector_recovered_timeout"] = (
        ~selected["base_solved"].astype(bool) & use_adapter & selected["adapter_solved"].astype(bool)
    )
    return selected


def metrics_for(frame: pd.DataFrame, probs: torch.Tensor, threshold: float) -> SelectorMetrics:
    eligible_mask = frame["eligible"].to_numpy(dtype=bool)
    eligible = frame.loc[eligible_mask].copy()
    if eligible.empty:
        raise ValueError("No eligible intervention rows found")
    eligible_positions = torch.tensor(np.flatnonzero(eligible_mask), dtype=torch.long)
    eligible_probs = probs[eligible_positions]
    selected = apply_selector(eligible, eligible_probs, threshold)
    return SelectorMetrics(
        threshold=float(threshold),
        selected_fraction=float(selected["selector_use_adapter"].mean()),
        base_solved=int(selected["base_solved"].sum()),
        adapter_solved=int(selected["adapter_solved"].sum()),
        selector_solved=int(selected["selector_solved"].sum()),
        lost_solution=int(selected["selector_lost_solution"].sum()),
        recovered_timeout=int(selected["selector_recovered_timeout"].sum()),
        base_mean=float(selected["base_time"].mean()),
        adapter_mean=float(selected["adapter_time"].mean()),
        selector_mean=float(selected["selector_time"].mean()),
    )


def choose_conservative_threshold(
    frame: pd.DataFrame,
    probs: torch.Tensor,
    max_selected_fraction: float | None = None,
) -> tuple[float, SelectorMetrics]:
    candidates = sorted(set(float(value) for value in probs.detach().cpu().tolist()) | {0.0, 0.5, 1.0, 1.000001})
    candidate_metrics = [(threshold, metrics_for(frame, probs, threshold)) for threshold in candidates]
    if max_selected_fraction is not None:
        capped = [
            item for item in candidate_metrics
            if item[1].selected_fraction <= float(max_selected_fraction)
        ]
        if capped:
            candidate_metrics = capped
    best_threshold = 1.000001
    best_metrics = None
    best_score = None
    for threshold, metrics in candidate_metrics:
        score = (
            metrics.selector_solved,
            -metrics.lost_solution,
            metrics.recovered_timeout,
            -metrics.selector_mean,
            -metrics.selected_fraction,
        )
        if best_score is None or score > best_score:
            best_threshold = threshold
            best_metrics = metrics
            best_score = score
    if best_metrics is None:
        raise ValueError("Failed to choose threshold")
    return best_threshold, best_metrics


def fit_selector_for_frame(
    frame: pd.DataFrame,
    feature_names: list[str],
    epochs: int,
    lr: float,
    l2: float,
    max_selected_fraction: float | None = None,
):
    labelled = frame[frame["labelled"]].copy()
    if labelled["selector_label"].nunique(dropna=True) < 2:
        raise ValueError("Need both positive and negative labels to train selector")
    selector, probs_labelled = fit_weighted_linear_selector(
        feature_tensor(labelled, feature_names),
        column_tensor(labelled, "selector_label"),
        column_tensor(labelled, "selector_weight"),
        feature_names=feature_names,
        epochs=epochs,
        lr=lr,
        l2=l2,
    )
    all_probs = selector_prob(
        selector,
        feature_tensor(frame, feature_names),
    )
    threshold, train_metrics = choose_conservative_threshold(
        frame,
        all_probs,
        max_selected_fraction=max_selected_fraction,
    )
    selector.threshold = float(threshold)
    return selector, all_probs, train_metrics, probs_labelled


def repeated_split_diagnostic(
    frame: pd.DataFrame,
    feature_names: list[str],
    seeds: int,
    train_fraction: float,
    epochs: int,
    lr: float,
    l2: float,
    max_selected_fraction: float | None,
) -> pd.DataFrame:
    rows = []
    eligible_index = frame.index[frame["eligible"]].to_numpy()
    if eligible_index.size == 0:
        return pd.DataFrame()
    for seed in range(1729, 1729 + int(seeds)):
        rng = np.random.default_rng(seed)
        train_indices = []
        heldout_indices = []
        for size, group in frame.loc[eligible_index].groupby("size", sort=True):
            idx = group.index.to_numpy()
            n_train = max(1, min(len(idx) - 1, int(round(float(train_fraction) * len(idx)))))
            chosen = rng.choice(idx, size=n_train, replace=False)
            train_indices.extend(chosen.tolist())
            heldout_indices.extend(sorted(set(idx.tolist()).difference(chosen.tolist())))
        train = frame.loc[train_indices].copy()
        heldout = frame.loc[heldout_indices].copy()
        if train[train["labelled"]]["selector_label"].nunique(dropna=True) < 2:
            continue
        selector, _, train_metrics, _ = fit_selector_for_frame(
            train,
            feature_names=feature_names,
            epochs=epochs,
            lr=lr,
            l2=l2,
            max_selected_fraction=max_selected_fraction,
        )
        heldout_probs = selector_prob(
            selector,
            feature_tensor(heldout, feature_names),
        )
        selected = apply_selector(heldout, heldout_probs, selector.threshold)
        for heldout_name, subset in [("300+350", selected)] + [
            (str(size), selected[selected["size"] == size]) for size in sorted(selected["size"].unique())
        ]:
            if subset.empty:
                continue
            rows.append(
                {
                    "seed": seed,
                    "heldout": heldout_name,
                    "n": int(len(subset)),
                    "threshold": float(selector.threshold),
                    "selected_fraction": float(subset["selector_use_adapter"].mean()),
                    "base_solved": int(subset["base_solved"].sum()),
                    "adapter_solved": int(subset["adapter_solved"].sum()),
                    "selector_solved": int(subset["selector_solved"].sum()),
                    "selector_delta_solved_vs_base": int(subset["selector_solved"].sum() - subset["base_solved"].sum()),
                    "selector_delta_solved_vs_adapter": int(subset["selector_solved"].sum() - subset["adapter_solved"].sum()),
                    "lost_solution": int(subset["selector_lost_solution"].sum()),
                    "recovered_timeout": int(subset["selector_recovered_timeout"].sum()),
                    "base_mean": float(subset["base_time"].mean()),
                    "adapter_mean": float(subset["adapter_time"].mean()),
                    "selector_mean": float(subset["selector_time"].mean()),
                    "selector_delta_vs_base": float(subset["selector_time"].mean() - subset["base_time"].mean()),
                    "selector_delta_vs_adapter": float(subset["selector_time"].mean() - subset["adapter_time"].mean()),
                    "train_selected_fraction": train_metrics.selected_fraction,
                    "train_lost_solution": train_metrics.lost_solution,
                    "train_recovered_timeout": train_metrics.recovered_timeout,
                }
            )
    return pd.DataFrame(rows)


def aggregate_splits(result: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if result.empty:
        return result
    for heldout, group in result.groupby("heldout", sort=False):
        row = {"heldout": heldout}
        for column in [
            "selected_fraction",
            "selector_delta_solved_vs_base",
            "selector_delta_solved_vs_adapter",
            "lost_solution",
            "recovered_timeout",
            "selector_delta_vs_base",
            "selector_delta_vs_adapter",
        ]:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_ci_low"] = float(group[column].quantile(0.025))
            row[f"{column}_ci_high"] = float(group[column].quantile(0.975))
        row["beats_base_solved_rate"] = float((group["selector_delta_solved_vs_base"] > 0).mean())
        row["keeps_base_solved_rate"] = float((group["selector_delta_solved_vs_base"] >= 0).mean())
        row["beats_base_time_rate"] = float((group["selector_delta_vs_base"] < 0.0).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def label_counts(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for size, group in frame.groupby("size", sort=True):
        counts = group["counterfactual_class"].value_counts()
        eligible = group[group["eligible"]]
        rows.append(
            {
                "size": size,
                "n": int(len(group)),
                "eligible": int(len(eligible)),
                "positive": int(counts.get("positive", 0)),
                "negative": int(counts.get("negative", 0)),
                "neutral": int(counts.get("neutral", 0)),
                "warmup_solved": int(counts.get("warmup_solved", 0)),
            }
        )
    return pd.DataFrame(rows)


def reason_counts(frame: pd.DataFrame) -> pd.DataFrame:
    if "counterfactual_reason" not in frame.columns:
        return pd.DataFrame()
    rows = []
    for size, group in frame.groupby("size", sort=True):
        counts = group["counterfactual_reason"].value_counts()
        for reason, count in counts.items():
            rows.append({"size": size, "reason": reason, "count": int(count)})
    return pd.DataFrame(rows)


def metrics_frame(metrics: SelectorMetrics) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "threshold": metrics.threshold,
                "selected_fraction": metrics.selected_fraction,
                "base_solved": metrics.base_solved,
                "adapter_solved": metrics.adapter_solved,
                "selector_solved": metrics.selector_solved,
                "delta_solved_vs_base": metrics.selector_solved - metrics.base_solved,
                "delta_solved_vs_adapter": metrics.selector_solved - metrics.adapter_solved,
                "lost_solution": metrics.lost_solution,
                "recovered_timeout": metrics.recovered_timeout,
                "base_mean": metrics.base_mean,
                "adapter_mean": metrics.adapter_mean,
                "selector_mean": metrics.selector_mean,
                "delta_vs_base": metrics.selector_mean - metrics.base_mean,
                "delta_vs_adapter": metrics.selector_mean - metrics.adapter_mean,
            }
        ]
    )


def write_doc(
    path: str,
    feature_names: list[str],
    counts: pd.DataFrame,
    reasons: pd.DataFrame,
    train_metrics: SelectorMetrics,
    split_summary: pd.DataFrame,
) -> None:
    columns_counts = ["size", "n", "eligible", "positive", "negative", "neutral", "warmup_solved"]
    columns_train = [
        "threshold",
        "selected_fraction",
        "base_solved",
        "adapter_solved",
        "selector_solved",
        "delta_solved_vs_base",
        "delta_solved_vs_adapter",
        "lost_solution",
        "recovered_timeout",
        "selector_mean",
        "delta_vs_base",
    ]
    columns_split = [
        "heldout",
        "selected_fraction_mean",
        "selector_delta_solved_vs_base_mean",
        "selector_delta_solved_vs_adapter_mean",
        "lost_solution_mean",
        "recovered_timeout_mean",
        "selector_delta_vs_base_mean",
        "keeps_base_solved_rate",
        "beats_base_time_rate",
    ]
    doc = [
        "# Counterfactual Risk Selector",
        "",
        "这个 selector 使用 same-evidence counterfactual outcome labels 训练。",
        "它是保守策略：negative labels 被加权放大，threshold 的选择顺序是",
        "先看 solved count，再看 lost solved instances，然后看 recovered",
        "timeouts，最后才看 runtime。",
        "",
        "特征：",
        "",
        "- " + "\n- ".join(feature_names),
        "",
        "## 标签计数",
        "",
        markdown_table(counts, columns_counts),
        "",
        "## 标签原因计数",
        "",
        markdown_table(reasons, ["size", "reason", "count"]) if not reasons.empty else "_无 counterfactual_reason 字段_",
        "",
        "## 全数据拟合 Selector",
        "",
        markdown_table(metrics_frame(train_metrics), columns_train),
        "",
        "## Repeated-Split 诊断",
        "",
        markdown_table(split_summary[columns_split], columns_split) if not split_summary.empty else "_split 数量不足_",
        "",
        "## 解读",
        "",
        "这应该作为 risk controller 使用，而不是作为 always-enable adapter",
        "的证据。拟合得到的 threshold 应写入 selector checkpoint，",
        "然后在 disjoint instances 上继续评估。",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n")


def save_selector_checkpoint(
    checkpoint: str,
    output_dir: str,
    selector,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    shutil.copy2(checkpoint, os.path.join(output_dir, "best.pt"))
    cfg_path = os.path.join(os.path.dirname(checkpoint), "config.yaml")
    cfg = OmegaConf.load(cfg_path)
    cfg.model.event_adapter.selector_feature_names = selector.feature_names
    cfg.model.event_adapter.selector_weights = selector.weights
    cfg.model.event_adapter.selector_bias = selector.bias
    cfg.model.event_adapter.selector_threshold = selector.threshold
    cfg.model.event_adapter.selector_feature_mean = selector.feature_mean
    cfg.model.event_adapter.selector_feature_std = selector.feature_std
    cfg.model.event_adapter.base_rho_gate_threshold = None
    cfg.model.event_adapter.graph_gate_indices = None
    cfg.model.event_adapter.graph_gate_threshold = None
    OmegaConf.save(cfg, os.path.join(output_dir, "config.yaml"))


def main() -> None:
    args = parse_args()
    feature_names = [name.strip() for name in args.features.split(",") if name.strip()]
    if not feature_names:
        raise ValueError("At least one feature is required")

    model, _, _ = load_checkpoint(args.checkpoint, var_output=True)
    model.event_adapter_selector_feature_names = []
    model.event_adapter_base_rho_gate_threshold = None
    model.event_adapter_graph_gate_indices = []
    model.event_adapter_graph_gate_threshold = None

    frame = load_counterfactual_frame(
        model=model,
        trace_paths=args.trace,
        feature_names=feature_names,
        batch_size=args.batch_size,
        negative_weight_scale=args.negative_weight_scale,
    )
    selector, probs, train_metrics, _ = fit_selector_for_frame(
        frame[frame["eligible"]].copy(),
        feature_names=feature_names,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        max_selected_fraction=args.max_selected_fraction,
    )
    selected = apply_selector(frame[frame["eligible"]].copy(), probs, selector.threshold)
    train_metrics = metrics_for(frame[frame["eligible"]].copy(), probs, selector.threshold)

    split_rows = repeated_split_diagnostic(
        frame,
        feature_names=feature_names,
        seeds=args.split_seeds,
        train_fraction=args.train_fraction,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        max_selected_fraction=args.max_selected_fraction,
    )
    split_summary = aggregate_splits(split_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_selector_checkpoint(args.checkpoint, args.output_dir, selector)
    frame.to_csv(output_dir / "counterfactual_selector_training_frame.csv", index=False)
    selected.to_csv(output_dir / "counterfactual_selector_all_data_policy.csv", index=False)
    split_rows.to_csv(output_dir / "counterfactual_selector_repeated_splits.csv", index=False)
    split_summary.to_csv(output_dir / "counterfactual_selector_repeated_split_summary.csv", index=False)
    write_doc(
        args.doc_path,
        feature_names=feature_names,
        counts=label_counts(frame),
        reasons=reason_counts(frame),
        train_metrics=train_metrics,
        split_summary=split_summary,
    )

    print(f"selector features: {selector.feature_names}")
    print(f"selector weights: {selector.weights}")
    print(f"selector bias: {selector.bias:.6f}")
    print(f"selector threshold: {selector.threshold:.6f}")
    print(f"selected fraction: {train_metrics.selected_fraction:.4f}")
    print(f"base solved: {train_metrics.base_solved}")
    print(f"adapter solved: {train_metrics.adapter_solved}")
    print(f"selector solved: {train_metrics.selector_solved}")
    print(f"lost solution: {train_metrics.lost_solution}")
    print(f"recovered timeout: {train_metrics.recovered_timeout}")
    print(f"selector mean: {train_metrics.selector_mean:.6f}")
    print(f"saved selector checkpoint dir: {args.output_dir}")
    print(f"saved report: {args.doc_path}")


if __name__ == "__main__":
    main()
