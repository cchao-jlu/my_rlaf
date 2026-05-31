from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "runs/analysis/benchmark_3sat450_gate/raw"
OUT_DIR = ROOT / "runs/analysis/benchmark_3sat450_gate"
DOC_PATH = ROOT / "docs/benchmark_3sat450_gate.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def load_raw() -> pd.DataFrame:
    frames = []
    for path in sorted(RAW_DIR.glob("*_repeat*.csv")):
        frame = pd.read_csv(path)
        frame["source_csv"] = str(path.relative_to(ROOT))
        frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
        frame["solved"] = frame["Result"].astype(str).isin(SOLVED)
        frame["time"] = pd.to_numeric(frame["time"], errors="coerce")
        frame["wall_time"] = pd.to_numeric(frame["wall_time"], errors="coerce")
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No raw gate CSVs found in {RAW_DIR}")
    return pd.concat(frames, ignore_index=True)


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_raw()
    frame.to_csv(OUT_DIR / "combined.csv", index=False)
    repeat_count = int(frame["repeat"].nunique())

    summary_rows = []
    for (solver_name, repeat), group in frame.groupby(["solver_name", "repeat"], sort=True):
        summary_rows.append(
            {
                "solver": solver_name,
                "repeat": int(repeat),
                "total": int(len(group)),
                "solved": int(group["solved"].sum()),
                "unknown": int((~group["solved"]).sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
                "max_time": float(group["time"].max()),
                "external_timeouts": int(
                    group["external_timeout"].astype(str).str.lower().isin({"true", "1", "yes"}).sum()
                ),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(["solver", "repeat"])
    summary.to_csv(OUT_DIR / "summary.csv", index=False)

    repeat_overlap_rows = []
    for repeat, group in frame.groupby("repeat", sort=True):
        pivot = group.pivot_table(index="file_key", columns="solver_name", values="solved", aggfunc="first")
        if not {"march", "cadical"}.issubset(pivot.columns):
            raise ValueError(f"Expected both march and cadical raw results for repeat {repeat}")
        march = pivot["march"].astype(bool)
        cadical = pivot["cadical"].astype(bool)
        repeat_overlap_rows.append(
            {
                "repeat": int(repeat),
                "total": int(len(pivot)),
                "both_solved": int((march & cadical).sum()),
                "march_only": int((march & ~cadical).sum()),
                "cadical_only": int((~march & cadical).sum()),
                "both_unknown": int((~march & ~cadical).sum()),
                "union_solved": int((march | cadical).sum()),
            }
        )
    repeat_overlap = pd.DataFrame(repeat_overlap_rows).sort_values("repeat")
    repeat_overlap.to_csv(OUT_DIR / "solver_overlap_by_repeat.csv", index=False)

    stable_rows = []
    for (solver_name, file_key), group in frame.groupby(["solver_name", "file_key"], sort=True):
        solved_repeats = int(group["solved"].sum())
        stable_rows.append(
            {
                "solver": solver_name,
                "file_key": file_key,
                "repeats": int(len(group)),
                "solved_repeats": solved_repeats,
                "solved_any": solved_repeats > 0,
                "solved_all": solved_repeats == len(group),
                "unsolved_all": solved_repeats == 0,
            }
        )
    stable = pd.DataFrame(stable_rows)
    stable.to_csv(OUT_DIR / "solver_instance_repeats.csv", index=False)

    stable_pivot = stable.pivot_table(index="file_key", columns="solver", values="solved_any", aggfunc="first")
    if not {"march", "cadical"}.issubset(stable_pivot.columns):
        raise ValueError("Expected both march and cadical stable repeat rows")
    march_any = stable_pivot["march"].astype(bool)
    cadical_any = stable_pivot["cadical"].astype(bool)
    stable_overlap = pd.DataFrame(
        [
            {
                "repeats": repeat_count,
                "total": int(len(stable_pivot)),
                "both_solved_any": int((march_any & cadical_any).sum()),
                "march_only_any": int((march_any & ~cadical_any).sum()),
                "cadical_only_any": int((~march_any & cadical_any).sum()),
                "both_unsolved_all": int((~march_any & ~cadical_any).sum()),
                "union_solved_any": int((march_any | cadical_any).sum()),
            }
        ]
    )
    stable_overlap.to_csv(OUT_DIR / "solver_overlap_stable.csv", index=False)

    stable_hard = stable_pivot.loc[~march_any & ~cadical_any].reset_index()
    stable_hard.to_csv(OUT_DIR / "strong_solver_hard_subset.csv", index=False)

    lines = [
        "# 3SAT-450 Strong-Solver Gate",
        "",
        "Scope: moderate 3SAT-450 benchmark gate using existing March and CaDiCaL",
        "artifacts under the same nominal 60s protocol. This does not train",
        "neural models, tune selectors, or change solver code.",
        "",
        "Inputs:",
        "",
        "```text",
        "data/benchmark_3sat450_gate/3sat/450/*.cnf",
        "runs/analysis/benchmark_3sat450_gate/raw/march_repeat0.csv",
        "runs/analysis/benchmark_3sat450_gate/raw/march_repeat1.csv",
        "runs/analysis/benchmark_3sat450_gate/raw/march_repeat2.csv",
        "runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat0.csv",
        "runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat1.csv",
        "runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat2.csv",
        "```",
        "",
        "## Solver Summary",
        "",
        *markdown_table(
            summary,
            ["solver", "repeat", "total", "solved", "unknown", "mean_time", "median_time", "max_time", "external_timeouts"],
        ),
        "",
        "## March / CaDiCaL Overlap By Repeat",
        "",
        *markdown_table(
            repeat_overlap,
            ["repeat", "total", "both_solved", "march_only", "cadical_only", "both_unknown", "union_solved"],
        ),
        "",
        "## Stable March / CaDiCaL Overlap",
        "",
        *markdown_table(
            stable_overlap,
            ["repeats", "total", "both_solved_any", "march_only_any", "cadical_only_any", "both_unsolved_all", "union_solved_any"],
        ),
        "",
        "## Strong-Solver-Hard Subset",
        "",
        *markdown_table(stable_hard, ["file_key", "cadical", "march"]),
        "",
        "## Decision",
        "",
        "- 3SAT-450 remains nontrivial beyond the 8-instance smoke: March and",
        "  CaDiCaL both leave a nonempty hard subset under the 60s gate.",
        f"- This gate currently has {repeat_count} repeat(s). The repeated",
        "  March/CaDiCaL solved patterns are stable in the current run.",
        "- The next experiment should evaluate the frozen neural workflow only on",
        "  the repeated strong-solver-hard subset.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/benchmark_3sat450_gate/combined.csv",
        "runs/analysis/benchmark_3sat450_gate/summary.csv",
        "runs/analysis/benchmark_3sat450_gate/solver_overlap_by_repeat.csv",
        "runs/analysis/benchmark_3sat450_gate/solver_overlap_stable.csv",
        "runs/analysis/benchmark_3sat450_gate/solver_instance_repeats.csv",
        "runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(repeat_overlap.to_string(index=False))
    print(stable_overlap.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
