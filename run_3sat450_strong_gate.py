from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from src.datasets.generate_ksat import Random3SATGenerator


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data/benchmark_3sat450_gate/3sat/450"
OUT_DIR = ROOT / "runs/analysis/benchmark_3sat450_gate/raw"

SOLVERS = {
    "march": {
        "path": ROOT / "solvers/march/march_nh",
        "cmd_template": "{solver} {file}",
    },
    "cadical": {
        "path": ROOT / "solvers/cadical/cadical",
        "cmd_template": "{solver} -q -t {limit} {file}",
    },
}


def ensure_data(instances: int, seed: int) -> None:
    existing = sorted(DATA_DIR.glob("*.cnf"))
    if len(existing) >= instances:
        return
    generator = Random3SATGenerator(
        data_dir=str(DATA_DIR),
        target_num=instances,
        num_var=(450, 450),
        seed=seed,
    )
    generator.generate_all()


def run_solver(solver_name: str, instances: int, repeat: int, limit: float, timeout: float, workers: int) -> None:
    solver = SOLVERS[solver_name]
    solver_path = solver["path"]
    if not solver_path.exists():
        raise FileNotFoundError(solver_path)
    output = OUT_DIR / f"{solver_name}_repeat{repeat}.csv"
    command = [
        "python",
        str(ROOT / "run_external_solver_baseline.py"),
        "--solver",
        str(solver_path),
        "--solver-name",
        solver_name,
        "--input",
        str(DATA_DIR / "*.cnf"),
        "--output",
        str(output),
        "--limit",
        f"{limit:g}",
        "--timeout",
        f"{timeout:g}",
        "--workers",
        str(workers),
        "--repeat",
        str(repeat),
        "--n",
        str(instances),
        "--cmd-template",
        solver["cmd_template"],
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a 3SAT-450 strong-solver gate. This generates a fixed random "
            "3SAT-450 candidate set and evaluates existing March/CaDiCaL artifacts."
        )
    )
    parser.add_argument("--instances", type=int, default=24)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--solver", action="append", choices=sorted(SOLVERS), default=None)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()

    ensure_data(args.instances, args.seed)
    print(f"data_dir={DATA_DIR} instances={args.instances} seed={args.seed}", flush=True)
    if args.generate_only:
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    solvers = args.solver or ["march", "cadical"]
    for solver_name in solvers:
        run_solver(
            solver_name=solver_name,
            instances=args.instances,
            repeat=args.repeat,
            limit=args.limit,
            timeout=args.timeout,
            workers=args.workers,
        )


if __name__ == "__main__":
    main()
