from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from src.datasets.generate_col import Random3ColGenerator
from src.datasets.generate_ksat import Random3SATGenerator


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/benchmark_candidate_smoke"
DATA_ROOT = ROOT / "data/benchmark_candidates"

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


def parse_candidate(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("candidate must be FAMILY:SIZE, e.g. 3sat:450")
    family, size_text = value.split(":", 1)
    family = family.strip().lower()
    if family not in {"3sat", "coloring"}:
        raise argparse.ArgumentTypeError(f"unsupported family: {family}")
    try:
        size = int(size_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid size: {size_text}") from exc
    return family, size


def generate_candidate(family: str, size: int, instances: int, seed: int) -> Path:
    data_dir = DATA_ROOT / family / str(size)
    pattern = "*.cnf"
    existing = sorted(data_dir.glob(pattern))
    if len(existing) >= instances:
        return data_dir

    if family == "3sat":
        generator = Random3SATGenerator(
            data_dir=str(data_dir),
            target_num=instances,
            num_var=(size, size),
            seed=seed,
        )
    elif family == "coloring":
        generator = Random3ColGenerator(
            data_dir=str(data_dir),
            target_num=instances,
            num_nodes=(size, size),
            seed=seed,
        )
    else:
        raise ValueError(f"unsupported family: {family}")
    generator.generate_all()
    return data_dir


def run_solver(
    solver_name: str,
    family: str,
    size: int,
    data_dir: Path,
    instances: int,
    limit: float,
    timeout: float,
    workers: int,
    repeat: int,
) -> None:
    solver = SOLVERS[solver_name]
    solver_path = solver["path"]
    if not solver_path.exists():
        raise FileNotFoundError(solver_path)
    output = OUT_DIR / f"{solver_name}_{family}_{size}_repeat{repeat}.csv"
    command = [
        "python",
        str(ROOT / "run_external_solver_baseline.py"),
        "--solver",
        str(solver_path),
        "--solver-name",
        solver_name,
        "--input",
        str(data_dir / "*.cnf"),
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
            "Generate small candidate benchmark smoke sets and evaluate existing "
            "strong solver artifacts. This does not train or tune neural models."
        )
    )
    parser.add_argument(
        "--candidate",
        action="append",
        type=parse_candidate,
        required=True,
        help="Candidate benchmark FAMILY:SIZE. Repeatable, e.g. --candidate 3sat:450.",
    )
    parser.add_argument("--solver", action="append", choices=sorted(SOLVERS), required=True)
    parser.add_argument("--instances", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--generate-only", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for family, size in args.candidate:
        data_dir = generate_candidate(family, size, args.instances, args.seed)
        print(f"candidate={family}:{size} data_dir={data_dir} instances={args.instances}", flush=True)
        if args.generate_only:
            continue
        for solver_name in args.solver:
            run_solver(
                solver_name=solver_name,
                family=family,
                size=size,
                data_dir=data_dir,
                instances=args.instances,
                limit=args.limit,
                timeout=args.timeout,
                workers=args.workers,
                repeat=args.repeat,
            )


if __name__ == "__main__":
    main()
