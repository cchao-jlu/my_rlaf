from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pandas as pd

from finalize_residual_elite_manifest import parse_bool_cell


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/sunshixin/anaconda3/envs/rlaf/bin/python"
PROCESS_SUBSTRINGS = (
    "run_march_sample_portfolio_multiseed.py",
    "solvers/march_weighted/march_nh",
    "train_residual_elite_replay.py",
    "train_rlaf.py --config-name config_train_rlaf_march_residual",
)
REQUIRED_TRAIN_AUDIT_CHECKS = {
    "manifest_exists",
    "split_csv_exists",
    "checkpoint_exists",
    "manifest_positive_instances_meet_floor",
    "manifest_split_matches_expected",
    "split_csv_matches_expected_split",
    "manifest_checkpoint_hash_matches",
    "manifest_raw_sources_cover_split_exactly",
    "manifest_raw_sources_have_complete_sample_grid",
    "manifest_rows_match_solved_raw_samples",
    "manifest_raw_sources_sample_seeds_match_expected",
    "manifest_raw_sources_num_samples_match_expected",
}


def require_audit_pass(audit_csv: Path) -> None:
    if not audit_csv.exists():
        raise FileNotFoundError(audit_csv)
    audit = pd.read_csv(audit_csv)
    required = {"check", "status"}
    missing_columns = sorted(required - set(audit.columns))
    if missing_columns:
        raise ValueError(f"Audit CSV is missing columns: {missing_columns}: {audit_csv}")
    observed_checks = set(audit["check"].astype(str))
    missing_checks = sorted(REQUIRED_TRAIN_AUDIT_CHECKS - observed_checks)
    if missing_checks:
        raise ValueError(f"Train manifest audit is missing required checks: {missing_checks}")
    failures = audit[audit["status"].astype(str).ne("pass")]
    if not failures.empty:
        raise ValueError(f"Train manifest audit failed: {failures.to_dict(orient='records')}")


def require_progress_ready(progress_csv: Path) -> None:
    if not progress_csv.exists():
        raise FileNotFoundError(progress_csv)
    progress = pd.read_csv(progress_csv)
    if len(progress) != 1:
        raise ValueError(f"Expected one progress row in {progress_csv}, got {len(progress)}")
    row = progress.iloc[0]
    checks = {
        "positive_floor_met": parse_bool_cell(row["positive_floor_met"], "positive_floor_met"),
        "complete_mining": parse_bool_cell(row["complete_mining"], "complete_mining"),
        "raw_artifacts_complete": parse_bool_cell(
            row.get("raw_artifacts_complete", False),
            "raw_artifacts_complete",
        ),
        "decision_ready": str(row["decision"]) == "ready_for_formal_elite_manifest",
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(
            "Train elite mining progress is not ready for residual-dev launch: "
            f"failed={failed} progress={progress_csv}"
        )


def active_march_processes() -> list[str]:
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


def require_no_active_march_processes() -> None:
    processes = active_march_processes()
    if processes:
        shown = "\n".join(processes[:8])
        raise RuntimeError(
            "Refusing to launch residual-dev mining while March/replay/training "
            f"processes are active:\n{shown}"
        )


def run_command(command: list[str], detached: bool) -> None:
    print(" ".join(command), flush=True)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    if detached:
        command = ["setsid", "-f", *command]
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    else:
        subprocess.run(command, cwd=ROOT, env=env, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded launcher for residual-dev elite mining.")
    parser.add_argument(
        "--train-manifest-audit",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument(
        "--train-progress-csv",
        type=Path,
        default=ROOT
        / "runs/analysis/benchmark_transition_band_residual_large/"
        / "residual_train_elite_mining_progress_coverage_diverse_best_iter2.csv",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--subset-root", type=Path, required=True)
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument("--sample-seeds", default="1729")
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--detached", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_progress_ready(args.train_progress_csv)
    require_audit_pass(args.train_manifest_audit)
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
    run_command(command, detached=bool(args.detached))


if __name__ == "__main__":
    main()
