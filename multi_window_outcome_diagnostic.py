from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from torch_geometric.loader import DataLoader

from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch
from summarize_contrastive_outcome_selector import (
    ContrastiveSpec,
    attach_contrastive_labels,
    choose_contrastive_threshold,
)
from summarize_risk_controller_selector import (
    ADAPTER_PATH,
    ALL_FEATURES,
    BASE_PATH,
    CHECKPOINT,
    FEATURE_CACHE,
    MICRO_FEATURES,
    OUT_DIR,
    SEEDS,
    SIZES,
    fit_weighted_linear_selector,
    markdown_table,
    selector_prob,
    summarize_policy,
)
from train_adapter_selector import extract_selector_features


WINDOWS = [100, 500, 1000]
DOC_PATH = Path("docs/multi_window_outcome_diagnostic.md")
PREFIX = "mw"


def window_cache_path(conflicts: int) -> Path:
    return OUT_DIR / f"multi_window_features_conf{conflicts}.csv"


def feature_cache_is_valid(path: Path) -> bool:
    if not path.exists():
        return False
    columns = set(pd.read_csv(path, nrows=1).columns)
    required = {"size", "cnf_id", *ALL_FEATURES}
    return required.issubset(columns)


def build_window_feature_cache(conflicts: int) -> pd.DataFrame:
    if conflicts == 500 and feature_cache_is_valid(FEATURE_CACHE):
        frame = pd.read_csv(FEATURE_CACHE)
        frame.to_csv(window_cache_path(conflicts), index=False)
        return frame

    model, transform, model_cfg = load_checkpoint(str(CHECKPOINT), var_output=True)
    if not getattr(model, "event_adapter_enabled", False):
        raise ValueError("Multi-window feature extraction requires an event-adapter checkpoint")
    model.eval()

    frames = []
    for size in SIZES:
        dataset_path = f"data/test/3sat/{size}/*.cnf"
        dataset = DimacsCNFDataset(path=dataset_path, transform=transform, lazy=True)
        loader = DataLoader(dataset=dataset, batch_size=20, num_workers=0, shuffle=False)
        warmup_data = sample_var_params(
            model=model,
            loader=loader,
            device="cpu",
            use_mode=True,
            num_samples=1,
            scale_sigma=model_cfg.scale_sigma,
            add_timing=True,
            cache_var_features=True,
        )
        warmup_params = apply_rollout_budget(
            dict(model_cfg.solver.params),
            budget_type="conflicts",
            cpu_lim=10.0,
            conflicts=conflicts,
        )
        warmup_params["collect-events"] = True
        warmup_stats = compute_solver_stats(
            dataset=dataset,
            data_list=warmup_data,
            num_workers=8,
            solver=model_cfg.solver.solver,
            **warmup_params,
        )
        refined_graphs = attach_var_event_state_batch(
            warmup_data,
            warmup_stats,
            var_state_dim=model.var_state_dim,
            momentum=0.5,
            feature_mode="enhanced",
        )
        feature_loader = DataLoader(dataset=refined_graphs, batch_size=20, num_workers=0, shuffle=False)
        frame = extract_selector_features(model, feature_loader, ALL_FEATURES)
        frame["size"] = size
        frame["selector_dataset"] = dataset_path
        frames.append(frame)

    feature_frame = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_frame.to_csv(window_cache_path(conflicts), index=False)
    return feature_frame


def load_window_features(conflicts: int) -> pd.DataFrame:
    path = window_cache_path(conflicts)
    if feature_cache_is_valid(path):
        return pd.read_csv(path)
    return build_window_feature_cache(conflicts)


def base_outcome_frame() -> pd.DataFrame:
    frames = []
    for size in SIZES:
        base = pd.read_csv(BASE_PATH.format(size=size))[
            ["cnf_id", "time", "Result", "conflicts", "decisions"]
        ].rename(
            columns={
                "time": "base_time",
                "Result": "base_result",
                "conflicts": "base_conflicts",
                "decisions": "base_decisions",
            }
        )
        adapter = pd.read_csv(ADAPTER_PATH.format(size=size))[
            ["cnf_id", "time", "Result", "conflicts", "decisions"]
        ].rename(
            columns={
                "time": "adapter_time",
                "Result": "adapter_result",
                "conflicts": "adapter_conflicts",
                "decisions": "adapter_decisions",
            }
        )
        frame = base.merge(adapter, on="cnf_id", how="inner")
        frame["size"] = size
        frame["base_solved"] = frame["base_result"] != "INDETERMINATE"
        frame["adapter_solved"] = frame["adapter_result"] != "INDETERMINATE"
        frame["gain"] = frame["base_time"] - frame["adapter_time"]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build_multi_window_frame() -> pd.DataFrame:
    frame = base_outcome_frame()
    for conflicts in WINDOWS:
        features = load_window_features(conflicts)
        keep = ["size", "cnf_id", *ALL_FEATURES]
        renamed = features[keep].rename(
            columns={name: f"{PREFIX}_{conflicts}_{name}" for name in ALL_FEATURES}
        )
        frame = frame.merge(renamed, on=["size", "cnf_id"], how="inner")

    frame["base_rho_mean"] = frame[f"{PREFIX}_500_base_rho_mean"]
    frame["num_vars_log"] = frame[f"{PREFIX}_500_num_vars_log"]
    for feature in MICRO_FEATURES:
        frame[f"d100_500_{feature}"] = frame[f"{PREFIX}_500_{feature}"] - frame[f"{PREFIX}_100_{feature}"]
        frame[f"d500_1000_{feature}"] = frame[f"{PREFIX}_1000_{feature}"] - frame[f"{PREFIX}_500_{feature}"]
    return attach_contrastive_labels(frame, ContrastiveSpec())


def feature_sets() -> dict[str, list[str]]:
    abs_features = [f"{PREFIX}_{window}_{feature}" for window in WINDOWS for feature in MICRO_FEATURES]
    drift_features = [
        f"{delta}_{feature}"
        for delta in ["d100_500", "d500_1000"]
        for feature in MICRO_FEATURES
    ]
    return {
        "base_rho": ["base_rho_mean"],
        "best_drift_corr": ["d100_500_rho_event_corr"],
        "base_plus_best_drift_corr": ["base_rho_mean", "d100_500_rho_event_corr"],
        "single_500": ["base_rho_mean", *[f"{PREFIX}_500_{feature}" for feature in MICRO_FEATURES]],
        "multi_abs": ["base_rho_mean", *abs_features],
        "multi_drift": ["base_rho_mean", *drift_features],
        "multi_full": ["base_rho_mean", *abs_features, *drift_features],
    }


def safe_auc(labels: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    if len(np.unique(labels)) < 2:
        return float("nan"), float("nan")
    auc = float(roc_auc_score(labels, scores))
    return auc, max(auc, 1.0 - auc)


def univariate_auc(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    labelled = frame[frame["contrastive_class"] != "neutral"].copy()
    labels = labelled["contrastive_label"].to_numpy(dtype=np.float32)
    rows = []
    for feature in feature_names:
        scores = labelled[feature].to_numpy(dtype=np.float32)
        auc, separability_auc = safe_auc(labels, scores)
        rows.append(
            {
                "feature": feature,
                "auc": auc,
                "separability_auc": separability_auc,
                "positive_mean": float(labelled.loc[labelled["contrastive_label"] == 1.0, feature].mean()),
                "negative_mean": float(labelled.loc[labelled["contrastive_label"] == 0.0, feature].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("separability_auc", ascending=False)


def repeated_split_rows(frame: pd.DataFrame, feature_name_sets: dict[str, list[str]]) -> list[dict[str, object]]:
    rows = []
    for feature_set_name, names in feature_name_sets.items():
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            train_indices = []
            heldout_indices = []
            for size in SIZES:
                size_indices = frame.index[frame["size"] == size].to_numpy()
                chosen = rng.choice(size_indices, size=100, replace=False)
                train_indices.extend(chosen.tolist())
                heldout_indices.extend(sorted(set(size_indices.tolist()).difference(chosen.tolist())))

            train = frame.loc[train_indices].copy()
            heldout = frame.loc[heldout_indices].copy()
            labelled = train[train["contrastive_class"] != "neutral"].copy()
            if labelled["contrastive_label"].nunique(dropna=True) < 2:
                continue
            train_features = torch.tensor(labelled[names].to_numpy(), dtype=torch.float32)
            selector, _ = fit_weighted_linear_selector(
                train_features,
                torch.tensor(labelled["contrastive_label"].to_numpy(), dtype=torch.float32),
                torch.tensor(labelled["contrastive_weight"].to_numpy(), dtype=torch.float32),
                feature_names=names,
                epochs=1000,
                lr=0.05,
                l2=1.0e-3,
            )
            train_all_features = torch.tensor(train[names].to_numpy(), dtype=torch.float32)
            train_probs = selector_prob(selector, train_all_features)
            threshold, train_metrics = choose_contrastive_threshold(train, train_probs)
            heldout_features = torch.tensor(heldout[names].to_numpy(), dtype=torch.float32)
            heldout_probs = selector_prob(selector, heldout_features)
            heldout_labelled = heldout[heldout["contrastive_class"] != "neutral"].copy()
            if heldout_labelled["contrastive_label"].nunique(dropna=True) >= 2:
                labelled_probs = selector_prob(
                    selector,
                    torch.tensor(heldout_labelled[names].to_numpy(), dtype=torch.float32),
                )
                heldout_auc, heldout_sep_auc = safe_auc(
                    heldout_labelled["contrastive_label"].to_numpy(dtype=np.float32),
                    labelled_probs.detach().cpu().numpy(),
                )
            else:
                heldout_auc, heldout_sep_auc = float("nan"), float("nan")
            for row in summarize_policy(
                seed=seed,
                feature_set=feature_set_name,
                policy_name="multi_window_contrastive",
                threshold=threshold,
                train_metrics={
                    **train_metrics,
                    "heldout_auc": heldout_auc,
                    "heldout_separability_auc": heldout_sep_auc,
                    "train_positive": float((labelled["contrastive_class"] == "positive").sum()),
                    "train_negative": float((labelled["contrastive_class"] == "negative").sum()),
                    "train_neutral": float((train["contrastive_class"] == "neutral").sum()),
                },
                heldout=heldout,
                probs=heldout_probs,
            ):
                rows.append(row)
    return rows


def aggregate(result: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (feature_set, heldout), group in result.groupby(["feature_set", "heldout"], sort=False):
        row = {"feature_set": feature_set, "heldout": heldout}
        for column in [
            "heldout_auc",
            "heldout_separability_auc",
            "selected_fraction",
            "selector_delta_solved_vs_base",
            "selector_delta_solved_vs_fixed_rho",
            "lost_solution",
            "recovered_timeout",
            "selector_delta_vs_base",
            "selector_delta_vs_fixed_rho",
        ]:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_ci_low"] = float(group[column].quantile(0.025))
            row[f"{column}_ci_high"] = float(group[column].quantile(0.975))
        row["beats_fixed_rho_time_rate"] = float((group["selector_delta_vs_fixed_rho"] < 0.0).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def label_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for size, group in frame.groupby("size", sort=True):
        counts = group["contrastive_class"].value_counts()
        rows.append(
            {
                "size": int(size),
                "positive": int(counts.get("positive", 0)),
                "negative": int(counts.get("negative", 0)),
                "neutral": int(counts.get("neutral", 0)),
                "n": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def write_doc(labels: pd.DataFrame, auc_table: pd.DataFrame, summary: pd.DataFrame) -> None:
    summary_columns = [
        "feature_set",
        "heldout",
        "heldout_separability_auc_mean",
        "selected_fraction_mean",
        "selector_delta_solved_vs_base_mean",
        "selector_delta_solved_vs_fixed_rho_mean",
        "lost_solution_mean",
        "recovered_timeout_mean",
        "selector_delta_vs_fixed_rho_mean",
        "beats_fixed_rho_time_rate",
    ]
    auc_columns = ["feature", "auc", "separability_auc", "positive_mean", "negative_mean"]
    doc = [
        "# Multi-Window Outcome Diagnostic",
        "",
        "This diagnostic tests whether multi-short-rollout evidence improves",
        "outcome predictiveness. It extracts warmup features at conflict budgets",
        "`100`, `500`, and `1000`, then adds drift features between adjacent",
        "windows. No final 60s solver evaluation is run here.",
        "",
        "## Label Counts",
        "",
        markdown_table(labels, ["size", "positive", "negative", "neutral", "n"]),
        "",
        "## Best Univariate Separability",
        "",
        markdown_table(auc_table.head(15), auc_columns),
        "",
        "## Repeated-Split Selector",
        "",
        markdown_table(summary[summary_columns], summary_columns),
        "",
        "## Current Conclusion",
        "",
        "- `d100_500_rho_event_corr` is the strongest univariate temporal",
        "  signal in this diagnostic, with separability AUC around `0.73`.",
        "- The conservative `best_drift_corr` and `base_plus_best_drift_corr`",
        "  selectors improve held-out label separability, but they do not beat",
        "  the simple `base_rho` risk controller on solved-count safety.",
        "- The next bottleneck is therefore the rollout/label evidence, not",
        "  another round of selector feature engineering.",
        "",
        "## Reading",
        "",
        "- If `multi_abs`, `multi_drift`, or `multi_full` do not improve AUC and",
        "  held-out solved/time metrics over `single_500`, then the current warmup",
        "  evidence is not predictive enough for a selector.",
        "- The important metric is not selected fraction alone; useful evidence must",
        "  preserve recovered timeouts while reducing lost solved instances.",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    frame = build_multi_window_frame()
    feature_name_sets = feature_sets()
    all_auc_features = sorted(
        {
            feature
            for features in feature_name_sets.values()
            for feature in features
        }
    )
    auc_table = univariate_auc(frame, all_auc_features)
    rows = repeated_split_rows(frame, feature_name_sets)
    result = pd.DataFrame(rows)
    summary = aggregate(result)
    labels = label_summary(frame)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT_DIR / "multi_window_outcome_frame_300350.csv", index=False)
    auc_table.to_csv(OUT_DIR / "multi_window_univariate_auc.csv", index=False)
    result.to_csv(OUT_DIR / "multi_window_selector_repeated_splits.csv", index=False)
    summary.to_csv(OUT_DIR / "multi_window_selector_summary.csv", index=False)
    write_doc(labels, auc_table, summary)
    print(f"wrote {OUT_DIR / 'multi_window_outcome_frame_300350.csv'}")
    print(f"wrote {OUT_DIR / 'multi_window_univariate_auc.csv'}")
    print(f"wrote {OUT_DIR / 'multi_window_selector_repeated_splits.csv'}")
    print(f"wrote {OUT_DIR / 'multi_window_selector_summary.csv'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
