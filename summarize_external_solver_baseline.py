from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize external SAT solver baseline CSVs.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    if "repeat" not in frame.columns:
        frame["repeat"] = 0
    if "solver_name" not in frame.columns:
        frame["solver_name"] = args.input.parent.name
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"].astype(str).isin(SOLVED_RESULTS)
    frame["time"] = pd.to_numeric(frame["time"], errors="coerce")
    frame["wall_time"] = pd.to_numeric(frame["wall_time"], errors="coerce")
    frame["external_timeout"] = frame["external_timeout"].astype(str).str.lower().isin({"true", "1", "yes"})

    args.output_dir.mkdir(parents=True, exist_ok=True)

    repeat_rows = []
    for (solver_name, repeat), group in frame.groupby(["solver_name", "repeat"], sort=True):
        repeat_rows.append(
            {
                "solver_name": solver_name,
                "repeat": int(repeat),
                "total": int(len(group)),
                "solved": int(group["solved"].sum()),
                "unknown": int((~group["solved"]).sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
                "mean_wall_time": float(group["wall_time"].mean()),
                "external_timeouts": int(group["external_timeout"].sum()),
            }
        )
    repeat_summary = pd.DataFrame(repeat_rows)
    repeat_summary.to_csv(args.output_dir / "repeat_summary.csv", index=False)

    aggregate_rows = []
    for solver_name, group in repeat_summary.groupby("solver_name", sort=True):
        aggregate_rows.append(
            {
                "solver_name": solver_name,
                "repeats": int(len(group)),
                "solved_mean": float(group["solved"].mean()),
                "solved_std": float(group["solved"].std(ddof=0)),
                "solved_min": int(group["solved"].min()),
                "solved_max": int(group["solved"].max()),
                "mean_time_mean": float(group["mean_time"].mean()),
                "mean_time_std": float(group["mean_time"].std(ddof=0)),
            }
        )
    aggregate = pd.DataFrame(aggregate_rows)
    aggregate.to_csv(args.output_dir / "aggregate.csv", index=False)

    instance_rows = []
    for (solver_name, file_key), group in frame.groupby(["solver_name", "file_key"], sort=True):
        group = group.sort_values("repeat")
        solved_repeats = int(group["solved"].sum())
        instance_rows.append(
            {
                "solver_name": solver_name,
                "file_key": file_key,
                "repeats": int(len(group)),
                "solved_repeats": solved_repeats,
                "stable_solved": solved_repeats in {0, len(group)},
                "time_mean": float(group["time"].mean()),
                "time_min": float(group["time"].min()),
                "time_max": float(group["time"].max()),
                "results": ",".join(group["Result"].astype(str).tolist()),
            }
        )
    instance_summary = pd.DataFrame(instance_rows)
    instance_summary.to_csv(args.output_dir / "instance_summary.csv", index=False)

    unstable = instance_summary.loc[~instance_summary["stable_solved"]].sort_values(
        ["solver_name", "file_key"]
    )
    unstable.to_csv(args.output_dir / "unstable_instances.csv", index=False)

    print(repeat_summary.to_string(index=False))
    print(aggregate.to_string(index=False))
    print(args.output_dir)


if __name__ == "__main__":
    main()
