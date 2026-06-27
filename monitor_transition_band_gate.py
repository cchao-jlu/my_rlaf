from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_raw_name(path: Path) -> tuple[str, int, int] | None:
    parts = path.stem.split("_")
    if len(parts) < 5:
        return None
    solver = parts[0]
    try:
        size = int(parts[2])
        instances = int(parts[3].removeprefix("n"))
    except ValueError:
        return None
    return solver, size, instances


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor a transition-band strong-solver gate.")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "runs/analysis/benchmark_transition_band_residual_large/raw")
    parser.add_argument("--sizes", type=int, nargs="*", default=None)
    parser.add_argument("--solvers", nargs="*", default=["march", "cadical"])
    parser.add_argument("--instances", type=int, default=None)
    args = parser.parse_args()

    raw_dir = args.raw_dir.resolve()
    rows = []
    for path in sorted(raw_dir.glob("*.csv")):
        parsed = parse_raw_name(path)
        if parsed is None:
            continue
        solver, size, instances = parsed
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            frame = pd.DataFrame()
        result = frame["Result"].astype(str) if "Result" in frame else pd.Series(dtype=str)
        solved = int(result.isin(SOLVED_RESULTS).sum())
        unknown = int(result.eq("UNKNOWN").sum())
        rows.append(
            {
                "solver": solver,
                "size": size,
                "target_instances": instances,
                "rows": int(len(frame)),
                "pending": int(max(instances - len(frame), 0)),
                "solved": solved,
                "unknown": unknown,
                "path": display_path(path),
            }
        )

    observed = {(row["solver"], row["size"]) for row in rows}
    if args.sizes is not None and args.instances is not None:
        for size in args.sizes:
            for solver in args.solvers:
                if (solver, size) in observed:
                    continue
                rows.append(
                    {
                        "solver": solver,
                        "size": int(size),
                        "target_instances": int(args.instances),
                        "rows": 0,
                        "pending": int(args.instances),
                        "solved": 0,
                        "unknown": 0,
                        "path": "missing",
                    }
                )

    if not rows:
        print(f"No raw CSVs found in {display_path(raw_dir)}")
        return
    summary = pd.DataFrame(rows).sort_values(["size", "solver"]).reset_index(drop=True)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
