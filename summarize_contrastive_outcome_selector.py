from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from summarize_risk_controller_selector import (
    ALL_FEATURES,
    MICRO_FEATURES,
    SEEDS,
    SIZES,
    apply_probs,
    fit_weighted_linear_selector,
    load_frame,
    markdown_table,
    selector_prob,
    summarize_policy,
)


OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/contrastive_outcome_selector_results.md")
POSITIVE_SPEEDUP_RATIO = 0.80
NEGATIVE_SLOWDOWN_RATIO = 1.10


@dataclass(frozen=True)
class ContrastiveSpec:
    positive_speedup_ratio: float = POSITIVE_SPEEDUP_RATIO
    negative_slowdown_ratio: float = NEGATIVE_SLOWDOWN_RATIO
    positive_weight: float = 4.0
    negative_weight: float = 8.0


def attach_contrastive_labels(frame: pd.DataFrame, spec: ContrastiveSpec) -> pd.DataFrame:
    frame = frame.copy()
    base_solved = frame["base_solved"].astype(bool)
    adapter_solved = frame["adapter_solved"].astype(bool)
    both_solved = base_solved & adapter_solved
    recovered = ~base_solved & adapter_solved
    lost = base_solved & ~adapter_solved
    speedup = both_solved & (frame["adapter_time"] <= spec.positive_speedup_ratio * frame["base_time"])
    slowdown = both_solved & (frame["adapter_time"] >= spec.negative_slowdown_ratio * frame["base_time"])

    frame["contrastive_class"] = "neutral"
    frame.loc[recovered | speedup, "contrastive_class"] = "positive"
    frame.loc[lost | slowdown, "contrastive_class"] = "negative"
    frame["contrastive_label"] = np.nan
    frame.loc[frame["contrastive_class"] == "positive", "contrastive_label"] = 1.0
    frame.loc[frame["contrastive_class"] == "negative", "contrastive_label"] = 0.0
    frame["contrastive_weight"] = 0.0
    frame.loc[frame["contrastive_class"] == "positive", "contrastive_weight"] = spec.positive_weight
    frame.loc[frame["contrastive_class"] == "negative", "contrastive_weight"] = spec.negative_weight
    return frame


def choose_contrastive_threshold(frame: pd.DataFrame, probs: torch.Tensor) -> tuple[float, dict[str, float]]:
    candidates = sorted(set(float(value) for value in probs.detach().cpu().tolist()) | {0.0, 0.5, 1.0, 1.000001})
    best_threshold = 1.000001
    best_tuple = None
    best_metrics: dict[str, float] = {}
    for threshold in candidates:
        selected = apply_probs(frame, probs, threshold)
        solved = int(selected["selector_solved"].sum())
        lost = int(selected["selector_lost_solution"].sum())
        recovered = int(selected["selector_recovered_timeout"].sum())
        mean_time = float(selected["selector_time"].mean())
        selected_fraction = float(selected["selector_use_adapter"].mean())
        score = (solved, recovered, -lost, -mean_time)
        if best_tuple is None or score > best_tuple:
            best_tuple = score
            best_threshold = threshold
            best_metrics = {
                "train_selected_solved": float(solved),
                "train_lost_solution": float(lost),
                "train_recovered_timeout": float(recovered),
                "train_mean_time": mean_time,
                "train_selected_fraction": selected_fraction,
            }
    return best_threshold, best_metrics


def split_rows(
    frame: pd.DataFrame,
    feature_names: list[str],
    seeds: list[int],
    spec: ContrastiveSpec,
) -> list[dict[str, object]]:
    rows = []
    feature_set = "+".join(feature_names)
    for seed in seeds:
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

        train_features = torch.tensor(labelled[feature_names].to_numpy(), dtype=torch.float32)
        heldout_features = torch.tensor(heldout[feature_names].to_numpy(), dtype=torch.float32)
        selector, _ = fit_weighted_linear_selector(
            train_features,
            torch.tensor(labelled["contrastive_label"].to_numpy(), dtype=torch.float32),
            torch.tensor(labelled["contrastive_weight"].to_numpy(), dtype=torch.float32),
            feature_names=feature_names,
            epochs=1000,
            lr=0.05,
            l2=1.0e-3,
        )
        train_all_features = torch.tensor(train[feature_names].to_numpy(), dtype=torch.float32)
        train_probs = selector_prob(selector, train_all_features)
        threshold, train_metrics = choose_contrastive_threshold(train, train_probs)
        heldout_probs = selector_prob(selector, heldout_features)
        policy_rows = summarize_policy(
            seed=seed,
            feature_set=feature_set,
            policy_name="contrastive_selector",
            threshold=threshold,
            train_metrics={
                **train_metrics,
                "train_positive": float((labelled["contrastive_class"] == "positive").sum()),
                "train_negative": float((labelled["contrastive_class"] == "negative").sum()),
                "train_neutral": float((train["contrastive_class"] == "neutral").sum()),
            },
            heldout=heldout,
            probs=heldout_probs,
        )
        rows.extend(policy_rows)
    return rows


def aggregate(result: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["feature_set", "policy", "heldout"]
    for keys, group in result.groupby(group_cols, sort=False):
        row = dict(zip(group_cols, keys))
        for column in [
            "selected_fraction",
            "selector_delta_solved_vs_base",
            "selector_delta_solved_vs_fixed_rho",
            "lost_solution",
            "recovered_timeout",
            "selector_delta_vs_base",
            "selector_delta_vs_fixed_rho",
            "train_positive",
            "train_negative",
            "train_neutral",
        ]:
            if column not in group:
                continue
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_ci_low"] = float(group[column].quantile(0.025))
            row[f"{column}_ci_high"] = float(group[column].quantile(0.975))
        row["beats_base_solved_rate"] = float((group["selector_delta_solved_vs_base"] > 0).mean())
        row["beats_fixed_rho_solved_rate"] = float(
            (group["selector_delta_solved_vs_fixed_rho"] > 0).mean()
        )
        row["beats_base_time_rate"] = float((group["selector_delta_vs_base"] < 0.0).mean())
        row["beats_fixed_rho_time_rate"] = float(
            (group["selector_delta_vs_fixed_rho"] < 0.0).mean()
        )
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


def write_doc(labels: pd.DataFrame, summary: pd.DataFrame) -> None:
    columns = [
        "feature_set",
        "heldout",
        "selected_fraction_mean",
        "selector_delta_solved_vs_base_mean",
        "selector_delta_solved_vs_fixed_rho_mean",
        "lost_solution_mean",
        "recovered_timeout_mean",
        "selector_delta_vs_base_mean",
        "selector_delta_vs_fixed_rho_mean",
        "beats_fixed_rho_time_rate",
    ]
    doc = [
        "# Contrastive Outcome Selector Results",
        "",
        "This is the first outcome-driven selector experiment. It uses existing",
        "clean CSVs only: one-shot is the base branch, fixed-rho is the adapter",
        "branch, and the selector is trained on counterfactual outcome labels.",
        "",
        "Label rules:",
        "",
        f"- positive: adapter solves a base timeout, or adapter time <= {POSITIVE_SPEEDUP_RATIO:.2f} * base time",
        f"- negative: adapter loses a base-solved instance, or adapter time >= {NEGATIVE_SLOWDOWN_RATIO:.2f} * base time",
        "- neutral: ignored by the classifier loss, still used for threshold selection",
        "",
        "## Label Counts",
        "",
        markdown_table(labels, ["size", "positive", "negative", "neutral", "n"]),
        "",
        "## Repeated-Split Summary",
        "",
        markdown_table(summary[columns], columns),
        "",
        "## Reading",
        "",
        "- This checks whether outcome labels help more than hand-written risk",
        "  labels. The key comparison is against `base_rho_mean` risk controller",
        "  from `docs/risk_controller_selector_results.md`.",
        "- If contrastive labels do not improve held-out solved/time tradeoffs,",
        "  the bottleneck is likely rollout evidence predictiveness, not just the",
        "  objective.",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    spec = ContrastiveSpec()
    frame = attach_contrastive_labels(load_frame(), spec)
    labels = label_summary(frame)
    rows = []
    feature_sets = [
        ["base_rho_mean"],
        ["base_rho_mean", "num_vars_log"],
        ["base_rho_mean", *MICRO_FEATURES],
        ["base_rho_mean", "num_vars_log", *MICRO_FEATURES],
    ]
    for feature_names in feature_sets:
        rows.extend(split_rows(frame, feature_names, SEEDS, spec))
    result = pd.DataFrame(rows)
    summary = aggregate(result)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUT_DIR / "contrastive_outcome_labels_300350.csv", index=False)
    result.to_csv(OUT_DIR / "contrastive_outcome_selector_repeated_splits.csv", index=False)
    summary.to_csv(OUT_DIR / "contrastive_outcome_selector_summary.csv", index=False)
    write_doc(labels, summary)
    print(f"wrote {OUT_DIR / 'contrastive_outcome_labels_300350.csv'}")
    print(f"wrote {OUT_DIR / 'contrastive_outcome_selector_repeated_splits.csv'}")
    print(f"wrote {OUT_DIR / 'contrastive_outcome_selector_summary.csv'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
