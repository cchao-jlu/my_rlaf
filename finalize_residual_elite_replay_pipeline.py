from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/sunshixin/anaconda3/envs/rlaf/bin/python"
REQUIRED_MANIFEST_AUDIT_CHECKS = {
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
REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS = {
    "training_config_exists",
    "training_config_has_elite_replay",
    "training_config_checkpoint_hash_matches",
    "training_config_train_manifest_exists",
    "training_config_train_manifest_path_matches",
    "training_config_train_manifest_hash_matches",
    "training_config_train_positive_instances_match",
    "training_config_min_train_positive_floor_matches",
    "training_config_expected_train_split_matches",
    "training_config_expected_train_sample_seeds_match",
    "training_config_expected_train_num_samples_match",
    "training_config_dev_manifest_exists",
    "training_config_dev_manifest_path_matches",
    "training_config_dev_manifest_hash_matches",
    "training_config_dev_positive_instances_match",
    "training_config_min_dev_positive_floor_matches",
    "training_config_expected_dev_split_matches",
    "training_config_expected_dev_sample_seeds_match",
    "training_config_expected_dev_num_samples_match",
    "training_config_disallows_partial_manifest_training",
    "training_config_uses_full_manifests",
}


def run_command(command: list[str]) -> None:
    print(" ".join(command), flush=True)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def require_audit_pass(audit_csv: Path, required_checks: set[str] | None = None) -> None:
    if not audit_csv.exists():
        raise FileNotFoundError(audit_csv)
    audit = pd.read_csv(audit_csv)
    required_columns = {"check", "status"}
    missing_columns = sorted(required_columns - set(audit.columns))
    if missing_columns:
        raise ValueError(f"Audit CSV is missing columns: {missing_columns}: {audit_csv}")
    if required_checks:
        observed_checks = set(audit["check"].astype(str))
        missing_checks = sorted(required_checks - observed_checks)
        if missing_checks:
            raise ValueError(f"Audit CSV is missing required checks: {missing_checks}")
    failures = audit[audit["status"].astype(str).ne("pass")]
    if not failures.empty:
        raise ValueError(f"Audit failed: {failures.to_dict(orient='records')}")


def require_artifact(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize formal residual elite replay training/audit or gate decision."
    )
    parser.add_argument(
        "--stage",
        choices=["train_audit", "gate"],
        default="train_audit",
        help=(
            "train_audit trains replay and audits config; gate consumes a separately "
            "generated all-49 oracle summary for model-dir/best.pt."
        ),
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--dev-manifest", type=Path, required=True)
    parser.add_argument("--train-split-csv", type=Path, required=True)
    parser.add_argument("--train-manifest-audit", type=Path, required=True)
    parser.add_argument("--dev-manifest-audit", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--kl-penalty", type=float, default=0.05)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--min-train-positive-instances", type=int, default=8)
    parser.add_argument("--min-dev-positive-instances", type=int, default=4)
    parser.add_argument("--expected-train-split", default="residual_train")
    parser.add_argument("--expected-dev-split", default="residual_dev")
    parser.add_argument("--expected-train-sample-seeds", default="1729")
    parser.add_argument("--expected-dev-sample-seeds", default="1729")
    parser.add_argument("--expected-train-num-samples", type=int, default=16)
    parser.add_argument("--expected-dev-num-samples", type=int, default=16)
    parser.add_argument("--training-config-audit-csv", type=Path, required=True)
    parser.add_argument("--training-config-audit-doc", type=Path, required=True)
    parser.add_argument("--oracle-summary", type=Path, default=None)
    parser.add_argument("--gate-output", type=Path, default=None)
    parser.add_argument("--gate-record-json", type=Path, default=None)
    parser.add_argument("--gate-name", default="")
    parser.add_argument("--expected-total", type=int, default=49)
    parser.add_argument("--fail-max", type=int, default=2)
    parser.add_argument("--pass-min", type=int, default=5)
    return parser.parse_args()


def require_gate_args(args: argparse.Namespace) -> tuple[Path, Path, str]:
    missing = []
    if args.oracle_summary is None:
        missing.append("--oracle-summary")
    if args.gate_output is None:
        missing.append("--gate-output")
    if not str(args.gate_name).strip():
        missing.append("--gate-name")
    if missing:
        raise ValueError(
            "Gate stage requires a separately generated all-49 oracle artifact: "
            f"missing={missing}"
        )
    return args.oracle_summary, args.gate_output, str(args.gate_name)


def require_common_artifacts(args: argparse.Namespace) -> None:
    require_artifact(args.checkpoint, "source checkpoint")
    require_artifact(args.train_manifest, "train manifest")
    require_artifact(args.dev_manifest, "dev manifest")
    require_artifact(args.train_split_csv, "train split CSV")
    require_audit_pass(args.train_manifest_audit, REQUIRED_MANIFEST_AUDIT_CHECKS)
    require_audit_pass(args.dev_manifest_audit, REQUIRED_MANIFEST_AUDIT_CHECKS)


def run_train_audit(args: argparse.Namespace) -> Path:
    run_command(
        [
            PYTHON,
            "train_residual_elite_replay.py",
            "--checkpoint",
            str(args.checkpoint),
            "--train-manifest",
            str(args.train_manifest),
            "--dev-manifest",
            str(args.dev_manifest),
            "--model-dir",
            str(args.model_dir),
            "--epochs",
            str(args.epochs),
            "--batch-size",
            str(args.batch_size),
            "--lr",
            str(args.lr),
            "--kl-penalty",
            str(args.kl_penalty),
            "--device",
            str(args.device),
            "--min-train-positive-instances",
            str(args.min_train_positive_instances),
            "--min-dev-positive-instances",
            str(args.min_dev_positive_instances),
            "--expected-train-split",
            str(args.expected_train_split),
            "--expected-dev-split",
            str(args.expected_dev_split),
            "--expected-train-sample-seeds",
            str(args.expected_train_sample_seeds),
            "--expected-dev-sample-seeds",
            str(args.expected_dev_sample_seeds),
            "--expected-train-num-samples",
            str(args.expected_train_num_samples),
            "--expected-dev-num-samples",
            str(args.expected_dev_num_samples),
        ]
    )

    best_checkpoint = args.model_dir / "best.pt"
    require_artifact(best_checkpoint, "replay best checkpoint")

    run_command(
        [
            PYTHON,
            "audit_residual_elite_replay_manifest.py",
            "--manifest",
            str(args.train_manifest),
            "--split-csv",
            str(args.train_split_csv),
            "--checkpoint",
            str(args.checkpoint),
            "--expected-split",
            str(args.expected_train_split),
            "--min-positive-instances",
            str(args.min_train_positive_instances),
            "--max-per-instance",
            "4",
            "--training-config",
            str(args.model_dir / "config.yaml"),
            "--train-manifest",
            str(args.train_manifest),
            "--dev-manifest",
            str(args.dev_manifest),
            "--min-train-positive-instances",
            str(args.min_train_positive_instances),
            "--min-dev-positive-instances",
            str(args.min_dev_positive_instances),
            "--expected-train-split",
            str(args.expected_train_split),
            "--expected-dev-split",
            str(args.expected_dev_split),
            "--expected-train-sample-seeds",
            str(args.expected_train_sample_seeds),
            "--expected-dev-sample-seeds",
            str(args.expected_dev_sample_seeds),
            "--expected-train-num-samples",
            str(args.expected_train_num_samples),
            "--expected-dev-num-samples",
            str(args.expected_dev_num_samples),
            "--output-csv",
            str(args.training_config_audit_csv),
            "--doc",
            str(args.training_config_audit_doc),
        ]
    )
    require_audit_pass(args.training_config_audit_csv, REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)
    print(f"finalized_replay_checkpoint={best_checkpoint}", flush=True)
    return best_checkpoint


def run_gate(args: argparse.Namespace) -> None:
    oracle_summary, gate_output, gate_name = require_gate_args(args)
    best_checkpoint = args.model_dir / "best.pt"
    require_artifact(best_checkpoint, "replay best checkpoint")
    require_audit_pass(args.training_config_audit_csv, REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)
    require_artifact(args.oracle_summary, "all-49 oracle summary")
    command = [
        PYTHON,
        "decide_residual_portfolio_gate.py",
        "--instance-oracle",
        str(args.oracle_summary),
        "--output",
        str(args.gate_output),
        "--gate-name",
        str(args.gate_name),
        "--checkpoint",
        str(best_checkpoint),
        "--training-config-audit",
        str(args.training_config_audit_csv),
        "--expected-total",
        str(args.expected_total),
        "--fail-max",
        str(args.fail_max),
        "--pass-min",
        str(args.pass_min),
    ]
    if args.gate_record_json is not None:
        command.extend(["--record-json", str(args.gate_record_json)])
    run_command(command)
    print(f"finalized_replay_gate={gate_output}", flush=True)


def main() -> None:
    args = parse_args()
    require_common_artifacts(args)
    if args.stage == "train_audit":
        run_train_audit(args)
    elif args.stage == "gate":
        run_gate(args)
    else:
        raise ValueError(f"Unsupported stage: {args.stage}")


if __name__ == "__main__":
    main()
