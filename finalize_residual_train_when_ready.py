from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

import pandas as pd

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


def active_mining_processes() -> list[str]:
    result = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ps failed with code {result.returncode}")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [
        line
        for line in lines
        if any(token in line for token in PROCESS_SUBSTRINGS)
    ]


def progress_ready(progress_csv: Path) -> bool:
    if not progress_csv.exists():
        return False
    progress = pd.read_csv(progress_csv)
    if len(progress) != 1:
        return False
    row = progress.iloc[0]
    return (
        parse_bool_cell(row["positive_floor_met"], "positive_floor_met")
        and parse_bool_cell(row["complete_mining"], "complete_mining")
        and parse_bool_cell(row.get("raw_artifacts_complete", False), "raw_artifacts_complete")
        and str(row["decision"]) == "ready_for_formal_elite_manifest"
    )


def progress_wait_reason(progress_csv: Path) -> str:
    if not progress_csv.exists():
        return f"missing_progress_csv={progress_csv}"
    progress = pd.read_csv(progress_csv)
    if len(progress) != 1:
        return f"invalid_progress_rows={len(progress)} progress_csv={progress_csv}"
    row = progress.iloc[0]
    fields = [
        f"decision={row.get('decision', '<missing>')}",
        f"completed={row.get('completed_instances', '<missing>')}",
        f"expected={row.get('expected_instances', '<missing>')}",
        f"raw_artifacts_complete={row.get('raw_artifacts_complete', '<missing>')}",
    ]
    return " ".join(fields)


def run_command(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def progress_refresh_command(args: argparse.Namespace) -> list[str]:
    return [
        PYTHON,
        "summarize_residual_elite_mining.py",
        "--input",
        str(args.split_csv),
        "--instances-dir",
        str(args.instances_dir),
        "--output-csv",
        str(args.progress_csv),
        "--remaining-csv",
        str(args.remaining_csv),
        "--doc",
        str(args.progress_doc),
        "--min-positive-instances",
        str(args.min_positive_instances),
    ]


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


def finalizer_command(args: argparse.Namespace) -> list[str]:
    return [
        PYTHON,
        "finalize_residual_elite_manifest.py",
        "--split-csv",
        str(args.split_csv),
        "--instances-dir",
        str(args.instances_dir),
        "--min-positive-instances",
        str(args.min_positive_instances),
        "--progress-csv",
        str(args.progress_csv),
        "--remaining-csv",
        str(args.remaining_csv),
        "--progress-doc",
        str(args.progress_doc),
        "--portfolio-input",
        str(args.portfolio_input),
        "--source-root",
        str(args.source_root),
        "--checkpoint",
        str(args.checkpoint),
        "--out-dir",
        str(args.out_dir),
        "--subset-root",
        str(args.subset_root),
        "--portfolio-doc",
        str(args.portfolio_doc),
        "--sample-seeds",
        str(args.sample_seeds),
        "--num-samples",
        str(args.num_samples),
        "--full-cpu-lim",
        str(args.full_cpu_lim),
        "--workers",
        str(args.workers),
        "--device",
        str(args.device),
        "--manifest-csv",
        str(args.manifest_csv),
        "--manifest-doc",
        str(args.manifest_doc),
        "--audit-csv",
        str(args.audit_csv),
        "--audit-doc",
        str(args.audit_doc),
        "--expected-split",
        str(args.expected_split),
        "--max-per-instance",
        str(args.max_per_instance),
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize residual-train elite manifest only when ready.")
    parser.add_argument(
        "--split-csv",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv",
    )
    parser.add_argument(
        "--instances-dir",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/instances",
    )
    parser.add_argument("--min-positive-instances", type=int, default=8)
    parser.add_argument(
        "--progress-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_mining_progress_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--remaining-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_mining_remaining_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--progress-doc",
        type=Path,
        default=ROOT / "docs/residual_train_elite_mining_progress_coverage_diverse_best_iter2.md",
    )
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
        default=ROOT / "runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--subset-root",
        type=Path,
        default=ROOT / "data/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2",
    )
    parser.add_argument(
        "--portfolio-doc",
        type=Path,
        default=ROOT / "docs/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2.md",
    )
    parser.add_argument("--sample-seeds", default="1729")
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--manifest-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--manifest-doc",
        type=Path,
        default=ROOT / "docs/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.md",
    )
    parser.add_argument(
        "--audit-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--audit-doc",
        type=Path,
        default=ROOT / "docs/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.md",
    )
    parser.add_argument("--expected-split", default="residual_train")
    parser.add_argument("--max-per-instance", type=int, default=4)
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=10.0,
        help=(
            "After refreshed progress is ready, require mining artifacts to stay "
            "unchanged for this many seconds before invoking the finalizer."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    active = active_mining_processes()
    if active:
        print(f"status=wait active_processes={len(active)}")
        for line in active[:8]:
            print(line)
        return
    run_command(progress_refresh_command(args))
    if not progress_ready(args.progress_csv):
        print("status=wait progress_not_ready")
        print(progress_wait_reason(args.progress_csv))
        return
    if not wait_for_artifacts_settled(args.instances_dir, args.out_dir, args.settle_seconds):
        print("status=wait artifacts_still_changing")
        return
    command = finalizer_command(args)
    if args.dry_run:
        print("status=ready_to_try_finalizer")
        print(" ".join(command))
        return
    run_command(command)


if __name__ == "__main__":
    main()
