from __future__ import annotations

import argparse
import fcntl
import os
import subprocess
import time
from pathlib import Path

import pandas as pd

from build_residual_elite_replay_manifest import parse_expected_sample_seeds
from finalize_residual_elite_manifest import parse_bool_cell


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/sunshixin/anaconda3/envs/rlaf/bin/python"
PROCESS_SUBSTRINGS = (
    "run_march_sample_portfolio_multiseed.py",
    "solvers/march_weighted/march_nh",
)
GLOBAL_SUMMARY_FILENAMES = (
    "raw_samples_all.csv",
    "instance_seed_summary.csv",
    "instance_oracle_summary.csv",
    "size_seed_summary.csv",
    "size_oracle_summary.csv",
)


def lock_path_for_out_dir(out_dir: Path) -> Path:
    return out_dir / ".run_march_sample_portfolio_multiseed.lock"


def work_dir_lock_is_held(out_dir: Path) -> bool:
    lock_path = lock_path_for_out_dir(out_dir)
    if not lock_path.exists():
        return False
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False


def run_command(command: list[str], dry_run: bool = False) -> None:
    print(" ".join(command), flush=True)
    if dry_run:
        return
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def active_mining_processes() -> list[str]:
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


def artifact_fingerprint(instances_dir: Path, out_dir: Path) -> tuple[tuple[str, int, int], ...]:
    paths = list(instances_dir.glob("*_raw.csv")) + list(instances_dir.glob("*_summary.csv"))
    paths.extend(out_dir / name for name in GLOBAL_SUMMARY_FILENAMES)
    observed = []
    for path in sorted(paths):
        if not path.exists():
            observed.append((str(path), -1, -1))
            continue
        stat = path.stat()
        observed.append((str(path), int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(observed)


def wait_for_artifacts_settled(instances_dir: Path, out_dir: Path, settle_seconds: float) -> bool:
    if settle_seconds <= 0:
        return True
    before = artifact_fingerprint(instances_dir, out_dir)
    time.sleep(float(settle_seconds))
    after = artifact_fingerprint(instances_dir, out_dir)
    return before == after


def require_complete_progress(
    progress_csv: Path,
    expected_sample_seeds: tuple[int, ...],
    min_positive_instances: int,
    require_positive_floor: bool,
) -> str:
    if not progress_csv.exists():
        raise FileNotFoundError(progress_csv)
    progress = pd.read_csv(progress_csv)
    if len(progress) != 1:
        raise ValueError(f"Expected one progress row in {progress_csv}, got {len(progress)}")
    row = progress.iloc[0]

    observed_seed_set = parse_expected_sample_seeds(str(row.get("expected_sample_seeds", "")))
    expected_seed_set = tuple(sorted(set(expected_sample_seeds)))
    completed_seed_pairs = int(row.get("completed_seed_pairs", -1))
    raw_complete_seed_pairs = int(row.get("raw_complete_seed_pairs", -1))
    expected_seed_pairs = int(row.get("expected_seed_pairs", -1))
    positive_instances = int(row.get("positive_instances", 0))
    positive_floor_met = parse_bool_cell(row["positive_floor_met"], "positive_floor_met")
    complete_mining = parse_bool_cell(row["complete_mining"], "complete_mining")
    raw_artifacts_complete = parse_bool_cell(row["raw_artifacts_complete"], "raw_artifacts_complete")
    decision = str(row["decision"])

    checks = {
        "sample_seed_set_matches_expected": tuple(sorted(set(observed_seed_set))) == expected_seed_set,
        "completed_seed_pairs_match_expected": completed_seed_pairs == expected_seed_pairs,
        "raw_complete_seed_pairs_match_expected": raw_complete_seed_pairs == expected_seed_pairs,
        "complete_mining": complete_mining,
        "raw_artifacts_complete": raw_artifacts_complete,
        "decision_is_final": decision in {"ready_for_formal_multiseed_manifest", "complete_but_sparse"},
    }
    if require_positive_floor:
        checks.update(
            {
                "positive_floor_met": positive_floor_met,
                "positive_instances_meet_floor": positive_instances >= int(min_positive_instances),
                "decision_ready": decision == "ready_for_formal_multiseed_manifest",
            }
        )
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(
            "Residual multiseed mining is not ready for strict summarize-only: "
            f"failed={failed} progress={progress_csv}"
        )
    return decision


def progress_refresh_command(args: argparse.Namespace) -> list[str]:
    return [
        PYTHON,
        "summarize_residual_multiseed_mining.py",
        "--input",
        str(args.split_csv),
        "--instances-dir",
        str(args.instances_dir),
        "--expected-sample-seeds",
        str(args.sample_seeds),
        "--output-csv",
        str(args.progress_csv),
        "--remaining-csv",
        str(args.remaining_csv),
        "--positives-csv",
        str(args.positives_csv),
        "--doc",
        str(args.progress_doc),
        "--min-positive-instances",
        str(args.min_positive_instances),
    ]


def strict_summarize_command(args: argparse.Namespace) -> list[str]:
    return [
        PYTHON,
        "run_march_sample_portfolio_multiseed.py",
        "--scope",
        "expanded",
        "--input",
        str(args.portfolio_input),
        "--source-root",
        str(args.source_root),
        "--checkpoint",
        str(args.checkpoint),
        "--out-dir",
        str(args.out_dir),
        "--subset-root",
        str(args.subset_root),
        "--doc",
        str(args.portfolio_doc),
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
        "--summarize-only",
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strictly finalize residual multi-seed mining raw summaries.")
    parser.add_argument(
        "--split-csv",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv",
    )
    parser.add_argument(
        "--instances-dir",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2/instances",
    )
    parser.add_argument(
        "--progress-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--remaining-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_multiseed_mining_remaining_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--positives-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_multiseed_mining_positives_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--progress-doc",
        type=Path,
        default=ROOT / "docs/residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.md",
    )
    parser.add_argument("--min-positive-instances", type=int, default=16)
    parser.add_argument(
        "--portfolio-input",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv",
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
        default=ROOT / "runs/analysis/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--subset-root",
        type=Path,
        default=ROOT / "data/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--portfolio-doc",
        type=Path,
        default=ROOT / "docs/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2.md",
    )
    parser.add_argument("--sample-seeds", default="1730,1731,1732")
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--require-positive-floor",
        action="store_true",
        help="Refuse complete-but-sparse mining when finalizing for dev-launch readiness.",
    )
    parser.add_argument("--settle-seconds", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if work_dir_lock_is_held(args.out_dir):
        print(f"status=wait active_work_dir_lock lock={lock_path_for_out_dir(args.out_dir)}", flush=True)
        return
    active = active_mining_processes()
    if active:
        shown = "\n".join(active[:8])
        print(f"status=wait active_mining_processes\n{shown}", flush=True)
        return

    run_command(progress_refresh_command(args), dry_run=bool(args.dry_run))
    if args.dry_run:
        print("status=dry_run progress_refreshed_command_only", flush=True)
        return

    expected_sample_seeds = parse_expected_sample_seeds(args.sample_seeds)
    decision = require_complete_progress(
        progress_csv=args.progress_csv,
        expected_sample_seeds=expected_sample_seeds,
        min_positive_instances=int(args.min_positive_instances),
        require_positive_floor=bool(args.require_positive_floor),
    )

    if not wait_for_artifacts_settled(args.instances_dir, args.out_dir, float(args.settle_seconds)):
        print("status=wait artifacts_still_changing", flush=True)
        return

    run_command(strict_summarize_command(args), dry_run=False)
    print(f"finalized_multiseed_raw={args.out_dir / 'raw_samples_all.csv'} decision={decision}", flush=True)


if __name__ == "__main__":
    main()
