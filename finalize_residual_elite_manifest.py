from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/sunshixin/anaconda3/envs/rlaf/bin/python"


def run_command(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def parse_bool_cell(value, column: str) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        raise ValueError(f"Missing boolean value for {column}")
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value for {column}: {value!r}")


def require_ready(progress_csv: Path) -> None:
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
            "Residual elite mining is not ready for formal manifest: "
            f"failed={failed} progress={progress_csv}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize a formal residual elite replay manifest.")
    parser.add_argument("--split-csv", type=Path, required=True)
    parser.add_argument("--instances-dir", type=Path, required=True)
    parser.add_argument("--min-positive-instances", type=int, required=True)
    parser.add_argument("--progress-csv", type=Path, required=True)
    parser.add_argument("--remaining-csv", type=Path, required=True)
    parser.add_argument("--progress-doc", type=Path, required=True)
    parser.add_argument("--portfolio-input", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--subset-root", type=Path, required=True)
    parser.add_argument("--portfolio-doc", type=Path, required=True)
    parser.add_argument("--sample-seeds", default="1729")
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--manifest-csv", type=Path, required=True)
    parser.add_argument("--manifest-doc", type=Path, required=True)
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--audit-doc", type=Path, required=True)
    parser.add_argument("--expected-split", required=True)
    parser.add_argument("--max-per-instance", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_command(
        [
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
    )
    require_ready(args.progress_csv)

    run_command(
        [
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
    )

    run_command(
        [
            PYTHON,
            "build_residual_elite_replay_manifest.py",
            "--raw-samples",
            str(args.out_dir / "raw_samples_all.csv"),
            "--split-csv",
            str(args.split_csv),
            "--checkpoint",
            str(args.checkpoint),
            "--output-csv",
            str(args.manifest_csv),
            "--doc",
            str(args.manifest_doc),
            "--max-per-instance",
            str(args.max_per_instance),
            "--min-positive-instances",
            str(args.min_positive_instances),
            "--require-raw-complete",
            "--expected-sample-seeds",
            str(args.sample_seeds),
            "--expected-num-samples",
            str(args.num_samples),
        ]
    )

    run_command(
        [
            PYTHON,
            "audit_residual_elite_replay_manifest.py",
            "--manifest",
            str(args.manifest_csv),
            "--split-csv",
            str(args.split_csv),
            "--checkpoint",
            str(args.checkpoint),
            "--expected-split",
            str(args.expected_split),
            "--min-positive-instances",
            str(args.min_positive_instances),
            "--max-per-instance",
            str(args.max_per_instance),
            "--expected-sample-seeds",
            str(args.sample_seeds),
            "--expected-num-samples",
            str(args.num_samples),
            "--output-csv",
            str(args.audit_csv),
            "--doc",
            str(args.audit_doc),
        ]
    )

    audit = pd.read_csv(args.audit_csv)
    failures = audit[audit["status"].astype(str).ne("pass")]
    if not failures.empty:
        raise ValueError(f"Residual elite manifest audit failed: {failures.to_dict(orient='records')}")
    print(f"finalized_manifest={args.manifest_csv}", flush=True)


if __name__ == "__main__":
    main()
