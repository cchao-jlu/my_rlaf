from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from omegaconf import OmegaConf

from src.model.model import load_checkpoint
from summarize_risk_controller_selector import (
    fit_weighted_linear_selector,
    markdown_table,
    selector_prob,
)
from train_counterfactual_risk_selector import (
    label_counts,
    load_counterfactual_frame,
    reason_counts,
)


DEFAULT_RISK_FEATURES = [
    "warmup_c500_solved",
    "warmup_c1000_solved",
    "warmup_c2000_base_rho_std",
    "warmup_c2000_base_rho_range",
    "warmup_c2000_event_conf_learnt_log_max",
    "warmup_c2000_minus_warmup_c1000_delta_abs_mean",
    "warmup_c2000_minus_warmup_c1000_delta_mu_abs_mean",
    "warmup_c2000_minus_warmup_c1000_propagations",
    "warmup_c2000_event_entropy_norm",
    "warmup_c2000_event_top10_mass",
    "warmup_c1000_minus_warmup_c500_rho_event_top10_overlap",
    "warmup_c2000_minus_warmup_c1000_event_top05_mass",
]

DEFAULT_RECOVERY_FEATURES = [
    "warmup_c500_decisions",
    "warmup_c1000_decisions",
    "warmup_c2000_decisions",
    "warmup_c500_propagations",
    "warmup_c1000_propagations",
    "warmup_c2000_propagations",
    "warmup_c2000_cpu_time",
    "warmup_c2000_base_rho_mean",
    "warmup_c2000_base_rho_std",
    "warmup_c2000_base_rho_range",
    "warmup_c2000_delta_abs_mean",
    "warmup_c2000_delta_abs_max",
    "warmup_c2000_event_entropy_norm",
    "warmup_c2000_event_top10_mass",
    "warmup_c2000_rho_event_corr",
    "warmup_c2000_rho_event_top10_overlap",
    "warmup_c2000_event_conf_learnt_log_mean",
    "warmup_c2000_event_conf_learnt_log_max",
    "warmup_c1000_minus_warmup_c500_event_top10_mass",
    "warmup_c2000_minus_warmup_c1000_event_top10_mass",
    "warmup_c1000_minus_warmup_c500_rho_event_corr",
    "warmup_c2000_minus_warmup_c1000_rho_event_corr",
]


@dataclass(frozen=True)
class TwoStageMetrics:
    risk_threshold: float
    recovery_threshold: float
    selected_fraction: float
    base_solved: int
    adapter_solved: int
    selector_solved: int
    lost_solution: int
    recovered_timeout: int
    base_mean: float
    adapter_mean: float
    selector_mean: float


@dataclass
class MLPStageSelector:
    feature_names: list[str]
    mlp_weights: list
    mlp_biases: list
    threshold: float
    feature_mean: list[float]
    feature_std: list[float]


class TinyStageMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a two-stage risk controller from counterfactual traces.")
    parser.add_argument("--trace", action="append", required=True)
    parser.add_argument(
        "--checkpoint",
        default="runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt",
    )
    parser.add_argument(
        "--output-dir",
        default="runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350",
    )
    parser.add_argument(
        "--doc-path",
        default="docs/two_stage_risk_controller_multipoint_300350.md",
    )
    parser.add_argument("--risk-features", default=",".join(DEFAULT_RISK_FEATURES))
    parser.add_argument("--recovery-features", default=",".join(DEFAULT_RECOVERY_FEATURES))
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=0.005)
    parser.add_argument("--stage-model", choices=["linear", "mlp"], default="linear")
    parser.add_argument("--mlp-hidden-dim", type=int, default=8)
    parser.add_argument("--mlp-seed", type=int, default=0)
    parser.add_argument(
        "--recovery-label-mode",
        choices=["all_positive", "timeout_recovery", "timeout_recovery_with_speedup_aux"],
        default="all_positive",
        help=(
            "all_positive keeps the old labels. timeout_recovery trains recovery only on "
            "recovered_timeout positives and hard/timeout/risky negatives. "
            "timeout_recovery_with_speedup_aux also keeps hard_speedup as a weak positive."
        ),
    )
    parser.add_argument("--split-seeds", type=int, default=50)
    parser.add_argument("--train-fraction", type=float, default=0.5)
    parser.add_argument("--max-selected-fraction", type=float, default=0.12)
    parser.add_argument(
        "--stage-scope",
        choices=["all", "focused", "risk_all_recovery_focused", "risk_focused_recovery_all"],
        default="focused",
        help="focused trains risk on easy/medium base-solved rows and recovery on medium/hard/timeout rows.",
    )
    parser.add_argument(
        "--risk-train-sizes",
        default="",
        help="Optional comma-separated sizes used to train only the risk stage, e.g. 300,350.",
    )
    parser.add_argument(
        "--recovery-train-sizes",
        default="",
        help="Optional comma-separated sizes used to train only the recovery stage, e.g. 350,400.",
    )
    parser.add_argument(
        "--stability-csv",
        default="",
        help=(
            "Optional recovered_timeout stability summary CSV. "
            "Rows are matched by file_key/size/trace_path and recovered positives are downweighted."
        ),
    )
    parser.add_argument(
        "--stability-min-weight",
        type=float,
        default=0.15,
        help="Fallback lower bound for recovered_timeout stability weights.",
    )
    return parser.parse_args()


def parse_features(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def parse_size_filter(value: str) -> set[str]:
    return {name.strip() for name in value.split(",") if name.strip()}


def ordered_union(*feature_lists: list[str]) -> list[str]:
    return list(dict.fromkeys([name for features in feature_lists for name in features]))


def stage_selector_feature_union(
    adapter,
    risk_features: list[str],
    recovery_features: list[str],
) -> list[str]:
    slowdown_features = []
    if hasattr(adapter, "slowdown_selector_feature_names") and adapter.slowdown_selector_feature_names is not None:
        slowdown_features = [str(name) for name in adapter.slowdown_selector_feature_names]
    return ordered_union(risk_features, recovery_features, slowdown_features)


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


def add_two_stage_labels(frame: pd.DataFrame, recovery_label_mode: str = "all_positive") -> pd.DataFrame:
    frame = frame.copy()
    if "eligible" not in frame.columns:
        if "warmup_solved" in frame.columns:
            frame["eligible"] = ~frame["warmup_solved"].astype(bool)
        elif "warmup_result" in frame.columns:
            frame["eligible"] = ~frame["warmup_result"].fillna("INDETERMINATE").astype(str).isin(
                ["SATISFIABLE", "UNSATISFIABLE"]
            )
        else:
            frame["eligible"] = True
    reason = frame["counterfactual_reason"].fillna("neutral")
    klass = frame["counterfactual_class"].fillna("neutral")
    frame["base_bucket"] = frame.apply(base_bucket, axis=1)
    frame["risk_label"] = (klass == "negative").astype("float32")
    if recovery_label_mode == "all_positive":
        frame["recovery_label"] = (klass == "positive").astype("float32")
    elif recovery_label_mode in {"timeout_recovery", "timeout_recovery_with_speedup_aux"}:
        frame["recovery_label"] = np.nan
        frame.loc[reason == "recovered_timeout", "recovery_label"] = 1.0
        if recovery_label_mode == "timeout_recovery_with_speedup_aux":
            frame.loc[reason == "hard_speedup", "recovery_label"] = 1.0
        recovery_negatives = (
            reason.isin(["lost_solution", "easy_slowdown", "slowdown"])
            | (
                (reason == "neutral")
                & frame["base_bucket"].isin(["medium", "hard", "timeout"])
            )
        )
        frame.loc[recovery_negatives, "recovery_label"] = 0.0
    else:
        raise ValueError(f"Unknown recovery_label_mode={recovery_label_mode}")
    frame["risk_weight"] = 1.0
    frame["recovery_weight"] = 1.0
    frame.loc[reason == "lost_solution", "risk_weight"] = 40.0
    frame.loc[reason == "easy_slowdown", "risk_weight"] = 20.0
    frame.loc[reason == "slowdown", "risk_weight"] = 12.0
    frame.loc[klass == "positive", "risk_weight"] = 8.0
    frame.loc[reason == "recovered_timeout", "recovery_weight"] = 32.0
    frame.loc[reason == "hard_speedup", "recovery_weight"] = (
        4.0 if recovery_label_mode == "timeout_recovery_with_speedup_aux" else 2.0
    )
    frame.loc[reason == "lost_solution", "recovery_weight"] = 24.0
    frame.loc[reason == "easy_slowdown", "recovery_weight"] = 10.0
    frame.loc[reason == "slowdown", "recovery_weight"] = 8.0
    frame.loc[
        (reason == "neutral") & frame["base_bucket"].isin(["medium", "hard", "timeout"]),
        "recovery_weight",
    ] = 2.0
    frame["risk_train"] = frame["eligible"].astype(bool)
    frame["recovery_train"] = frame["eligible"].astype(bool) & frame["recovery_label"].notna()
    return frame


def _stability_file_key(path: str) -> str:
    return os.path.basename(str(path))


def _normalise_stability_size(value) -> str:
    if pd.isna(value):
        return "unknown"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def apply_recovery_stability_weights(
    frame: pd.DataFrame,
    stability_csv: str,
    min_weight: float,
) -> pd.DataFrame:
    if not stability_csv:
        frame = frame.copy()
        frame["recovery_stability_weight"] = 1.0
        frame["recovery_stability_weight_raw"] = 1.0
        frame["recovered_rate"] = np.nan
        frame["stable_recovered"] = np.nan
        return frame
    stability = pd.read_csv(stability_csv)
    if stability.empty:
        raise ValueError(f"Stability CSV is empty: {stability_csv}")
    if "recovery_stability_weight" not in stability.columns:
        if "recovered_rate" not in stability.columns:
            raise ValueError("Stability CSV must contain recovery_stability_weight or recovered_rate")
        stability["recovery_stability_weight"] = stability["recovered_rate"]
    if "file_key" not in stability.columns and "file" in stability.columns:
        stability["file_key"] = stability["file"].map(_stability_file_key)
    if "size" in stability.columns:
        stability["size"] = stability["size"].map(_normalise_stability_size)
    keep = [
        column
        for column in [
            "trace_path",
            "size",
            "file_key",
            "recovered_rate",
            "recovery_stability_weight_raw",
            "recovery_stability_weight",
            "stable_recovered",
            "repeats",
        ]
        if column in stability.columns
    ]
    stability = stability[keep].copy()
    stability["recovery_stability_weight"] = (
        pd.to_numeric(stability["recovery_stability_weight"], errors="coerce")
        .fillna(float(min_weight))
        .clip(lower=float(min_weight), upper=1.0)
    )
    if "recovery_stability_weight_raw" in stability.columns:
        stability["recovery_stability_weight_raw"] = pd.to_numeric(
            stability["recovery_stability_weight_raw"],
            errors="coerce",
        )
    else:
        stability["recovery_stability_weight_raw"] = stability["recovery_stability_weight"]

    frame = frame.copy()
    frame["file_key"] = frame["file"].map(_stability_file_key)
    frame["size"] = frame["size"].map(_normalise_stability_size)
    merge_keys = ["size", "file_key"]
    if "trace_path" in frame.columns and "trace_path" in stability.columns:
        merge_keys = ["trace_path", *merge_keys]
    stability = stability.drop_duplicates(subset=merge_keys, keep="last")
    frame = frame.merge(stability, on=merge_keys, how="left")
    frame["recovery_stability_weight"] = frame["recovery_stability_weight"].fillna(1.0)
    frame["recovery_stability_weight_raw"] = frame["recovery_stability_weight_raw"].fillna(1.0)
    reason = frame["counterfactual_reason"].fillna("neutral")
    recovered = reason == "recovered_timeout"
    frame.loc[recovered, "recovery_weight"] = (
        frame.loc[recovered, "recovery_weight"].astype(float)
        * frame.loc[recovered, "recovery_stability_weight"].astype(float)
    )
    return frame


def base_bucket(row: pd.Series) -> str:
    if not bool(row["base_solved"]):
        return "timeout"
    base_time = float(row["base_time"])
    if base_time < 10.0:
        return "easy"
    if base_time < 30.0:
        return "medium"
    return "hard"


def apply_stage_scope(frame: pd.DataFrame, stage_scope: str) -> pd.DataFrame:
    frame = frame.copy()
    base_risk_train = frame["risk_train"].astype(bool)
    base_recovery_train = frame["recovery_train"].astype(bool)
    if stage_scope == "all":
        frame["risk_train"] = base_risk_train
        frame["recovery_train"] = base_recovery_train
        return frame
    base_solved = frame["base_solved"].astype(bool)
    easy_medium = frame["base_bucket"].isin(["easy", "medium"])
    medium_hard_timeout = frame["base_bucket"].isin(["medium", "hard", "timeout"])
    if stage_scope == "focused":
        frame["risk_train"] = base_risk_train & base_solved & easy_medium
        frame["recovery_train"] = base_recovery_train & medium_hard_timeout
        return frame
    if stage_scope == "risk_all_recovery_focused":
        frame["risk_train"] = base_risk_train
        frame["recovery_train"] = base_recovery_train & medium_hard_timeout
        return frame
    if stage_scope == "risk_focused_recovery_all":
        frame["risk_train"] = base_risk_train & base_solved & easy_medium
        frame["recovery_train"] = base_recovery_train
        return frame
    raise ValueError(f"Unknown stage_scope={stage_scope}")


def apply_stage_size_filter(
    frame: pd.DataFrame,
    risk_sizes: set[str],
    recovery_sizes: set[str],
) -> pd.DataFrame:
    frame = frame.copy()
    sizes = frame["size"].astype(str)
    if risk_sizes:
        frame["risk_train"] = frame["risk_train"].astype(bool) & sizes.isin(risk_sizes)
    if recovery_sizes:
        frame["recovery_train"] = frame["recovery_train"].astype(bool) & sizes.isin(recovery_sizes)
    return frame


def fit_weighted_mlp_selector(
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_weights: torch.Tensor,
    feature_names: list[str],
    epochs: int,
    lr: float,
    l2: float,
    hidden_dim: int,
    seed: int,
) -> tuple[MLPStageSelector, torch.Tensor]:
    features = features.to(dtype=torch.float32)
    labels = labels.to(dtype=torch.float32).view(-1)
    sample_weights = sample_weights.to(dtype=torch.float32).view(-1)
    mean = features.mean(dim=0)
    std = features.std(dim=0, unbiased=False).clamp_min(1.0e-6)
    x = (features - mean) / std

    torch.manual_seed(int(seed))
    model = TinyStageMLP(input_dim=features.shape[1], hidden_dim=int(hidden_dim))
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(lr), weight_decay=0.0)

    for _ in range(int(epochs)):
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits,
            labels,
            reduction="none",
        )
        loss = (loss * sample_weights).sum() / sample_weights.sum().clamp_min(1.0)
        if l2 > 0:
            penalty = torch.zeros((), dtype=torch.float32)
            for param in model.parameters():
                penalty = penalty + param.pow(2).mean()
            loss = loss + float(l2) * penalty
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        probs = torch.sigmoid(model(x))
    linear_layers = [module for module in model.net if isinstance(module, nn.Linear)]
    selector = MLPStageSelector(
        feature_names=list(feature_names),
        mlp_weights=[
            [[float(value) for value in row] for row in layer.weight.detach().tolist()]
            for layer in linear_layers
        ],
        mlp_biases=[
            [float(value) for value in layer.bias.detach().tolist()]
            for layer in linear_layers
        ],
        threshold=0.5,
        feature_mean=[float(value) for value in mean.tolist()],
        feature_std=[float(value) for value in std.tolist()],
    )
    return selector, probs


def stage_selector_prob(selector, values: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(selector.feature_mean, dtype=torch.float32)
    std = torch.tensor(selector.feature_std, dtype=torch.float32).clamp_min(1.0e-6)
    x = (values.to(dtype=torch.float32) - mean) / std
    if hasattr(selector, "mlp_weights"):
        for layer_idx, (weights, biases) in enumerate(zip(selector.mlp_weights, selector.mlp_biases)):
            weight = torch.tensor(weights, dtype=torch.float32)
            bias = torch.tensor(biases, dtype=torch.float32)
            x = x.matmul(weight.t()) + bias
            if layer_idx + 1 < len(selector.mlp_weights):
                x = torch.relu(x)
        return torch.sigmoid(x.view(-1))
    return selector_prob(selector, values)


def fit_stage(
    frame: pd.DataFrame,
    feature_names: list[str],
    label_column: str,
    weight_column: str,
    train_mask_column: str,
    epochs: int,
    lr: float,
    l2: float,
    stage_model: str,
    mlp_hidden_dim: int,
    seed: int,
):
    train_frame = frame[frame[train_mask_column].astype(bool)].copy()
    if train_frame[label_column].nunique(dropna=True) < 2:
        raise ValueError(f"Need both labels to train {label_column}")
    train_features = feature_tensor(train_frame, feature_names)
    train_labels = column_tensor(train_frame, label_column)
    train_weights = column_tensor(train_frame, weight_column)
    if stage_model == "mlp":
        selector, _ = fit_weighted_mlp_selector(
            train_features,
            train_labels,
            train_weights,
            feature_names=feature_names,
            epochs=epochs,
            lr=lr,
            l2=l2,
            hidden_dim=mlp_hidden_dim,
            seed=seed,
        )
    else:
        selector, _ = fit_weighted_linear_selector(
            train_features,
            train_labels,
            train_weights,
            feature_names=feature_names,
            epochs=epochs,
            lr=lr,
            l2=l2,
        )
    probs = stage_selector_prob(
        selector,
        feature_tensor(frame, feature_names),
    )
    return selector, probs


def apply_two_stage(
    frame: pd.DataFrame,
    risk_probs: torch.Tensor,
    recovery_probs: torch.Tensor,
    risk_threshold: float,
    recovery_threshold: float,
) -> pd.DataFrame:
    selected = frame.copy()
    selected["risk_prob"] = risk_probs.detach().cpu().numpy()
    selected["recovery_prob"] = recovery_probs.detach().cpu().numpy()
    use_adapter = (
        selected["eligible"].astype(bool).to_numpy()
        & (selected["risk_prob"].to_numpy() < float(risk_threshold))
        & (selected["recovery_prob"].to_numpy() >= float(recovery_threshold))
    )
    selected["selector_use_adapter"] = use_adapter.astype("int64")
    selected["selector_time"] = np.where(use_adapter, selected["adapter_time"], selected["base_time"])
    selected["selector_solved"] = np.where(use_adapter, selected["adapter_solved"], selected["base_solved"])
    selected["selector_lost_solution"] = (
        selected["base_solved"].astype(bool).to_numpy()
        & use_adapter
        & ~selected["adapter_solved"].astype(bool).to_numpy()
    )
    selected["selector_recovered_timeout"] = (
        ~selected["base_solved"].astype(bool).to_numpy()
        & use_adapter
        & selected["adapter_solved"].astype(bool).to_numpy()
    )
    return selected


def metrics_for(
    frame: pd.DataFrame,
    risk_probs: torch.Tensor,
    recovery_probs: torch.Tensor,
    risk_threshold: float,
    recovery_threshold: float,
) -> TwoStageMetrics:
    selected = apply_two_stage(frame, risk_probs, recovery_probs, risk_threshold, recovery_threshold)
    eligible = selected[selected["eligible"]].copy()
    return TwoStageMetrics(
        risk_threshold=float(risk_threshold),
        recovery_threshold=float(recovery_threshold),
        selected_fraction=float(eligible["selector_use_adapter"].mean()),
        base_solved=int(eligible["base_solved"].sum()),
        adapter_solved=int(eligible["adapter_solved"].sum()),
        selector_solved=int(eligible["selector_solved"].sum()),
        lost_solution=int(eligible["selector_lost_solution"].sum()),
        recovered_timeout=int(eligible["selector_recovered_timeout"].sum()),
        base_mean=float(eligible["base_time"].mean()),
        adapter_mean=float(eligible["adapter_time"].mean()),
        selector_mean=float(eligible["selector_time"].mean()),
    )


def choose_two_stage_thresholds(
    frame: pd.DataFrame,
    risk_probs: torch.Tensor,
    recovery_probs: torch.Tensor,
    max_selected_fraction: float,
) -> tuple[float, float, TwoStageMetrics]:
    risk_candidates = threshold_candidates(risk_probs)
    recovery_candidates = threshold_candidates(recovery_probs)
    best = None
    best_score = None
    for risk_threshold in risk_candidates:
        for recovery_threshold in recovery_candidates:
            metrics = metrics_for(frame, risk_probs, recovery_probs, risk_threshold, recovery_threshold)
            if metrics.selected_fraction > float(max_selected_fraction):
                continue
            score = (
                -metrics.lost_solution,
                metrics.recovered_timeout,
                metrics.selector_solved - metrics.base_solved,
                -metrics.selector_mean,
                -metrics.selected_fraction,
            )
            if best_score is None or score > best_score:
                best = (risk_threshold, recovery_threshold, metrics)
                best_score = score
    if best is None:
        risk_threshold = 0.0
        recovery_threshold = 1.000001
        return risk_threshold, recovery_threshold, metrics_for(frame, risk_probs, recovery_probs, risk_threshold, recovery_threshold)
    return best


def threshold_candidates(probabilities: torch.Tensor, num_quantiles: int = 25) -> list[float]:
    values = probabilities.detach().cpu().numpy().astype(float)
    if values.size == 0:
        return [0.0, 0.5, 1.0, 1.000001]
    quantiles = np.quantile(values, np.linspace(0.0, 1.0, int(num_quantiles)))
    candidates = {0.0, 0.5, 1.0, 1.000001}
    candidates.update(float(value) for value in quantiles)
    return sorted(candidates)


def fit_two_stage_for_frame(
    frame: pd.DataFrame,
    risk_features: list[str],
    recovery_features: list[str],
    epochs: int,
    lr: float,
    l2: float,
    max_selected_fraction: float,
    stage_model: str,
    mlp_hidden_dim: int,
    seed: int,
):
    risk_selector, risk_probs = fit_stage(
        frame,
        feature_names=risk_features,
        label_column="risk_label",
        weight_column="risk_weight",
        train_mask_column="risk_train",
        epochs=epochs,
        lr=lr,
        l2=l2,
        stage_model=stage_model,
        mlp_hidden_dim=mlp_hidden_dim,
        seed=seed,
    )
    recovery_selector, recovery_probs = fit_stage(
        frame,
        feature_names=recovery_features,
        label_column="recovery_label",
        weight_column="recovery_weight",
        train_mask_column="recovery_train",
        epochs=epochs,
        lr=lr,
        l2=l2,
        stage_model=stage_model,
        mlp_hidden_dim=mlp_hidden_dim,
        seed=seed + 1,
    )
    risk_threshold, recovery_threshold, train_metrics = choose_two_stage_thresholds(
        frame,
        risk_probs,
        recovery_probs,
        max_selected_fraction=max_selected_fraction,
    )
    risk_selector.threshold = float(risk_threshold)
    recovery_selector.threshold = float(recovery_threshold)
    return risk_selector, recovery_selector, risk_probs, recovery_probs, train_metrics


def repeated_split_diagnostic(
    frame: pd.DataFrame,
    risk_features: list[str],
    recovery_features: list[str],
    seeds: int,
    train_fraction: float,
    epochs: int,
    lr: float,
    l2: float,
    max_selected_fraction: float,
    stage_model: str,
    mlp_hidden_dim: int,
    mlp_seed: int,
) -> pd.DataFrame:
    rows = []
    eligible_index = frame.index[frame["eligible"]].to_numpy()
    for seed in range(1729, 1729 + int(seeds)):
        rng = np.random.default_rng(seed)
        train_indices = []
        heldout_indices = []
        for _, group in frame.loc[eligible_index].groupby("size", sort=True):
            idx = group.index.to_numpy()
            n_train = max(1, min(len(idx) - 1, int(round(float(train_fraction) * len(idx)))))
            chosen = rng.choice(idx, size=n_train, replace=False)
            train_indices.extend(chosen.tolist())
            heldout_indices.extend(sorted(set(idx.tolist()).difference(chosen.tolist())))
        train = frame.loc[train_indices].copy()
        heldout = frame.loc[heldout_indices].copy()
        if (
            train[train["risk_train"].astype(bool)]["risk_label"].nunique(dropna=True) < 2
            or train[train["recovery_train"].astype(bool)]["recovery_label"].nunique(dropna=True) < 2
        ):
            continue
        risk_selector, recovery_selector, _, _, train_metrics = fit_two_stage_for_frame(
            train,
            risk_features=risk_features,
            recovery_features=recovery_features,
            epochs=epochs,
            lr=lr,
            l2=l2,
            max_selected_fraction=max_selected_fraction,
            stage_model=stage_model,
            mlp_hidden_dim=mlp_hidden_dim,
            seed=mlp_seed + seed,
        )
        heldout_risk_probs = stage_selector_prob(
            risk_selector,
            feature_tensor(heldout, risk_features),
        )
        heldout_recovery_probs = stage_selector_prob(
            recovery_selector,
            feature_tensor(heldout, recovery_features),
        )
        selected = apply_two_stage(
            heldout,
            heldout_risk_probs,
            heldout_recovery_probs,
            risk_selector.threshold,
            recovery_selector.threshold,
        )
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
                    "risk_threshold": float(risk_selector.threshold),
                    "recovery_threshold": float(recovery_selector.threshold),
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


def metrics_frame(metrics: TwoStageMetrics) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "risk_threshold": metrics.risk_threshold,
                "recovery_threshold": metrics.recovery_threshold,
                "selected_fraction": metrics.selected_fraction,
                "base_solved": metrics.base_solved,
                "adapter_solved": metrics.adapter_solved,
                "selector_solved": metrics.selector_solved,
                "delta_solved_vs_base": metrics.selector_solved - metrics.base_solved,
                "delta_solved_vs_adapter": metrics.selector_solved - metrics.adapter_solved,
                "lost_solution": metrics.lost_solution,
                "recovered_timeout": metrics.recovered_timeout,
                "selector_mean": metrics.selector_mean,
                "delta_vs_base": metrics.selector_mean - metrics.base_mean,
            }
        ]
    )


def stage_count_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for stage, mask_column, label_column in [
        ("risk", "risk_train", "risk_label"),
        ("recovery", "recovery_train", "recovery_label"),
    ]:
        subset = frame[frame[mask_column].astype(bool)]
        rows.append(
            {
                "stage": stage,
                "n": int(len(subset)),
                "positive": int((subset[label_column] == 1.0).sum()),
                "negative": int((subset[label_column] == 0.0).sum()),
            }
        )
    return pd.DataFrame(rows)


def save_two_stage_checkpoint(
    checkpoint: str,
    output_dir: str,
    risk_selector,
    recovery_selector,
    stage_model: str,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    shutil.copy2(checkpoint, os.path.join(output_dir, "best.pt"))
    cfg_path = os.path.join(os.path.dirname(checkpoint), "config.yaml")
    cfg = OmegaConf.load(cfg_path)
    adapter = cfg.model.event_adapter
    union_features = stage_selector_feature_union(
        adapter,
        risk_features=risk_selector.feature_names,
        recovery_features=recovery_selector.feature_names,
    )
    adapter.selector_mode = "two_stage_mlp" if stage_model == "mlp" else "two_stage"
    adapter.selector_feature_names = union_features
    adapter.selector_weights = None
    adapter.selector_bias = 0.0
    adapter.selector_threshold = 0.5
    adapter.selector_feature_mean = None
    adapter.selector_feature_std = None
    adapter.risk_selector_feature_names = risk_selector.feature_names
    adapter.risk_selector_weights = (
        None if stage_model == "mlp" else risk_selector.weights
    )
    adapter.risk_selector_bias = (
        0.0 if stage_model == "mlp" else risk_selector.bias
    )
    adapter.risk_selector_threshold = risk_selector.threshold
    adapter.risk_selector_feature_mean = risk_selector.feature_mean
    adapter.risk_selector_feature_std = risk_selector.feature_std
    adapter.risk_selector_mlp_weights = (
        risk_selector.mlp_weights if stage_model == "mlp" else None
    )
    adapter.risk_selector_mlp_biases = (
        risk_selector.mlp_biases if stage_model == "mlp" else None
    )
    adapter.recovery_selector_feature_names = recovery_selector.feature_names
    adapter.recovery_selector_weights = (
        None if stage_model == "mlp" else recovery_selector.weights
    )
    adapter.recovery_selector_bias = (
        0.0 if stage_model == "mlp" else recovery_selector.bias
    )
    adapter.recovery_selector_threshold = recovery_selector.threshold
    adapter.recovery_selector_feature_mean = recovery_selector.feature_mean
    adapter.recovery_selector_feature_std = recovery_selector.feature_std
    adapter.recovery_selector_mlp_weights = (
        recovery_selector.mlp_weights if stage_model == "mlp" else None
    )
    adapter.recovery_selector_mlp_biases = (
        recovery_selector.mlp_biases if stage_model == "mlp" else None
    )
    adapter.base_rho_gate_threshold = None
    adapter.graph_gate_indices = None
    adapter.graph_gate_threshold = None
    OmegaConf.save(cfg, os.path.join(output_dir, "config.yaml"))


def write_doc(
    path: str,
    risk_features: list[str],
    recovery_features: list[str],
    stage_scope: str,
    stage_model: str,
    mlp_hidden_dim: int,
    recovery_label_mode: str,
    risk_train_sizes: set[str],
    recovery_train_sizes: set[str],
    counts: pd.DataFrame,
    reasons: pd.DataFrame,
    train_metrics: TwoStageMetrics,
    split_summary: pd.DataFrame,
    stage_counts: pd.DataFrame,
    stability_csv: str,
    stability_summary: pd.DataFrame,
) -> None:
    columns_counts = ["size", "n", "eligible", "positive", "negative", "neutral", "warmup_solved"]
    columns_train = [
        "risk_threshold",
        "recovery_threshold",
        "selected_fraction",
        "base_solved",
        "adapter_solved",
        "selector_solved",
        "delta_solved_vs_base",
        "lost_solution",
        "recovered_timeout",
        "selector_mean",
        "delta_vs_base",
    ]
    columns_split = [
        "heldout",
        "selected_fraction_mean",
        "selector_delta_solved_vs_base_mean",
        "lost_solution_mean",
        "recovered_timeout_mean",
        "selector_delta_vs_base_mean",
        "keeps_base_solved_rate",
        "beats_base_time_rate",
    ]
    doc = [
        "# 双阶段风险控制器",
        "",
        "该 selector 分成两个 head：",
        "",
        "- easy-risk gate：预测 adapter 是否可能造成 lost/slowdown，触发后直接 fallback；",
        "- hard-recovery detector：预测 adapter 是否可能恢复 timeout 或明显加速 hard instance。",
        "",
        "最终策略是：`use_adapter = recovery_detector && !risk_gate`。",
        "",
        f"训练作用域：`{stage_scope}`。",
        f"阶段模型：`{stage_model}`。",
        f"MLP hidden dim：`{mlp_hidden_dim}`。" if stage_model == "mlp" else "",
        f"recovery 标签模式：`{recovery_label_mode}`。",
        f"risk 训练 size filter：`{','.join(sorted(risk_train_sizes)) or 'all'}`。",
        f"recovery 训练 size filter：`{','.join(sorted(recovery_train_sizes)) or 'all'}`。",
        f"recovered_timeout 稳定性标注：`{stability_csv or '未使用'}`。",
        "",
        "## 阶段训练样本计数",
        "",
        markdown_table(stage_counts, ["stage", "n", "positive", "negative"]),
        "",
        "## recovered_timeout 稳定性权重",
        "",
        markdown_table(
            stability_summary,
            ["size", "n", "stable_recovered", "recovered_rate_mean", "stability_weight_mean"],
        ) if not stability_summary.empty else "_未接入稳定性标注_",
        "",
        "## Risk Gate 特征",
        "",
        "- " + "\n- ".join(risk_features),
        "",
        "## Recovery Detector 特征",
        "",
        "- " + "\n- ".join(recovery_features),
        "",
        "## 标签计数",
        "",
        markdown_table(counts, columns_counts),
        "",
        "## 标签原因计数",
        "",
        markdown_table(reasons, ["size", "reason", "count"]) if not reasons.empty else "_无 counterfactual_reason 字段_",
        "",
        "## 全数据拟合",
        "",
        markdown_table(metrics_frame(train_metrics), columns_train),
        "",
        "## Repeated-Split 诊断",
        "",
        markdown_table(split_summary[columns_split], columns_split) if not split_summary.empty else "_split 数量不足_",
        "",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n")


def main() -> None:
    args = parse_args()
    risk_features = parse_features(args.risk_features)
    recovery_features = parse_features(args.recovery_features)
    union_features = ordered_union(risk_features, recovery_features)
    if not risk_features or not recovery_features:
        raise ValueError("Both risk and recovery feature lists are required")

    model, _, _ = load_checkpoint(args.checkpoint, var_output=True)
    model.event_adapter_selector_feature_names = []
    model.event_adapter_base_rho_gate_threshold = None
    model.event_adapter_graph_gate_indices = []
    model.event_adapter_graph_gate_threshold = None

    frame = load_counterfactual_frame(
        model=model,
        trace_paths=args.trace,
        feature_names=union_features,
        batch_size=args.batch_size,
        negative_weight_scale=1.0,
    )
    frame = add_two_stage_labels(frame, recovery_label_mode=args.recovery_label_mode)
    frame = apply_recovery_stability_weights(
        frame,
        stability_csv=args.stability_csv,
        min_weight=float(args.stability_min_weight),
    )
    frame = apply_stage_scope(frame, args.stage_scope)
    risk_train_sizes = parse_size_filter(args.risk_train_sizes)
    recovery_train_sizes = parse_size_filter(args.recovery_train_sizes)
    frame = apply_stage_size_filter(
        frame,
        risk_sizes=risk_train_sizes,
        recovery_sizes=recovery_train_sizes,
    )
    risk_selector, recovery_selector, risk_probs, recovery_probs, train_metrics = fit_two_stage_for_frame(
        frame[frame["eligible"]].copy(),
        risk_features=risk_features,
        recovery_features=recovery_features,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        max_selected_fraction=args.max_selected_fraction,
        stage_model=args.stage_model,
        mlp_hidden_dim=args.mlp_hidden_dim,
        seed=args.mlp_seed,
    )
    selected = apply_two_stage(
        frame[frame["eligible"]].copy(),
        risk_probs,
        recovery_probs,
        risk_selector.threshold,
        recovery_selector.threshold,
    )
    split_rows = repeated_split_diagnostic(
        frame,
        risk_features=risk_features,
        recovery_features=recovery_features,
        seeds=args.split_seeds,
        train_fraction=args.train_fraction,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        max_selected_fraction=args.max_selected_fraction,
        stage_model=args.stage_model,
        mlp_hidden_dim=args.mlp_hidden_dim,
        mlp_seed=args.mlp_seed,
    )
    split_summary = aggregate_splits(split_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_two_stage_checkpoint(
        args.checkpoint,
        args.output_dir,
        risk_selector=risk_selector,
        recovery_selector=recovery_selector,
        stage_model=args.stage_model,
    )
    frame.to_csv(output_dir / "two_stage_training_frame.csv", index=False)
    selected.to_csv(output_dir / "two_stage_all_data_policy.csv", index=False)
    split_rows.to_csv(output_dir / "two_stage_repeated_splits.csv", index=False)
    split_summary.to_csv(output_dir / "two_stage_repeated_split_summary.csv", index=False)
    stability_summary = pd.DataFrame()
    if args.stability_csv:
        recovered_frame = frame[frame["counterfactual_reason"].eq("recovered_timeout")].copy()
        if not recovered_frame.empty:
            stability_summary = (
                recovered_frame.groupby("size", sort=True)
                .agg(
                    n=("file_key", "count"),
                    stable_recovered=(
                        "stable_recovered",
                        lambda values: int(
                            pd.Series(values)
                            .map(lambda value: bool(value) if not pd.isna(value) else False)
                            .sum()
                        ),
                    ),
                    recovered_rate_mean=("recovered_rate", "mean"),
                    stability_weight_mean=("recovery_stability_weight", "mean"),
                )
                .reset_index()
            )
            stability_summary.to_csv(output_dir / "recovered_timeout_stability_weight_summary.csv", index=False)
    write_doc(
        args.doc_path,
        risk_features=risk_features,
        recovery_features=recovery_features,
        stage_scope=args.stage_scope,
        stage_model=args.stage_model,
        mlp_hidden_dim=args.mlp_hidden_dim,
        recovery_label_mode=args.recovery_label_mode,
        risk_train_sizes=risk_train_sizes,
        recovery_train_sizes=recovery_train_sizes,
        counts=label_counts(frame),
        reasons=reason_counts(frame),
        train_metrics=train_metrics,
        split_summary=split_summary,
        stage_counts=stage_count_frame(frame),
        stability_csv=args.stability_csv,
        stability_summary=stability_summary,
    )

    print(f"risk features: {risk_selector.feature_names}")
    print(f"stage model: {args.stage_model}")
    print(f"recovery label mode: {args.recovery_label_mode}")
    print(f"stability csv: {args.stability_csv or 'none'}")
    print(f"risk train sizes: {sorted(risk_train_sizes) if risk_train_sizes else 'all'}")
    print(f"recovery train sizes: {sorted(recovery_train_sizes) if recovery_train_sizes else 'all'}")
    print(f"risk threshold: {risk_selector.threshold:.6f}")
    print(f"recovery features: {recovery_selector.feature_names}")
    print(f"recovery threshold: {recovery_selector.threshold:.6f}")
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
