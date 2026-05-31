from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
IN_DIR = ROOT / "runs/analysis/benchmark_candidate_smoke"
OUT_DIR = ROOT / "runs/analysis/benchmark_candidate_smoke"
DOC_PATH = ROOT / "docs/benchmark_candidate_smoke.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def parse_name(path: Path) -> tuple[str, str, int]:
    # <solver>_<family>_<size>_repeat0.csv
    parts = path.stem.split("_")
    if len(parts) < 4:
        raise ValueError(f"Unexpected candidate smoke filename: {path.name}")
    solver = parts[0]
    family = parts[1]
    size = int(parts[2])
    return solver, family, size


def load_all() -> pd.DataFrame:
    frames = []
    for path in sorted(IN_DIR.glob("*_*_*_repeat0.csv")):
        solver, family, size = parse_name(path)
        frame = pd.read_csv(path)
        frame["solver_name"] = solver
        frame["family"] = family
        frame["size"] = size
        frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
        frame["solved"] = frame["Result"].astype(str).isin(SOLVED)
        frame["time"] = pd.to_numeric(frame["time"], errors="coerce")
        frame["wall_time"] = pd.to_numeric(frame["wall_time"], errors="coerce")
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No candidate smoke CSVs found in {IN_DIR}")
    return pd.concat(frames, ignore_index=True)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
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
    frame = load_all()
    frame.to_csv(OUT_DIR / "combined.csv", index=False)

    summary_rows = []
    for (family, size, solver), group in frame.groupby(["family", "size", "solver_name"], sort=True):
        summary_rows.append(
            {
                "family": family,
                "size": int(size),
                "solver": solver,
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
    summary = pd.DataFrame(summary_rows).sort_values(["family", "size", "solver"])
    summary.to_csv(OUT_DIR / "summary.csv", index=False)

    overlap_rows = []
    for (family, size), group in frame.groupby(["family", "size"], sort=True):
        pivot = group.pivot_table(index="file_key", columns="solver_name", values="solved", aggfunc="first")
        if not {"march", "cadical"}.issubset(pivot.columns):
            continue
        march = pivot["march"].astype(bool)
        cadical = pivot["cadical"].astype(bool)
        overlap_rows.append(
            {
                "family": family,
                "size": int(size),
                "total": int(len(pivot)),
                "both_solved": int((march & cadical).sum()),
                "march_only": int((march & ~cadical).sum()),
                "cadical_only": int((~march & cadical).sum()),
                "both_unknown": int((~march & ~cadical).sum()),
                "union_solved": int((march | cadical).sum()),
            }
        )
    overlap = pd.DataFrame(overlap_rows).sort_values(["family", "size"])
    overlap.to_csv(OUT_DIR / "solver_overlap.csv", index=False)

    lines = [
        "# Benchmark Candidate Smoke",
        "",
        "Scope: search for candidate benchmark regimes where the current strong",
        "solver artifacts are not trivially dominant. This is a small smoke gate",
        "only. It does not train neural models, change selectors, or tune thresholds.",
        "",
        "Generated candidates:",
        "",
        "```text",
        "data/benchmark_candidates/3sat/450/*.cnf",
        "data/benchmark_candidates/3sat/500/*.cnf",
        "data/benchmark_candidates/coloring/400/*.cnf",
        "data/benchmark_candidates/coloring/500/*.cnf",
        "```",
        "",
        "## Solver Summary",
        "",
        *markdown_table(
            summary,
            ["family", "size", "solver", "total", "solved", "unknown", "mean_time", "median_time", "max_time"],
        ),
        "",
        "## March / CaDiCaL Overlap",
        "",
        *markdown_table(
            overlap,
            ["family", "size", "total", "both_solved", "march_only", "cadical_only", "both_unknown", "union_solved"],
        ),
        "",
        "## Decision",
        "",
        "- Coloring 400 is too easy for both solver families in this smoke gate.",
        "- Coloring 500 creates one March timeout, but CaDiCaL solves all 8 smoke",
        "  instances; this is a solver-family difference, not a strong-solver-hard",
        "  benchmark.",
        "- Random 3SAT-450 is the first useful candidate: March solves 2/8,",
        "  CaDiCaL solves 5/8, and 3 instances are unsolved by both within the",
        "  60s gate. This is a plausible next benchmark-regime probe.",
        "- Random 3SAT-500 is harder: March solves 2/8 and CaDiCaL solves 1/8.",
        "  It may be too hard for the current neural workflow, but it is useful",
        "  as a strong-solver-hard stress test.",
        "- The next top-conference-oriented experiment should not tune selectors.",
        "  It should generate a moderate 3SAT-450 candidate set, run March and",
        "  CaDiCaL repeats, then test whether the frozen neural workflow solves",
        "  any repeated-strong-solver-hard instances.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/benchmark_candidate_smoke/combined.csv",
        "runs/analysis/benchmark_candidate_smoke/summary.csv",
        "runs/analysis/benchmark_candidate_smoke/solver_overlap.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
