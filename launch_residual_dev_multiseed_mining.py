from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pandas as pd

from build_residual_elite_replay_manifest import parse_expected_sample_seeds
from finalize_residual_elite_manifest import parse_bool_cell


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/sunshixin/anaconda3/envs/rlaf/bin/python"
PROCESS_SUBSTRINGS = (
    "run_march_sample_portfolio_multiseed.py",
    "solvers/march_weighted/march_nh",
    "train_residual_contrastive_replay.py",
    "train_residual_elite_replay.py",
    "train_rlaf.py --config-name config_train_rlaf_march_residual",
)


def parse_seed_set(value: object) -> tuple[int, ...]:
    return parse_expected_sample_seeds(str(value))


def require_train_multiseed_ready(
    progress_csv: Path,
    expected_sample_seeds: tuple[int, ...],
    min_positive_instances: int,
) -> None:
    if not progress_csv.exists():
        raise FileNotFoundError(progress_csv)
    progress = pd.read_csv(progress_csv)
    if len(progress) != 1:
        raise ValueError(f"Expected one progress row in {progress_csv}, got {len(progress)}")

    row = progress.iloc[0]
    observed_seed_set = parse_seed_set(row.get("expected_sample_seeds", ""))
    expected_seed_set = tuple(sorted(set(expected_sample_seeds)))
    if tuple(sorted(set(observed_seed_set))) != expected_seed_set:
        raise ValueError(
            "Train multiseed progress seed set does not match dev-launch protocol: "
            f"observed={observed_seed_set} expected={expected_seed_set}"
        )

    expected_seed_pairs = int(row.get("expected_seed_pairs", -1))
    completed_seed_pairs = int(row.get("completed_seed_pairs", -2))
    raw_complete_seed_pairs = int(row.get("raw_complete_seed_pairs", -3))
    positive_instances = int(row.get("positive_instances", 0))
    checks = {
        "positive_floor_met": parse_bool_cell(row["positive_floor_met"], "positive_floor_met"),
        "complete_mining": parse_bool_cell(row["complete_mining"], "complete_mining"),
        "raw_artifacts_complete": parse_bool_cell(
            row.get("raw_artifacts_complete", False),
            "raw_artifacts_complete",
        ),
        "decision_ready": str(row["decision"]) == "ready_for_formal_multiseed_manifest",
        "completed_seed_pairs_match_expected": completed_seed_pairs == expected_seed_pairs,
        "raw_complete_seed_pairs_match_expected": raw_complete_seed_pairs == expected_seed_pairs,
        "positive_instances_meet_floor": positive_instances >= int(min_positive_instances),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(
            "Train multiseed mining progress is not ready for residual-dev launch: "
            f"failed={failed} progress={progress_csv}"
        )


def active_march_processes() -> list[str]:
    observed: dict[str, None] = {}
    for token in PROCESS_SUBSTRINGS:
        result = subprocess.run(
            ["pgrep", "-af", token],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or f"pgrep failed with code {result.returncode}")
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if "pgrep -af" in line or "codex-linux-sandbox" in line:
                continue
            if any(active_token in line for active_token in PROCESS_SUBSTRINGS):
                observed[line] = None
    return sorted(observed)


def require_no_active_march_processes() -> None:
    processes = active_march_processes()
    if processes:
        shown = "\n".join(processes[:8])
        raise RuntimeError(
            "Refusing to launch residual-dev multiseed mining while March/replay/"
            f"residual-training processes are active:\n{shown}"
        )


def run_command(command: list[str], detached: bool, dry_run: bool) -> None:
    print(" ".join(command), flush=True)
    if dry_run:
        return
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    if detached:
        command = ["setsid", "-f", *command]
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded launcher for residual-dev multiseed mining.")
    parser.add_argument(
        "--train-progress-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument("--expected-train-sample-seeds", default="1730,1731,1732")
    parser.add_argument("--min-train-positive-instances", type=int, default=16)
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv",
    )
    parser.add_argument("--source-root", type=Path, default=ROOT / "data/benchmark_transition_band_residual_large")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=ROOT / "runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_march_residual_dev_multiseed_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--subset-root",
        type=Path,
        default=ROOT / "data/benchmark_march_residual_dev_multiseed_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--doc",
        type=Path,
        default=ROOT / "docs/benchmark_march_residual_dev_multiseed_mining_coverage_diverse_best_iter2.md",
    )
    parser.add_argument("--sample-seeds", default="1730,1731,1732")
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--detached", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_train_sample_seeds = parse_expected_sample_seeds(args.expected_train_sample_seeds)
    require_train_multiseed_ready(
        progress_csv=args.train_progress_csv,
        expected_sample_seeds=expected_train_sample_seeds,
        min_positive_instances=int(args.min_train_positive_instances),
    )
    require_no_active_march_processes()
    command = [
        PYTHON,
        "run_march_sample_portfolio_multiseed.py",
        "--scope",
        "expanded",
        "--input",
        str(args.input),
        "--source-root",
        str(args.source_root),
        "--checkpoint",
        str(args.checkpoint),
        "--out-dir",
        str(args.out_dir),
        "--subset-root",
        str(args.subset_root),
        "--doc",
        str(args.doc),
        "--sample-seeds",
        str(args.sample_seeds),
        "--num-samples",
        str(args.num_samples),
        "--artifact-mode",
        "instance",
        "--full-cpu-lim",
        str(args.full_cpu_lim),
        "--workers",
        str(args.workers),
        "--device",
        str(args.device),
    ]
    run_command(command, detached=bool(args.detached), dry_run=bool(args.dry_run))


if __name__ == "__main__":
    main()
