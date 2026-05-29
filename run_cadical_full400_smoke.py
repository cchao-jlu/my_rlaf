from __future__ import annotations

import argparse
import csv
import subprocess
import time
from pathlib import Path


DEFAULT_OUTPUT = Path("runs/analysis/cadical_smoke/smoke.csv")
DEFAULT_SOLVER = Path("solvers/cadical/cadical")


def parse_result(stdout: str, returncode: int) -> str:
    for line in stdout.splitlines():
        if line.startswith("s "):
            return line.split()[1]
    if returncode == 10:
        return "SATISFIABLE"
    if returncode == 20:
        return "UNSATISFIABLE"
    return "UNKNOWN"


def run_one(solver: Path, cnf: Path, time_limit: float, external_timeout: float) -> dict[str, object]:
    command = [str(solver), "-q", "-t", f"{time_limit:g}", str(cnf)]
    start = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=external_timeout)
        wall_time = time.monotonic() - start
        result = parse_result(proc.stdout, proc.returncode)
        return {
            "file": str(cnf),
            "Result": result,
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
            "file": str(cnf),
            "Result": "UNKNOWN",
            "wall_time": wall_time,
            "external_timeout": True,
            "returncode": "timeout",
            "stdout_head": stdout.splitlines()[:3],
            "stderr_head": stderr.splitlines()[:3],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test CaDiCaL on a small full400 subset.")
    parser.add_argument("--input", default="data/test/3sat/400/*.cnf")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--solver", type=Path, default=DEFAULT_SOLVER)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    files = sorted(Path().glob(args.input))[: args.n]
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for cnf in files:
        row = run_one(args.solver, cnf, args.limit, args.timeout)
        rows.append(row)
        print(
            f"{cnf.name} {row['Result']} wall={float(row['wall_time']):.3f} "
            f"returncode={row['returncode']} external_timeout={row['external_timeout']}",
            flush=True,
        )

    fieldnames = ["file", "Result", "wall_time", "external_timeout", "returncode", "stdout_head", "stderr_head"]
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
