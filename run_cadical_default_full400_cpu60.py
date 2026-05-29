from __future__ import annotations

import argparse
import csv
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


DEFAULT_INPUT = "data/test/3sat/400/*.cnf"
DEFAULT_OUTPUT = Path("runs/cadical/solver_stats_full400_cpu60.csv")
DEFAULT_SOLVER = Path("solvers/cadical/cadical")
FIELDNAMES = [
    "file",
    "Result",
    "time",
    "wall_time",
    "external_timeout",
    "returncode",
    "stdout_head",
    "stderr_head",
]


def existing_files(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    with output_path.open(newline="") as handle:
        return {row["file"] for row in csv.DictReader(handle) if row.get("file")}


def parse_result(stdout: str, returncode: int) -> str:
    for line in stdout.splitlines():
        if line.startswith("s "):
            return line.split()[1]
    if returncode == 10:
        return "SATISFIABLE"
    if returncode == 20:
        return "UNSATISFIABLE"
    return "UNKNOWN"


def solve_one(file_path: str, solver: str, time_limit: float, external_timeout: float) -> dict[str, object]:
    command = [solver, "-q", "-t", f"{time_limit:g}", file_path]
    start = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=external_timeout)
        wall_time = time.monotonic() - start
        result = parse_result(proc.stdout, proc.returncode)
        reported_time = wall_time if result in {"SATISFIABLE", "UNSATISFIABLE"} else time_limit
        return {
            "file": file_path,
            "Result": result,
            "time": reported_time,
            "wall_time": wall_time,
            "external_timeout": False,
            "returncode": proc.returncode,
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
            "file": file_path,
            "Result": "UNKNOWN",
            "time": time_limit,
            "wall_time": wall_time,
            "external_timeout": True,
            "returncode": "timeout",
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
    parser = argparse.ArgumentParser(description="Run unguided CaDiCaL on full400 with a 60s wall-time cap.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--solver", type=Path, default=DEFAULT_SOLVER)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    files = sorted(str(path) for path in Path().glob(args.input))
    done = existing_files(args.output)
    pending = [path for path in files if path not in done]
    print(f"found={len(files)} done={len(done)} pending={len(pending)} output={args.output}", flush=True)
    if not pending:
        return

    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(solve_one, path, str(args.solver), args.limit, args.timeout): path
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
