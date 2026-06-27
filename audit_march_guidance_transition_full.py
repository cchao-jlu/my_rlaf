from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
STRONG_CSV = ROOT / "runs/analysis/benchmark_transition_band/combined.csv"
GUIDED_CSV = ROOT / "runs/analysis/benchmark_march_guidance_transition_full/combined.csv"
OUT_DIR = ROOT / "runs/analysis/benchmark_march_guidance_transition_full"
PAIR_CSV = OUT_DIR / "strong_solver_overlap.csv"
SUMMARY_CSV = OUT_DIR / "strong_solver_overlap_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_guidance_transition_full_overlap.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def load_pair_frame() -> pd.DataFrame:
    strong = pd.read_csv(STRONG_CSV)
    guided = pd.read_csv(GUIDED_CSV)
    strong["file_key"] = strong["file"].astype(str).map(lambda value: Path(value).name)
    guided["file_key"] = guided["file"].astype(str).map(lambda value: Path(value).name)
    strong["solved"] = strong["Result"].astype(str).isin(SOLVED)
    guided["solved"] = guided["Result"].astype(str).isin(SOLVED)
    strong_pivot = strong.pivot_table(index=["family", "size", "file_key"], columns="solver_name", values=["solved", "time"], aggfunc="first")
    strong_pivot.columns = [f"{metric}_{solver}" for metric, solver in strong_pivot.columns]
    strong_pivot = strong_pivot.reset_index()
    guided_one = guided[guided["seed"].astype(int).eq(1)].copy()
    guided_one = guided_one[["family", "size", "file_key", "solved", "time", "Result"]].rename(
        columns={
            "solved": "solved_march_guided",
            "time": "time_march_guided",
            "Result": "result_march_guided",
        }
    )
    pair = strong_pivot.merge(guided_one, on=["family", "size", "file_key"], how="inner")
    pair["strong_union_solved"] = pair["solved_march"].astype(bool) | pair["solved_cadical"].astype(bool)
    pair["strong_both_unknown"] = ~pair["solved_march"].astype(bool) & ~pair["solved_cadical"].astype(bool)
    pair["guided_only_vs_union"] = pair["solved_march_guided"].astype(bool) & ~pair["strong_union_solved"]
    pair["union_only_vs_guided"] = pair["strong_union_solved"] & ~pair["solved_march_guided"].astype(bool)
    pair["guided_only_vs_march"] = pair["solved_march_guided"].astype(bool) & ~pair["solved_march"].astype(bool)
    pair["march_only_vs_guided"] = pair["solved_march"].astype(bool) & ~pair["solved_march_guided"].astype(bool)
    pair["guided_minus_march_time"] = pair["time_march_guided"] - pair["time_march"]
    pair["guided_minus_cadical_time"] = pair["time_march_guided"] - pair["time_cadical"]
    return pair


def summarize(pair: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for size, group in pair.groupby("size", sort=True):
        rows.append(
            {
                "size": int(size),
                "n": int(len(group)),
                "march_solved": int(group["solved_march"].sum()),
                "cadical_solved": int(group["solved_cadical"].sum()),
                "strong_union_solved": int(group["strong_union_solved"].sum()),
                "march_guided_solved": int(group["solved_march_guided"].sum()),
                "guided_only_vs_union": int(group["guided_only_vs_union"].sum()),
                "union_only_vs_guided": int(group["union_only_vs_guided"].sum()),
                "guided_only_vs_march": int(group["guided_only_vs_march"].sum()),
                "march_only_vs_guided": int(group["march_only_vs_guided"].sum()),
                "mean_guided_minus_march_time": float(group["guided_minus_march_time"].mean()),
                "median_guided_minus_march_time": float(group["guided_minus_march_time"].median()),
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


def write_doc(pair: pd.DataFrame, summary: pd.DataFrame) -> None:
    guided_only_union = pair[pair["guided_only_vs_union"]]
    guided_only_march = pair[pair["guided_only_vs_march"]]
    march_only_guided = pair[pair["march_only_vs_guided"]]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# March-Guided Full Transition-Band Overlap",
        "",
        "Scope: diagnostic comparison of frozen March-guided one-shot against",
        "unguided March and CaDiCaL on the 36-instance transition-band set.",
        "This is model-result evidence, not paper polishing.",
        "",
        "## Summary",
        "",
        *markdown_table(
            summary,
            [
                "size",
                "n",
                "march_solved",
                "cadical_solved",
                "strong_union_solved",
                "march_guided_solved",
                "guided_only_vs_union",
                "union_only_vs_guided",
                "guided_only_vs_march",
                "march_only_vs_guided",
                "mean_guided_minus_march_time",
            ],
        ),
        "",
        "## Guided-Only vs Strong Union",
        "",
        *markdown_table(guided_only_union, ["size", "file_key", "result_march_guided", "time_march_guided", "time_march", "time_cadical"]),
        "",
        "## Guided-Only vs Unguided March",
        "",
        *markdown_table(guided_only_march, ["size", "file_key", "result_march_guided", "time_march_guided", "time_march", "time_cadical"]),
        "",
        "## Unguided March-Only vs Guided",
        "",
        *markdown_table(march_only_guided, ["size", "file_key", "time_march", "time_march_guided", "time_cadical"]),
        "",
        "## Decision",
        "",
    ]
    if int(summary["guided_only_vs_union"].sum()) > 0:
        lines.extend(
            [
                "- March-guided one-shot has nonzero complementarity against the",
                "  March/CaDiCaL union on this transition-band set.",
                "- This is the first promising model-side signal and should be repeated",
                "  across seeds and a larger generated set before changing the main claim.",
            ]
        )
    else:
        lines.extend(
            [
                "- March-guided one-shot has no complementarity against the March/CaDiCaL",
                "  union on this transition-band set.",
                "- If it helps relative to unguided March, that help is still covered by",
                "  CaDiCaL and does not create a top-conference performance path yet.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(PAIR_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    pair = load_pair_frame()
    pair.to_csv(PAIR_CSV, index=False)
    summary = summarize(pair)
    summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(pair, summary)
    print(summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
