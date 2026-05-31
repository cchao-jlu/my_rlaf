from __future__ import annotations

import argparse
import csv
import glob
import shlex
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}
FIELDNAMES = [
    "solver_name",
    "repeat",
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


def parse_result(stdout: str, returncode: int) -> str:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("s "):
            parts = stripped.split()
            if len(parts) >= 2:
                return parts[1]
        if stripped in SOLVED_RESULTS:
            return stripped
    if returncode == 10:
        return "SATISFIABLE"
    if returncode == 20:
        return "UNSATISFIABLE"
    return "UNKNOWN"


def existing_keys(output_path: Path) -> set[tuple[str, str]]:
    if not output_path.exists():
        return set()
    with output_path.open(newline="") as handle:
        return {
            (row.get("repeat", ""), row.get("file", ""))
            for row in csv.DictReader(handle)
            if row.get("file")
        }


def build_command(template: str, solver: Path, cnf: str, limit: float) -> list[str]:
    rendered = template.format(solver=str(solver), file=cnf, limit=f"{limit:g}")
    return shlex.split(rendered)


def solve_one(
    solver_name: str,
    repeat: int,
    solver: Path,
    command_template: str,
    cnf: str,
    time_limit: float,
    external_timeout: float,
) -> dict[str, object]:
    command = build_command(command_template, solver, cnf, time_limit)
    start = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=external_timeout)
        wall_time = time.monotonic() - start
        result = parse_result(proc.stdout, proc.returncode)
        reported_time = wall_time if result in SOLVED_RESULTS else time_limit
        return {
            "solver_name": solver_name,
            "repeat": repeat,
            "file": cnf,
            "Result": result,
            "time": reported_time,
            "wall_time": wall_time,
            "external_timeout": False,
            "returncode": proc.returncode,
            "command": " ".join(command),
            "stdout_head": proc.stdout.splitlines()[:3],
            "stderr_head": proc.stderr.splitlines()[:3],
        }
    except subprocess.TimeoutExpired as exc:
        wall_time = time.monotonic() - start
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "solver_name": solver_name,
            "repeat": repeat,
            "file": cnf,
            "Result": "UNKNOWN",
            "time": time_limit,
            "wall_time": wall_time,
            "external_timeout": True,
            "returncode": "timeout",
            "command": " ".join(command),
            "stdout_head": stdout.splitlines()[:3],
            "stderr_head": stderr.splitlines()[:3],
        }


def append_row(output_path: Path, row: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_path.exists()
    with output_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a generic external SAT solver baseline with a fixed wall-clock cap."
    )
    parser.add_argument("--solver", type=Path, required=True, help="Path to the solver executable.")
    parser.add_argument("--solver-name", required=True, help="Name to record in output CSV, e.g. kissat.")
    parser.add_argument("--input", default="data/test/3sat/400/*.cnf")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=float, default=60.0, help="Nominal solver budget in seconds.")
    parser.add_argument("--timeout", type=float, default=65.0, help="External timeout in seconds.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--n", type=int, default=0, help="Optional smoke limit. 0 means all matched CNFs.")
    parser.add_argument(
        "--cmd-template",
        default="{solver} {file}",
        help=(
            "Shell-like command template. Available placeholders: {solver}, {file}, {limit}. "
            "Example for CaDiCaL: '{solver} -q -t {limit} {file}'."
        ),
    )
    args = parser.parse_args()

    if not args.solver.exists():
        raise FileNotFoundError(args.solver)

    files = sorted(glob.glob(args.input))
    if args.n > 0:
        files = files[: args.n]

    done = existing_keys(args.output)
    pending = [path for path in files if (str(args.repeat), path) not in done]
    print(
        f"solver={args.solver_name} repeat={args.repeat} found={len(files)} "
        f"done={len(done)} pending={len(pending)} output={args.output}",
        flush=True,
    )
    if not pending:
        return

    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                solve_one,
                args.solver_name,
                args.repeat,
                args.solver,
                args.cmd_template,
                path,
                args.limit,
                args.timeout,
            ): path
            for path in pending
        }
        for future in as_completed(futures):
            path = futures[future]
            row = future.result()
            append_row(args.output, row)
            completed += 1
            print(
                f"[{completed}/{len(pending)}] {Path(path).name} "
                f"{row['Result']} time={float(row['time']):.3f} "
                f"wall={float(row['wall_time']):.3f} "
                f"external_timeout={row['external_timeout']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
