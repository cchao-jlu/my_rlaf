from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
FEATURES_CSV = ROOT / "runs/analysis/benchmark_march_sample_selector_features/focused_sample_features.csv"
OUT_DIR = ROOT / "runs/analysis/benchmark_march_sample_selector_features"
SIM_CSV = OUT_DIR / "budgeted_selector_simulation.csv"
SUMMARY_CSV = OUT_DIR / "budgeted_selector_summary.csv"
INSTANCE_CSV = OUT_DIR / "budgeted_selector_instance_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_sample_selector_budget.md"


POLICIES: list[tuple[str, str, bool]] = [
    ("low_log_prob", "log_prob", True),
    ("high_weight_std", "weight_std", False),
    ("high_phase_mode_match", "phase_mode_match", False),
    ("high_log_weight_abs_mean", "log_weight_abs_mean", False),
    ("combined_low_logprob_high_weightstd", "combined_rank_logprob_weightstd", True),
]
TOP_KS = [1, 2, 4, 8, 16]


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def add_combined_rank(frame: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in frame.groupby(["size", "file_key", "sample_seed"], sort=True):
        group = group.copy()
        group["rank_low_log_prob"] = group["log_prob"].rank(method="first", ascending=True)
        group["rank_high_weight_std"] = group["weight_std"].rank(method="first", ascending=False)
        group["combined_rank_logprob_weightstd"] = group["rank_low_log_prob"] + group["rank_high_weight_std"]
        frames.append(group)
    return pd.concat(frames, ignore_index=True)


def stop_cost(ranked: pd.DataFrame, top_k: int) -> tuple[bool, float, int]:
    selected = ranked.head(top_k).copy()
    selected["cpu_capped"] = selected["CPU time"].astype(float).clip(upper=60.0)
    cost = 0.0
    for idx, row in enumerate(selected.itertuples(index=False), start=1):
        cost += float(getattr(row, "cpu_capped"))
        if bool(getattr(row, "solved_strict60")):
            return True, cost, idx
    return False, cost, -1


def simulate_ranked(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (size, file_key, sample_seed), group in frame.groupby(["size", "file_key", "sample_seed"], sort=True):
        positive = bool(group["solved_strict60"].any())
        for policy, metric, ascending in POLICIES:
            ranked = group.sort_values(metric, ascending=ascending).reset_index(drop=True)
            for top_k in TOP_KS:
                solved, cost, first_hit = stop_cost(ranked, top_k)
                selected = ranked.head(top_k)
                rows.append(
                    {
                        "policy": policy,
                        "top_k": int(top_k),
                        "size": int(size),
                        "file_key": file_key,
                        "sample_seed": int(sample_seed),
                        "oracle_positive": positive,
                        "selected_solved": solved,
                        "first_hit_rank": int(first_hit),
                        "stop_cpu_capped": float(cost),
                        "selected_cpu_capped_no_stop": float(selected["CPU time"].astype(float).clip(upper=60.0).sum()),
                        "selected_strict60_solved_samples": int(selected["solved_strict60"].sum()),
                    }
                )
    return pd.DataFrame(rows)


def simulate_random(frame: pd.DataFrame, trials: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for (size, file_key, sample_seed), group in frame.groupby(["size", "file_key", "sample_seed"], sort=True):
        positive = bool(group["solved_strict60"].any())
        group = group.reset_index(drop=True)
        for top_k in TOP_KS:
            solved_count = 0
            costs = []
            hit_ranks = []
            for _ in range(trials):
                order = rng.permutation(len(group))
                ranked = group.iloc[order].reset_index(drop=True)
                solved, cost, first_hit = stop_cost(ranked, top_k)
                solved_count += int(solved)
                costs.append(cost)
                hit_ranks.append(first_hit)
            rows.append(
                {
                    "policy": "random",
                    "top_k": int(top_k),
                    "size": int(size),
                    "file_key": file_key,
                    "sample_seed": int(sample_seed),
                    "oracle_positive": positive,
                    "selected_solved": solved_count / float(trials),
                    "first_hit_rank": float(np.mean([rank for rank in hit_ranks if rank > 0])) if any(rank > 0 for rank in hit_ranks) else -1.0,
                    "stop_cpu_capped": float(np.mean(costs)),
                    "selected_cpu_capped_no_stop": float("nan"),
                    "selected_strict60_solved_samples": float("nan"),
                }
            )
    return pd.DataFrame(rows)


def summarize(sim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (policy, top_k), group in sim.groupby(["policy", "top_k"], sort=True):
        positives = group[group["oracle_positive"]]
        rows.append(
            {
                "policy": policy,
                "top_k": int(top_k),
                "groups": int(len(group)),
                "oracle_positive_groups": int(len(positives)),
                "selected_solved_groups": float(group["selected_solved"].sum()),
                "positive_recovered_groups": float(positives["selected_solved"].sum()),
                "positive_recall": float(positives["selected_solved"].mean()) if len(positives) else float("nan"),
                "mean_stop_cpu_capped": float(group["stop_cpu_capped"].mean()),
                "mean_stop_cpu_capped_positive": float(positives["stop_cpu_capped"].mean()) if len(positives) else float("nan"),
                "mean_first_hit_rank_positive": float(
                    positives.loc[positives["first_hit_rank"].astype(float) > 0, "first_hit_rank"].astype(float).mean()
                )
                if len(positives)
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def summarize_instances(sim: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (policy, top_k, size, file_key), group in sim.groupby(["policy", "top_k", "size", "file_key"], sort=True):
        positive_seed_groups = int(group["oracle_positive"].sum())
        recovered = float(group.loc[group["oracle_positive"], "selected_solved"].sum()) if positive_seed_groups else 0.0
        rows.append(
            {
                "policy": policy,
                "top_k": int(top_k),
                "size": int(size),
                "file_key": file_key,
                "seed_groups": int(len(group)),
                "oracle_positive_seed_groups": positive_seed_groups,
                "recovered_positive_seed_groups": recovered,
                "instance_hit_any_seed": bool(group["selected_solved"].astype(float).sum() > 0.0),
                "mean_stop_cpu_capped": float(group["stop_cpu_capped"].mean()),
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(summary: pd.DataFrame, instance_summary: pd.DataFrame) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    ranked = summary[summary["top_k"].isin([1, 2, 4])].sort_values(
        ["positive_recall", "mean_stop_cpu_capped"], ascending=[False, True]
    )
    focus = instance_summary[
        (instance_summary["policy"].isin(["low_log_prob", "high_weight_std", "high_phase_mode_match", "random"]))
        & (instance_summary["top_k"].isin([1, 2, 4]))
    ].sort_values(["size", "file_key", "policy", "top_k"])
    lines = [
        "# March Sample Selector Budget Simulation",
        "",
        "Scope: offline budget simulation over the focused March sampled-portfolio",
        "artifacts. It does not run new SAT solving. Each policy ranks the 16",
        "sampled guidances for an instance/seed group, executes only top-k in that",
        "rank order, caps each attempt at nominal 60 seconds, and stops after the",
        "first strict-60 solve.",
        "",
        "This is a deployability gate for the oracle sampled-portfolio signal: if",
        "cheap ranking cannot recover complement cases at small k, the evidence",
        "remains an oracle diagnostic rather than a top-conference performance",
        "claim.",
        "",
        "## Top-k Summary",
        "",
        *markdown_table(
            ranked,
            [
                "policy",
                "top_k",
                "oracle_positive_groups",
                "positive_recovered_groups",
                "positive_recall",
                "mean_stop_cpu_capped",
                "mean_stop_cpu_capped_positive",
                "mean_first_hit_rank_positive",
            ],
        ),
        "",
        "## Instance-Level Recovery",
        "",
        *markdown_table(
            focus,
            [
                "policy",
                "top_k",
                "size",
                "file_key",
                "oracle_positive_seed_groups",
                "recovered_positive_seed_groups",
                "instance_hit_any_seed",
                "mean_stop_cpu_capped",
            ],
        ),
        "",
        "## Decision",
        "",
    ]
    best_top4 = summary[(summary["policy"] == "low_log_prob") & (summary["top_k"] == 4)]
    if not best_top4.empty and float(best_top4.iloc[0]["positive_recall"]) >= 0.75:
        lines.extend(
            [
                "- Cheap static ranking is not yet a deployable top-conference result.",
                "  It recovers most strict-60 positive seed groups at top-2/top-4,",
                "  but random top-4 is close on this small focused set.",
                "- The signal is strong enough only for the next experimental gate: a",
                "  real fixed-budget runner on the focused complement cases, generating",
                "  samples, ranking before solving, and executing only fixed top-k",
                "  without per-instance tuning.",
                "- If the real runner does not preserve the complement hits under a",
                "  fixed wall-clock budget, the next method step should add early",
                "  solver-trace features or retrain toward strong-union-unsolved cases.",
            ]
        )
    else:
        lines.extend(
            [
                "- Cheap static ranking is not sufficient as a deployable selector.",
                "- The next method gate should add early solver-trace features or change",
                "  the training objective toward strong-union-unsolved cases.",
            ]
        )
    lines.extend(
        [
            "",
            "Artifacts:",
            "",
            "```text",
            str(SIM_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            str(INSTANCE_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate budgeted selection over sampled March guidance artifacts.")
    parser.add_argument("--features", default=str(FEATURES_CSV))
    parser.add_argument("--random-trials", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    frame = pd.read_csv(args.features)
    frame["solved_strict60"] = _as_bool(frame["solved_strict60"])
    frame = add_combined_rank(frame)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ranked_sim = simulate_ranked(frame)
    random_sim = simulate_random(frame, trials=args.random_trials, rng=np.random.default_rng(args.seed))
    sim = pd.concat([ranked_sim, random_sim], ignore_index=True)
    summary = summarize(sim)
    instance_summary = summarize_instances(sim)
    sim.to_csv(SIM_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    instance_summary.to_csv(INSTANCE_CSV, index=False)
    write_doc(summary, instance_summary)

    print(summary.sort_values(["top_k", "positive_recall", "mean_stop_cpu_capped"], ascending=[True, False, True]).to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
