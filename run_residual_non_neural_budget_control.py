from __future__ import annotations

import argparse
import csv
import shlex
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "data/benchmark_transition_band_expanded"
BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv"
OUT_DIR = ROOT / "runs/analysis/benchmark_residual_non_neural_budget_control"
ATTEMPT_DIR = OUT_DIR / "attempts"
RAW_CSV = OUT_DIR / "raw_attempts.csv"
INSTANCE_CSV = OUT_DIR / "instance_summary.csv"
SCHEDULE_CSV = OUT_DIR / "schedule.csv"
DOC_PATH = ROOT / "docs/benchmark_residual_non_neural_budget_control.md"

SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}
SOLVER_VARIANTS = {
    "march": {
        "binary": "march",
        "args": [],
        "budget_enforcement": "external_wall_clock_timeout",
    },
    "cadical": {
        "binary": "cadical",
        "args": [],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_seed1": {
        "binary": "cadical",
        "args": ["--seed=1"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_seed2": {
        "binary": "cadical",
        "args": ["--seed=2"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_seed3": {
        "binary": "cadical",
        "args": ["--seed=3"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_plain_seed1": {
        "binary": "cadical",
        "args": ["--plain", "--seed=1"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_plain_seed2": {
        "binary": "cadical",
        "args": ["--plain", "--seed=2"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_sat_seed1": {
        "binary": "cadical",
        "args": ["--sat", "--seed=1"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_unsat_seed1": {
        "binary": "cadical",
        "args": ["--unsat", "--seed=1"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_shuffle_seed1": {
        "binary": "cadical",
        "args": ["--shuffle", "--seed=1"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
    "cadical_shuffle_seed2": {
        "binary": "cadical",
        "args": ["--shuffle", "--seed=2"],
        "budget_enforcement": "internal_wall_clock_limit_plus_external_timeout",
    },
}

SOLVERS = {
    "march": ROOT / "solvers/march/march_nh",
    "cadical": ROOT / "solvers/cadical/cadical",
}
FIELDNAMES = [
    "family",
    "size",
    "file_key",
    "attempt_id",
    "solver_name",
    "solver_binary",
    "solver_args",
    "limit",
    "budget_enforcement",
    "schedule_mode",
    "instance_schedule",
    "file",
    "Result",
    "time",
    "wall_time",
    "external_timeout",
    "returncode",
    "command",
    "stdout_head",
    "stderr_head",
]


def parse_schedule(raw: str) -> list[tuple[str, float]]:
    schedule = []
    for idx, part in enumerate(raw.split(",")):
        item = part.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid schedule entry {item!r}; expected solver:seconds.")
        solver_name, limit_raw = item.split(":", 1)
        solver_name = solver_name.strip()
        if solver_name not in SOLVER_VARIANTS:
            raise ValueError(f"Unknown solver in schedule entry {idx}: {solver_name}")
        limit = float(limit_raw)
        if limit <= 0:
            raise ValueError(f"Schedule limit must be positive: {item}")
        schedule.append((solver_name, limit))
    if not schedule:
        raise ValueError("At least one non-neural schedule entry is required.")
    return schedule


def format_schedule(schedule: list[tuple[str, float]]) -> str:
    return ",".join(f"{solver}:{limit:g}" for solver, limit in schedule)


def schedule_from_budget(total_budget: float, solver_cycle: list[str], attempt_limit: float) -> list[tuple[str, float]]:
    if total_budget <= 0:
        raise ValueError(f"total_budget must be positive, got {total_budget}")
    if attempt_limit <= 0:
        raise ValueError(f"attempt_limit must be positive, got {attempt_limit}")
    if not solver_cycle:
        raise ValueError("solver_cycle must contain at least one solver variant.")
    schedule: list[tuple[str, float]] = []
    remaining = float(total_budget)
    idx = 0
    while remaining > 1e-9:
        solver_name = solver_cycle[idx % len(solver_cycle)]
        if solver_name not in SOLVER_VARIANTS:
            raise ValueError(f"Unknown solver in solver_cycle: {solver_name}")
        limit = min(float(attempt_limit), remaining)
        schedule.append((solver_name, limit))
        remaining -= limit
        idx += 1
    return schedule


def load_schedule(schedule: str, schedule_csv: Path | None) -> tuple[list[tuple[str, float]], str, dict[str, str]]:
    if schedule_csv is None:
        return parse_schedule(schedule), "command_line", {}
    if not schedule_csv.exists():
        raise FileNotFoundError(schedule_csv)
    frame = pd.read_csv(schedule_csv)
    if frame.empty or "schedule" not in frame.columns:
        raise ValueError(f"Schedule CSV must contain a non-empty schedule column: {schedule_csv}")
    metadata = {str(key): str(value) for key, value in frame.iloc[0].dropna().to_dict().items()}
    return parse_schedule(str(frame.iloc[0]["schedule"])), display_path(schedule_csv.resolve()), metadata


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_subset(
    input_csv: Path,
    limit_instances: int = 0,
    sizes: set[int] | None = None,
    file_keys: set[str] | None = None,
) -> pd.DataFrame:
    frame = pd.read_csv(input_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {sorted(missing)}")
    if limit_instances > 0:
        frame = frame.head(limit_instances).copy()
    if sizes:
        frame = frame[frame["size"].astype(int).isin(sizes)].copy()
    if file_keys:
        frame = frame[frame["file_key"].astype(str).isin(file_keys)].copy()
    if frame.empty:
        raise ValueError("No residual instances selected.")
    return frame


def attach_instance_budgets(
    subset: pd.DataFrame,
    neural_budget_summary: Path,
    schedule_metadata: dict[str, str],
    fallback_schedule: list[tuple[str, float]],
) -> tuple[pd.DataFrame, str]:
    if not neural_budget_summary.exists():
        raise FileNotFoundError(neural_budget_summary)
    neural = pd.read_csv(neural_budget_summary)
    required = {"size", "file_key", "total_cpu_allocated"}
    missing = required - set(neural.columns)
    if missing:
        raise ValueError(f"Neural budget summary is missing columns: {sorted(missing)}")
    if "solver_cycle" in schedule_metadata and schedule_metadata["solver_cycle"].strip():
        solver_cycle = [part.strip() for part in schedule_metadata["solver_cycle"].split(",") if part.strip()]
    else:
        solver_cycle = [solver for solver, _ in fallback_schedule]
    if "attempt_limit" in schedule_metadata and str(schedule_metadata["attempt_limit"]).strip():
        attempt_limit = float(schedule_metadata["attempt_limit"])
    else:
        attempt_limit = max(limit for _, limit in fallback_schedule)
    budgets = (
        neural.groupby(["size", "file_key"], sort=True)["total_cpu_allocated"]
        .mean()
        .astype(float)
        .reset_index(name="neural_total_cpu_allocated")
    )
    budgeted = subset.merge(budgets, on=["size", "file_key"], how="left", validate="one_to_one")
    missing_budget = int(budgeted["neural_total_cpu_allocated"].isna().sum())
    if missing_budget:
        missing_rows = budgeted[budgeted["neural_total_cpu_allocated"].isna()][["size", "file_key"]].head(10)
        raise ValueError(f"Missing neural budgets for {missing_budget} instances, examples={missing_rows.to_dict('records')}")
    budgeted["non_neural_schedule"] = budgeted["neural_total_cpu_allocated"].map(
        lambda value: format_schedule(schedule_from_budget(float(value), solver_cycle=solver_cycle, attempt_limit=attempt_limit))
    )
    return budgeted, f"{display_path(neural_budget_summary.resolve())} per_instance_total_cpu_allocated"


def instance_file(cnf_root: Path, family: str, size: int, file_key: str, cnf_path: str | None = None) -> Path:
    if cnf_path and str(cnf_path) != "nan":
        path = Path(cnf_path)
        if not path.is_absolute():
            path = ROOT / path
    else:
        path = cnf_root / family / str(size) / file_key
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def parse_result(stdout: str, returncode: int) -> str:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("s "):
            parts = stripped.split()
            if len(parts) >= 2:
                return parts[1]
        if stripped in SOLVED:
            return stripped
    if returncode == 10:
        return "SATISFIABLE"
    if returncode == 20:
        return "UNSATISFIABLE"
    return "UNKNOWN"


def build_command(solver_name: str, cnf_path: Path, limit: float) -> list[str]:
    variant = SOLVER_VARIANTS[solver_name]
    binary_name = str(variant["binary"])
    solver_path = SOLVERS[binary_name]
    if not solver_path.exists():
        raise FileNotFoundError(solver_path)
    if binary_name == "cadical":
        return [str(solver_path), "-q", "-t", f"{limit:g}", *list(variant["args"]), str(cnf_path)]
    if binary_name == "march":
        return [str(solver_path), str(cnf_path)]
    raise ValueError(f"Unknown solver: {solver_name}")


def budget_enforcement(solver_name: str) -> str:
    return str(SOLVER_VARIANTS[solver_name]["budget_enforcement"])


def solve_attempt(task: dict) -> dict:
    solver_name = str(task["solver_name"])
    limit = float(task["limit"])
    cnf_path = Path(str(task["file"]))
    command = build_command(solver_name=solver_name, cnf_path=cnf_path, limit=limit)
    timeout = limit + 5.0
    start = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        wall_time = time.monotonic() - start
        result = parse_result(proc.stdout, proc.returncode)
        reported_time = min(wall_time, limit) if result in SOLVED else limit
        row = dict(task)
        row.update(
            {
                "Result": result,
                "time": reported_time,
                "wall_time": wall_time,
                "external_timeout": False,
                "returncode": proc.returncode,
                "command": " ".join(command),
                "stdout_head": proc.stdout.splitlines()[:3],
                "stderr_head": proc.stderr.splitlines()[:3],
            }
        )
        return row
    except subprocess.TimeoutExpired as exc:
        wall_time = time.monotonic() - start
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        row = dict(task)
        row.update(
            {
                "Result": "UNKNOWN",
                "time": limit,
                "wall_time": wall_time,
                "external_timeout": True,
                "returncode": "timeout",
                "command": " ".join(command),
                "stdout_head": stdout.splitlines()[:3],
                "stderr_head": stderr.splitlines()[:3],
            }
        )
        return row


def attempt_paths(size: int, file_key: str, attempt_id: int, solver_name: str, limit: float) -> Path:
    stem = f"size{size}_{Path(file_key).stem}_attempt{attempt_id}_{solver_name}_{limit:g}s"
    return ATTEMPT_DIR / f"{stem}.csv"


def read_attempt(path: Path) -> dict:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected one row in {path}, found {len(rows)}")
    return rows[0]


def write_attempt(path: Path, row: dict) -> None:
    ATTEMPT_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(row)


def build_tasks(subset: pd.DataFrame, schedule: list[tuple[str, float]], force: bool) -> tuple[list[dict], list[dict]]:
    pending = []
    completed = []
    for row in subset.itertuples(index=False):
        family = str(row.family)
        size = int(row.size)
        file_key = str(row.file_key)
        cnf_path_value = getattr(row, "cnf_path", None)
        cnf_path = instance_file(cnf_root=SOURCE_ROOT, family=family, size=size, file_key=file_key, cnf_path=cnf_path_value)
        row_schedule = getattr(row, "non_neural_schedule", None)
        if row_schedule is not None and str(row_schedule) != "nan" and str(row_schedule).strip():
            instance_schedule = parse_schedule(str(row_schedule))
            schedule_mode = "per_instance"
        else:
            instance_schedule = schedule
            schedule_mode = "global"
        for attempt_id, (solver_name, limit) in enumerate(instance_schedule):
            path = attempt_paths(size=size, file_key=file_key, attempt_id=attempt_id, solver_name=solver_name, limit=limit)
            if path.exists() and not force:
                completed.append(read_attempt(path))
                continue
            pending.append(
                {
                    "family": family,
                    "size": size,
                    "file_key": file_key,
                    "attempt_id": attempt_id,
                    "solver_name": solver_name,
                    "solver_binary": str(SOLVER_VARIANTS[solver_name]["binary"]),
                    "solver_args": " ".join(shlex.quote(arg) for arg in SOLVER_VARIANTS[solver_name]["args"]),
                    "limit": limit,
                    "budget_enforcement": budget_enforcement(solver_name),
                    "schedule_mode": schedule_mode,
                    "instance_schedule": format_schedule(instance_schedule),
                    "file": str(cnf_path),
                }
            )
    return pending, completed


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (family, size, file_key), group in raw.groupby(["family", "size", "file_key"], sort=True):
        group = group.copy()
        group["solved"] = group["Result"].astype(str).isin(SOLVED)
        solved = group[group["solved"]]
        rows.append(
            {
                "family": family,
                "size": int(size),
                "file_key": file_key,
                "attempts": int(len(group)),
                "schedule": ",".join(
                    f"{str(row.solver_name)}:{float(row.limit):g}"
                    for row in group.sort_values("attempt_id").itertuples(index=False)
                ),
                "schedule_mode": ",".join(sorted({str(value) for value in group["schedule_mode"].dropna().unique()}))
                if "schedule_mode" in group.columns
                else "unknown",
                "solver_binaries": ",".join(
                    str(row.solver_binary) for row in group.sort_values("attempt_id").itertuples(index=False)
                )
                if "solver_binary" in group.columns
                else "",
                "solver_args": " | ".join(
                    str(row.solver_args) for row in group.sort_values("attempt_id").itertuples(index=False)
                )
                if "solver_args" in group.columns
                else "",
                "budget_cpu_total": float(pd.to_numeric(group["limit"], errors="coerce").sum()),
                "used_capped_cpu_total": float(pd.to_numeric(group["time"], errors="coerce").sum()),
                "wall_time_total": float(pd.to_numeric(group["wall_time"], errors="coerce").sum()),
                "solved_any": bool(group["solved"].any()),
                "first_solved_attempt": int(solved.sort_values("attempt_id").iloc[0]["attempt_id"]) if not solved.empty else -1,
                "first_solved_solver": str(solved.sort_values("attempt_id").iloc[0]["solver_name"]) if not solved.empty else "",
                "best_time": float(pd.to_numeric(solved["time"], errors="coerce").min()) if not solved.empty else float(pd.to_numeric(group["time"], errors="coerce").min()),
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


def write_doc(
    input_csv: Path,
    cnf_root: Path,
    subset: pd.DataFrame,
    schedule: list[tuple[str, float]],
    schedule_source: str,
    budget_source: str,
    summary: pd.DataFrame,
) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    solved = int(summary["solved_any"].sum()) if not summary.empty else 0
    lines = [
        "# Residual Non-Neural Budget Control",
        "",
        "Scope: fixed same-budget non-neural rerun portfolio for the residual",
        "March/CaDiCaL both-unknown transition-band set. This is the required",
        "control for the residual neural restart portfolio mainline.",
        "",
        f"Input CSV: `{display_path(input_csv)}`.",
        f"CNF root: `{display_path(cnf_root)}`.",
        f"Input residual instances: {len(subset)}.",
        f"Fixed schedule: {', '.join(f'{solver}:{limit:g}s' for solver, limit in schedule)}.",
        f"Schedule source: `{schedule_source}`.",
        f"Budget source: `{budget_source}`.",
        "",
        "Budget enforcement:",
        "",
        "- CaDiCaL uses its internal wall-clock limit (`-t`) plus an external timeout.",
        "- CaDiCaL variants can fix seed/config options such as `--seed`, `--plain`,",
        "  `--sat`, `--unsat`, and `--shuffle` through the frozen schedule.",
        "- March has no internal limit in this unweighted binary, so the per-attempt",
        "  budget is enforced by external wall-clock timeout and capped CPU accounting.",
        "",
        "## Summary",
        "",
        f"Solved residual instances: {solved} / {len(summary)}",
        "",
        *markdown_table(
            summary,
            [
                "family",
                "size",
                "file_key",
                "attempts",
                "budget_cpu_total",
                "used_capped_cpu_total",
                "wall_time_total",
                "solved_any",
                "first_solved_attempt",
                "first_solved_solver",
            ],
        ),
        "",
        "Artifacts:",
        "",
        "```text",
        str(ATTEMPT_DIR.relative_to(ROOT)) + "/",
        str(RAW_CSV.relative_to(ROOT)),
        str(INSTANCE_CSV.relative_to(ROOT)),
        str(SCHEDULE_CSV.relative_to(ROOT)),
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_int_set(raw: str) -> set[int]:
    return {int(part.strip()) for part in raw.split(",") if part.strip()}


def parse_str_set(raw: str) -> set[str]:
    return {part.strip() for part in raw.split(",") if part.strip()}


def main() -> None:
    global SOURCE_ROOT
    global OUT_DIR
    global ATTEMPT_DIR
    global RAW_CSV
    global INSTANCE_CSV
    global SCHEDULE_CSV
    global DOC_PATH

    parser = argparse.ArgumentParser(description="Run fixed same-budget non-neural residual rerun control.")
    parser.add_argument("--input", type=Path, default=BOTH_UNKNOWN_CSV, help="Residual CSV with family,size,file_key columns.")
    parser.add_argument("--cnf-root", type=Path, default=SOURCE_ROOT, help="Root containing family/size/file_key CNFs.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    parser.add_argument(
        "--schedule",
        default="march:60,cadical:60",
        help=(
            "Comma-separated fixed schedule, e.g. "
            "march:60,cadical_seed1:60,cadical_plain_seed1:60."
        ),
    )
    parser.add_argument(
        "--schedule-csv",
        type=Path,
        default=None,
        help="CSV artifact with a schedule column. Overrides --schedule and records the artifact as the schedule source.",
    )
    parser.add_argument(
        "--neural-budget-summary",
        type=Path,
        default=None,
        help=(
            "Optional held-out neural summary with total_cpu_allocated. When set, the frozen solver/config cycle "
            "from --schedule-csv/--schedule is expanded per instance to match each neural allocated budget."
        ),
    )
    parser.add_argument("--limit-instances", type=int, default=0)
    parser.add_argument("--sizes", default="")
    parser.add_argument("--file-keys", default="")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()

    SOURCE_ROOT = args.cnf_root.resolve()
    OUT_DIR = args.out_dir.resolve()
    ATTEMPT_DIR = OUT_DIR / "attempts"
    RAW_CSV = OUT_DIR / "raw_attempts.csv"
    INSTANCE_CSV = OUT_DIR / "instance_summary.csv"
    SCHEDULE_CSV = OUT_DIR / "schedule.csv"
    DOC_PATH = args.doc.resolve()
    if args.schedule_csv is not None and args.schedule_csv.resolve() == SCHEDULE_CSV:
        raise ValueError(
            "--schedule-csv must not be the same path as the run output schedule.csv; "
            "keep the frozen source schedule artifact outside --out-dir or use a different filename."
        )

    schedule, schedule_source, schedule_metadata = load_schedule(
        args.schedule,
        args.schedule_csv.resolve() if args.schedule_csv else None,
    )
    sizes = parse_int_set(args.sizes) if args.sizes else None
    file_keys = parse_str_set(args.file_keys) if args.file_keys else None
    input_csv = args.input.resolve()
    subset = load_subset(input_csv=input_csv, limit_instances=args.limit_instances, sizes=sizes, file_keys=file_keys)
    budget_source = "global_schedule_budget"
    if args.neural_budget_summary is not None:
        subset, budget_source = attach_instance_budgets(
            subset=subset,
            neural_budget_summary=args.neural_budget_summary.resolve(),
            schedule_metadata=schedule_metadata,
            fallback_schedule=schedule,
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subset.to_csv(OUT_DIR / "both_unknown_subset.csv", index=False)
    schedule_rows = [
        {
            "attempt_id": attempt_id,
            "solver_name": solver_name,
            "limit": limit,
            "schedule_source": schedule_source,
            "budget_source": budget_source,
        }
        for attempt_id, (solver_name, limit) in enumerate(schedule)
    ]
    for key in ["neural_summary", "neural_summary_sha256", "source_split", "selector_spec", "selector_spec_sha256", "solver_cycle", "attempt_limit", "schedule_mode"]:
        if key in schedule_metadata:
            for row in schedule_rows:
                row[key] = schedule_metadata[key]
    pd.DataFrame(schedule_rows).to_csv(SCHEDULE_CSV, index=False)

    pending, completed = build_tasks(subset=subset, schedule=schedule, force=args.force)
    rows = list(completed)
    if args.summarize_only:
        if pending:
            raise FileNotFoundError(f"Missing {len(pending)} attempt artifacts for summarize-only.")
    else:
        print(f"completed={len(completed)} pending={len(pending)}", flush=True)
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(solve_attempt, task): task for task in pending}
            for idx, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                path = attempt_paths(
                    size=int(row["size"]),
                    file_key=str(row["file_key"]),
                    attempt_id=int(row["attempt_id"]),
                    solver_name=str(row["solver_name"]),
                    limit=float(row["limit"]),
                )
                write_attempt(path, row)
                rows.append(row)
                print(
                    f"[{idx}/{len(pending)}] {row['size']}/{row['file_key']} "
                    f"{row['solver_name']} result={row['Result']} time={float(row['time']):.3f}",
                    flush=True,
                )

    raw = pd.DataFrame(rows)
    if raw.empty:
        raise ValueError("No attempt rows available.")
    raw = raw.sort_values(["size", "file_key", "attempt_id"]).reset_index(drop=True)
    raw.to_csv(RAW_CSV, index=False)
    summary = summarize(raw)
    summary.to_csv(INSTANCE_CSV, index=False)
    write_doc(
        input_csv=input_csv,
        cnf_root=SOURCE_ROOT,
        subset=subset,
        schedule=schedule,
        schedule_source=schedule_source,
        budget_source=budget_source,
        summary=summary,
    )
    print(summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
