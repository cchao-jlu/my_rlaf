from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.training.adapter_selector import choose_threshold_for_time, fit_linear_selector, selected_time


FEATURE_SOURCE = Path(
    "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorRho300350/"
    "selector_training.csv"
)
BASE_PATH = "runs/GNN_Glucose_3SAT_V1/eval_oneshot_{size}_optimized_events_gated.csv"
ADAPTER_PATH = (
    "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
    "eval_trace_adapter_rho_gate_{size}_optimized_events_gated.csv"
)
OUT_DIR = Path("runs/analysis")
OUT_CSV = OUT_DIR / "offline_selector_split_stability_fixed_rho.csv"
DOC_PATH = Path("docs/clean_stability_and_cactus_results.md")
SIZES = [300, 350]


def size_from_dataset(value: str) -> int:
    match = re.search(r"/(\d+)/", value)
    if match is None:
        raise ValueError(f"Cannot infer size from selector_dataset={value!r}")
    return int(match.group(1))


def load_current_selector_frame() -> pd.DataFrame:
    features = pd.read_csv(FEATURE_SOURCE)
    features = features[["selector_dataset", "cnf_id", "base_rho_mean"]].copy()
    features["size"] = features["selector_dataset"].astype(str).map(size_from_dataset)

    frames = []
    for size in SIZES:
        base = pd.read_csv(BASE_PATH.format(size=size))[["cnf_id", "time"]].rename(
            columns={"time": "base_time"}
        )
        adapter = pd.read_csv(ADAPTER_PATH.format(size=size))[["cnf_id", "time"]].rename(
            columns={"time": "adapter_time"}
        )
        current = (
            features[features["size"] == size]
            .merge(base, on="cnf_id", how="inner")
            .merge(adapter, on="cnf_id", how="inner")
        )
        current["gain"] = current["base_time"] - current["adapter_time"]
        current["label"] = (current["gain"] > 0.0).astype("float32")
        frames.append(current)
    return pd.concat(frames, ignore_index=True)


def selector_prob(selector, values: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(selector.feature_mean, dtype=torch.float32)
    std = torch.tensor(selector.feature_std, dtype=torch.float32).clamp_min(1.0e-6)
    weights = torch.tensor(selector.weights, dtype=torch.float32)
    bias = torch.tensor(selector.bias, dtype=torch.float32)
    x = (values - mean) / std
    return torch.sigmoid(x.matmul(weights) + bias)


def split_rows(frame: pd.DataFrame, seeds: list[int], train_per_size: int = 100) -> list[dict[str, object]]:
    rows = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        train_indices = []
        heldout_indices = []
        for size in SIZES:
            size_indices = frame.index[frame["size"] == size].to_numpy()
            chosen = rng.choice(size_indices, size=train_per_size, replace=False)
            train_indices.extend(chosen.tolist())
            heldout_indices.extend(sorted(set(size_indices.tolist()).difference(chosen.tolist())))

        train = frame.loc[train_indices].copy()
        heldout = frame.loc[heldout_indices].copy()
        feature_names = ["base_rho_mean"]
        train_features = torch.tensor(train[feature_names].to_numpy(), dtype=torch.float32)
        labels = torch.tensor(train["label"].to_numpy(), dtype=torch.float32)
        selector, train_probs = fit_linear_selector(
            train_features,
            labels,
            feature_names=feature_names,
            epochs=1000,
            lr=0.05,
            l2=1.0e-3,
        )
        train_base = torch.tensor(train["base_time"].to_numpy(), dtype=torch.float32)
        train_adapter = torch.tensor(train["adapter_time"].to_numpy(), dtype=torch.float32)
        threshold, train_selector_time = choose_threshold_for_time(
            train_base,
            train_adapter,
            train_probs,
        )
        selector.threshold = float(threshold)

        heldout_features = torch.tensor(heldout[feature_names].to_numpy(), dtype=torch.float32)
        probs = selector_prob(selector, heldout_features)
        heldout = heldout.copy()
        heldout["selector_prob"] = probs.detach().cpu().numpy()
        heldout["selector_use_adapter"] = (
            heldout["selector_prob"].to_numpy() >= selector.threshold
        ).astype("int64")
        heldout["selector_time"] = selected_time(
            torch.tensor(heldout["base_time"].to_numpy(), dtype=torch.float32),
            torch.tensor(heldout["adapter_time"].to_numpy(), dtype=torch.float32),
            probs,
            selector.threshold,
        ).cpu().numpy()

        for size_name, subset in [("300+350", heldout)] + [
            (str(size), heldout[heldout["size"] == size]) for size in SIZES
        ]:
            base_mean = float(subset["base_time"].mean())
            adapter_mean = float(subset["adapter_time"].mean())
            selector_mean = float(subset["selector_time"].mean())
            rows.append(
                {
                    "seed": seed,
                    "heldout": size_name,
                    "n": int(len(subset)),
                    "selected_fraction": float(subset["selector_use_adapter"].mean()),
                    "train_selector_time": float(train_selector_time),
                    "threshold": float(selector.threshold),
                    "base_mean": base_mean,
                    "fixed_rho_mean": adapter_mean,
                    "selector_mean": selector_mean,
                    "fixed_rho_delta_vs_base": adapter_mean - base_mean,
                    "selector_delta_vs_base": selector_mean - base_mean,
                    "selector_delta_vs_fixed_rho": selector_mean - adapter_mean,
                    "selector_better_than_base": int(selector_mean < base_mean),
                    "selector_better_than_fixed_rho": int(selector_mean < adapter_mean),
                }
            )
    return rows


def append_doc(summary: pd.DataFrame) -> None:
    lines = [
        "",
        "## Offline Repeated Selector Split",
        "",
        "This additional check retrains a one-feature linear selector on 50 random",
        "100-per-size training splits from 3SAT-300/350, then evaluates on the",
        "held-out halves. It uses the existing `base_rho_mean` selector feature but",
        "replaces labels/times with the current clean one-shot and fixed-rho CSVs.",
        "",
        "| heldout | selector delta vs base | selector delta vs fixed-rho | better than base | better than fixed-rho | selected fraction |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            "| {heldout} | {delta_base:.4f} [{delta_base_lo:.4f}, {delta_base_hi:.4f}] | "
            "{delta_adapter:.4f} [{delta_adapter_lo:.4f}, {delta_adapter_hi:.4f}] | "
            "{better_base:.3f} | {better_adapter:.3f} | {selected:.3f} |".format(
                heldout=row["heldout"],
                delta_base=row["selector_delta_vs_base_mean"],
                delta_base_lo=row["selector_delta_vs_base_ci_low"],
                delta_base_hi=row["selector_delta_vs_base_ci_high"],
                delta_adapter=row["selector_delta_vs_fixed_rho_mean"],
                delta_adapter_lo=row["selector_delta_vs_fixed_rho_ci_low"],
                delta_adapter_hi=row["selector_delta_vs_fixed_rho_ci_high"],
                better_base=row["selector_better_than_base_mean"],
                better_adapter=row["selector_better_than_fixed_rho_mean"],
                selected=row["selected_fraction_mean"],
            )
        )
    lines.extend(
        [
            "",
            "The selector does not reliably beat fixed-rho on held-out splits, so it",
            "should remain an ablation/open direction rather than the main method.",
        ]
    )
    with DOC_PATH.open("a") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    frame = load_current_selector_frame()
    seeds = list(range(1729, 1779))
    rows = split_rows(frame, seeds=seeds)
    result = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)

    summary_rows = []
    for heldout, group in result.groupby("heldout", sort=False):
        summary_rows.append(
            {
                "heldout": heldout,
                "selector_delta_vs_base_mean": float(group["selector_delta_vs_base"].mean()),
                "selector_delta_vs_base_ci_low": float(group["selector_delta_vs_base"].quantile(0.025)),
                "selector_delta_vs_base_ci_high": float(group["selector_delta_vs_base"].quantile(0.975)),
                "selector_delta_vs_fixed_rho_mean": float(group["selector_delta_vs_fixed_rho"].mean()),
                "selector_delta_vs_fixed_rho_ci_low": float(
                    group["selector_delta_vs_fixed_rho"].quantile(0.025)
                ),
                "selector_delta_vs_fixed_rho_ci_high": float(
                    group["selector_delta_vs_fixed_rho"].quantile(0.975)
                ),
                "selector_better_than_base_mean": float(group["selector_better_than_base"].mean()),
                "selector_better_than_fixed_rho_mean": float(
                    group["selector_better_than_fixed_rho"].mean()
                ),
                "selected_fraction_mean": float(group["selected_fraction"].mean()),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "offline_selector_split_stability_fixed_rho_summary.csv", index=False)
    append_doc(summary)
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_DIR / 'offline_selector_split_stability_fixed_rho_summary.csv'}")
    print(f"updated {DOC_PATH}")


if __name__ == "__main__":
    main()
