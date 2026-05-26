from __future__ import annotations

import argparse
import csv
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from src.data.io_utils import load_dimacs_cnf
from src.solving.solver import SOLVER_BIN_PATHS, cnf_to_dimacs, stdout_to_results_dict


DEFAULT_INPUT = "data/test/3sat/400/*.cnf"
DEFAULT_OUTPUT = Path("runs/glucose/solver_stats_full400_cpu60.csv")
FIELDNAMES = [
    "file",
    "restarts",
    "conflicts",
    "decisions",
    "propagations",
    "CPU time",
    "Result",
    "time",
    "wall_time",
    "external_timeout",
    "returncode",
]


def existing_files(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    with output_path.open(newline="") as handle:
        return {row["file"] for row in csv.DictReader(handle) if row.get("file")}


def normalize_row(row: dict[str, object], file_path: str) -> dict[str, object]:
    normalized = {key: row.get(key, "") for key in FIELDNAMES}
    normalized["file"] = file_path
    if normalized["Result"] == "":
        normalized["Result"] = "INDETERMINATE"
    if normalized["CPU time"] == "":
        normalized["CPU time"] = 60.0
    normalized["time"] = normalized["CPU time"]
    return normalized


def solve_one(file_path: str, cpu_lim: float, timeout: float) -> dict[str, object]:
    cnf = load_dimacs_cnf(file_path)
    dimacs = cnf_to_dimacs(cnf, var_params=None)
    call = [
        SOLVER_BIN_PATHS["glucose"],
        "-rnd-seed=1",
        f"-cpu-lim={cpu_lim:g}",
        "-rnd-freq=0.0",
        "-K=0.1",
    ]
    start = time.monotonic()
    try:
        with tempfile.TemporaryFile(mode="w+") as tmp_file:
            tmp_file.write(dimacs)
            tmp_file.seek(0)
            result = subprocess.run(
                call,
                capture_output=True,
                text=True,
                stdin=tmp_file,
                timeout=timeout,
            )
        wall_time = time.monotonic() - start
        stats = stdout_to_results_dict(result.stdout)
        stats["external_timeout"] = False
        stats["returncode"] = result.returncode
    except subprocess.TimeoutExpired as exc:
        wall_time = time.monotonic() - start
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        stats = stdout_to_results_dict(stdout)
        stats["Result"] = "INDETERMINATE"
        stats["CPU time"] = cpu_lim
        stats["external_timeout"] = True
        stats["returncode"] = "timeout"

    stats["wall_time"] = wall_time
    return normalize_row(stats, file_path)


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
        description="Run unguided Glucose default on full400 with an external 60s cap."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cpu-lim", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    files = sorted(str(path) for path in Path().glob(args.input))
    done = existing_files(args.output)
    pending = [path for path in files if path not in done]
    print(f"found={len(files)} done={len(done)} pending={len(pending)} output={args.output}")
    if not pending:
        return

    completed = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(solve_one, path, args.cpu_lim, args.timeout): path
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
