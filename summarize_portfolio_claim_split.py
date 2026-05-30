from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/portfolio_e2e_local5_cadical55"
DOC_PATH = ROOT / "docs/portfolio_claim_split.md"


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                if pd.isna(value):
                    values.append("")
                elif col.endswith("_time") or col.endswith("_mean") or col.endswith("_std"):
                    values.append(f"{value:.3f}")
                elif float(value).is_integer():
                    values.append(str(int(value)))
                else:
                    values.append(f"{value:.3f}")
            elif pd.isna(value):
                values.append("")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def classify(row: pd.Series, repeats: int) -> str:
    if row["portfolio_only_vs_cadical_repeats"] <= 0:
        return "not_portfolio_only"
    if row["local_first_stage_solved_repeats"] == repeats:
        return "stable_neural_first_complement"
    if row["local_first_stage_solved_repeats"] > 0:
        return "unstable_neural_first_complement"
    if row["cadical_second_stage_solved_repeats"] == repeats:
        return "stable_second_stage_runtime_boundary"
    return "unstable_second_stage_runtime_boundary"


def main() -> None:
    overlap = pd.read_csv(OUT_DIR / "repeat_instance_overlap.csv", dtype={"pattern": str})
    repeat_summary = pd.read_csv(OUT_DIR / "repeat_stability_summary.csv")
    repeats = int(len(repeat_summary))

    claim_frame = overlap.loc[overlap["portfolio_only_vs_cadical_repeats"].gt(0)].copy()
    claim_frame["claim_class"] = claim_frame.apply(classify, axis=1, repeats=repeats)
    claim_frame["paper_interpretation"] = claim_frame["claim_class"].map(
        {
            "stable_neural_first_complement": "Strong neural-first portfolio complement: Local solves within 5s in all repeats while CaDiCaL 60s times out.",
            "unstable_neural_first_complement": "Neural-first complement, but not stable across all repeats.",
            "stable_second_stage_runtime_boundary": "Sequential-schedule runtime-boundary evidence: second-stage CaDiCaL 55s solves in all repeats while independent CaDiCaL 60s baseline times out.",
            "unstable_second_stage_runtime_boundary": "Cutoff/runtime boundary evidence, not a neural solve.",
        }
    )
    claim_frame = claim_frame.sort_values(["claim_class", "file_key"])
    claim_frame.to_csv(OUT_DIR / "portfolio_claim_split.csv", index=False)

    summary = (
        claim_frame.groupby("claim_class", dropna=False)
        .agg(
            instances=("file_key", "count"),
            total_portfolio_only_repeats=("portfolio_only_vs_cadical_repeats", "sum"),
            local_first_stage_solved_repeats=("local_first_stage_solved_repeats", "sum"),
            cadical_second_stage_solved_repeats=("cadical_second_stage_solved_repeats", "sum"),
        )
        .reset_index()
        .sort_values("claim_class")
    )
    summary.to_csv(OUT_DIR / "portfolio_claim_split_summary.csv", index=False)

    stable_neural = claim_frame.loc[claim_frame["claim_class"].eq("stable_neural_first_complement")]
    stable_boundary = claim_frame.loc[claim_frame["claim_class"].eq("stable_second_stage_runtime_boundary")]
    unstable_boundary = claim_frame.loc[claim_frame["claim_class"].eq("unstable_second_stage_runtime_boundary")]

    lines = [
        "# Portfolio Claim Split",
        "",
        "Scope: classify the end-to-end Local-5s / CaDiCaL-55s portfolio-only",
        "instances into neural-first complementarity and second-stage runtime",
        "boundary evidence. This document is meant to prevent over-claiming",
        "portfolio-only solves as neural solves.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv",
        "```",
        "",
        "## Summary",
        "",
        *markdown_table(
            summary,
            [
                "claim_class",
                "instances",
                "total_portfolio_only_repeats",
                "local_first_stage_solved_repeats",
                "cadical_second_stage_solved_repeats",
            ],
        ),
        "",
        "## Stable Neural-First Complement",
        "",
        *markdown_table(
            stable_neural,
            [
                "file_key",
                "portfolio_only_vs_cadical_repeats",
                "local_first_stage_solved_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
                "paper_interpretation",
            ],
        ),
        "",
        "## Stable Second-Stage Runtime Boundary",
        "",
        *markdown_table(
            stable_boundary,
            [
                "file_key",
                "portfolio_only_vs_cadical_repeats",
                "cadical_second_stage_solved_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
                "paper_interpretation",
            ],
        ),
        "",
        "## Unstable Second-Stage Runtime Boundary",
        "",
        *markdown_table(
            unstable_boundary,
            [
                "file_key",
                "portfolio_only_vs_cadical_repeats",
                "cadical_second_stage_solved_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
                "paper_interpretation",
            ],
        ),
        "",
        "## Decision",
        "",
        "- The strongest top-conference claim is not that neural guidance alone",
        "  beats CaDiCaL. It is that a neural-first/CDCL-second schedule has",
        "  stable complementarity with CaDiCaL 60s on full400.",
        "- The strict neural-first complement consists of 3 stable instances:",
        "  `3sat_132.cnf`, `3sat_140.cnf`, and `3sat_25.cnf`.",
        "- `3sat_111.cnf` is stable portfolio-only evidence, but it is solved by",
        "  the second-stage CaDiCaL run, so it should be described as a",
        "  sequential-schedule runtime-boundary case.",
        "- `3sat_48.cnf` appears in two of three repeats and is also a",
        "  second-stage CaDiCaL cutoff/runtime boundary case.",
        "- Paper tables may report total portfolio solved count, but explanatory",
        "  text must split neural-first complement from second-stage runtime",
        "  boundary evidence.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split_summary.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
