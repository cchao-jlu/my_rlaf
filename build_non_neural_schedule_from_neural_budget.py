from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SCHEDULE_SOLVERS = [
    "march",
    "cadical",
    "cadical_seed1",
    "cadical_seed2",
    "cadical_seed3",
    "cadical_plain_seed1",
    "cadical_plain_seed2",
    "cadical_sat_seed1",
    "cadical_unsat_seed1",
    "cadical_shuffle_seed1",
    "cadical_shuffle_seed2",
]
SCHEDULE_VARIANT_DETAILS = {
    "march": "binary=march args=<none>",
    "cadical": "binary=cadical args=<none>",
    "cadical_seed1": "binary=cadical args=--seed=1",
    "cadical_seed2": "binary=cadical args=--seed=2",
    "cadical_seed3": "binary=cadical args=--seed=3",
    "cadical_plain_seed1": "binary=cadical args=--plain --seed=1",
    "cadical_plain_seed2": "binary=cadical args=--plain --seed=2",
    "cadical_sat_seed1": "binary=cadical args=--sat --seed=1",
    "cadical_unsat_seed1": "binary=cadical args=--unsat --seed=1",
    "cadical_shuffle_seed1": "binary=cadical args=--shuffle --seed=1",
    "cadical_shuffle_seed2": "binary=cadical args=--shuffle --seed=2",
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_schedule(total_budget: float, solver_cycle: list[str], attempt_limit: float) -> list[tuple[str, float]]:
    if total_budget <= 0:
        raise ValueError("total_budget must be positive.")
    if attempt_limit <= 0:
        raise ValueError("attempt_limit must be positive.")
    if not solver_cycle:
        raise ValueError("solver_cycle must contain at least one solver variant.")
    schedule: list[tuple[str, float]] = []
    remaining = float(total_budget)
    idx = 0
    while remaining > 1e-9:
        solver = solver_cycle[idx % len(solver_cycle)]
        limit = min(float(attempt_limit), remaining)
        schedule.append((solver, limit))
        remaining -= limit
        idx += 1
    return schedule


def format_schedule(schedule: list[tuple[str, float]]) -> str:
    return ",".join(f"{solver}:{limit:g}" for solver, limit in schedule)


def format_variant_details(solver_cycle: list[str]) -> str:
    return "; ".join(f"{solver}({SCHEDULE_VARIANT_DETAILS[solver]})" for solver in solver_cycle)


def markdown_table(frame: pd.DataFrame) -> list[str]:
    lines = ["| " + " | ".join(frame.columns) + " |", "| " + " | ".join("---" for _ in frame.columns) + " |"]
    for _, row in frame.iterrows():
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(args: argparse.Namespace, schedule: list[tuple[str, float]], summary: pd.DataFrame) -> None:
    lines = [
        "# Non-Neural Schedule From Neural Budget",
        "",
        "Scope: derive a fixed same-budget non-neural rerun schedule from the",
        "allocated residual CPU budget of the frozen neural portfolio. Use this",
        "schedule before held-out evaluation; do not tune it on held-out results.",
        "",
        f"Neural summary: `{display_path(args.neural_summary.resolve())}`.",
        f"Neural summary SHA256: `{file_sha256(args.neural_summary.resolve())}`.",
        f"Source split: `{args.source_split}`.",
        f"Budget aggregation: `{args.aggregation}`.",
        f"Attempt limit: {args.attempt_limit:g}.",
        f"Solver cycle: {', '.join(args.solver_cycle)}.",
        f"Solver variant details: {format_variant_details(args.solver_cycle)}.",
        "",
        "## Schedule",
        "",
        "```text",
        format_schedule(schedule),
        "```",
        "",
        "## Budget Summary",
        "",
        *markdown_table(summary),
        "",
    ]
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a fixed non-neural schedule from neural allocated budget.")
    parser.add_argument("--neural-summary", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument(
        "--source-split",
        choices=["dev", "train", "heldout", "unknown"],
        default="dev",
        help="Split used to derive this schedule. Paper protocol audits require dev.",
    )
    parser.add_argument(
        "--selector-spec",
        type=Path,
        default=None,
        help="Optional frozen selector spec used by the dev neural summary.",
    )
    parser.add_argument("--aggregation", choices=["mean", "max"], default="mean")
    parser.add_argument("--attempt-limit", type=float, default=60.0)
    parser.add_argument("--first-solver", choices=SCHEDULE_SOLVERS, default="march")
    parser.add_argument("--second-solver", choices=SCHEDULE_SOLVERS, default="cadical_seed1")
    parser.add_argument(
        "--solver-cycle",
        nargs="+",
        choices=SCHEDULE_SOLVERS,
        default=None,
        help=(
            "Fixed solver/config variant cycle for the same-budget control. "
            "Defaults to --first-solver followed by --second-solver."
        ),
    )
    args = parser.parse_args()

    frame = pd.read_csv(args.neural_summary)
    required = {"size", "file_key", "total_cpu_allocated"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Neural summary is missing columns: {sorted(missing)}")
    per_instance = (
        frame.groupby(["size", "file_key"], sort=True)["total_cpu_allocated"]
        .mean()
        .astype(float)
        .reset_index(name="total_cpu_allocated")
    )
    if args.aggregation == "mean":
        total_budget = float(per_instance["total_cpu_allocated"].mean())
    else:
        total_budget = float(per_instance["total_cpu_allocated"].max())
    if args.solver_cycle is None:
        args.solver_cycle = [args.first_solver, args.second_solver]
    schedule = build_schedule(
        total_budget=total_budget,
        solver_cycle=list(args.solver_cycle),
        attempt_limit=args.attempt_limit,
    )
    summary = pd.DataFrame(
        [
            {
                "instances": int(len(per_instance)),
                "neural_summary": display_path(args.neural_summary.resolve()),
                "neural_summary_sha256": file_sha256(args.neural_summary.resolve()),
                "source_split": args.source_split,
                "selector_spec": display_path(args.selector_spec.resolve()) if args.selector_spec else "",
                "selector_spec_sha256": file_sha256(args.selector_spec.resolve()) if args.selector_spec else "",
                "aggregation": args.aggregation,
                "attempt_limit": float(args.attempt_limit),
                "solver_cycle": ",".join(args.solver_cycle),
                "solver_variant_details": format_variant_details(args.solver_cycle),
                "schedule_mode": "dev_budget_rule",
                "neural_budget_min": float(per_instance["total_cpu_allocated"].min()),
                "neural_budget_mean": float(per_instance["total_cpu_allocated"].mean()),
                "neural_budget_max": float(per_instance["total_cpu_allocated"].max()),
                "selected_budget": total_budget,
                "schedule": format_schedule(schedule),
            }
        ]
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_csv, index=False)
    write_doc(args=args, schedule=schedule, summary=summary)
    print(summary.to_string(index=False))
    print(f"--schedule {format_schedule(schedule)}")
    print(display_path(args.output_csv.resolve()))
    print(display_path(args.doc.resolve()))


if __name__ == "__main__":
    main()
