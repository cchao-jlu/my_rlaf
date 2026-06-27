from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INSTANCE_ORACLE = (
    ROOT
    / "runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/instance_oracle_summary.csv"
)
DEFAULT_OUTPUT = ROOT / "docs/residual_portfolio_gate_decision.md"
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


def parse_bool_series(values: pd.Series, column: str) -> pd.Series:
    return values.map(lambda value: parse_bool_cell(value, column))


def validate_oracle_summary(oracle: pd.DataFrame, expected_total: int, allow_diagnostic_total: bool) -> pd.Series:
    required = {"family", "size", "file_key", "solved_any"}
    missing = sorted(required - set(oracle.columns))
    if missing:
        raise ValueError(f"Oracle CSV is missing columns: {missing}")
    key_duplicates = int(oracle.duplicated(["family", "size", "file_key"]).sum())
    if key_duplicates:
        raise ValueError(f"Oracle CSV contains duplicate instance keys: duplicates={key_duplicates}")
    total = int(len(oracle))
    if total != expected_total and not allow_diagnostic_total:
        raise ValueError(
            "Oracle CSV total does not match the pre-registered gate denominator: "
            f"observed={total} expected={expected_total}. "
            "Use --allow-diagnostic-total only for non-formal diagnostic summaries."
        )
    return parse_bool_series(oracle["solved_any"], "solved_any")


def decision_label(
    total: int,
    solved: int,
    expected_total: int,
    fail_max: int,
    pass_min: int,
) -> tuple[str, str]:
    if total == expected_total and solved <= fail_max:
        return (
            "fail",
            "Stop selector tuning for this checkpoint and switch to residual-targeted training.",
        )
    if total == expected_total and solved >= pass_min:
        return (
            "pass",
            "Proceed to larger residual pool, dev-only selector tuning, and held-out evaluation.",
        )
    if total == expected_total:
        return (
            "marginal",
            "Do not claim performance. Expand the pilot or improve training before selector work.",
        )
    return (
        "diagnostic",
        "This is not the pre-registered all-49 gate; use it only as diagnostic evidence.",
    )


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_training_config_audit(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise FileNotFoundError(path)
    audit = pd.read_csv(path)
    required = {"check", "status"}
    missing = sorted(required - set(audit.columns))
    if missing:
        raise ValueError(f"Training config audit CSV is missing columns: {missing}")
    observed_checks = set(audit["check"].astype(str))
    missing_checks = sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS - observed_checks)
    if missing_checks:
        raise ValueError(f"Training config audit CSV is missing required checks: {missing_checks}")
    failures = int(audit["status"].astype(str).ne("pass").sum())
    if failures:
        failed = audit[audit["status"].astype(str).ne("pass")].head(5).to_dict(orient="records")
        raise ValueError(f"Training config audit has failures: failures={failures} examples={failed}")
    return int(len(audit)), failures


def validate_oracle_checkpoint_provenance(oracle: pd.DataFrame, checkpoint_path: Path | None) -> tuple[str, str]:
    if checkpoint_path is None or "source_checkpoint_sha256" not in oracle.columns:
        return "not-recorded", "not-checked"
    expected_hash = file_sha256(checkpoint_path)
    observed_hashes = set(oracle["source_checkpoint_sha256"].dropna().astype(str))
    observed_hashes.discard("")
    if observed_hashes and observed_hashes != {expected_hash}:
        raise ValueError(
            "Oracle summary checkpoint hash does not match --checkpoint: "
            f"observed={sorted(observed_hashes)} expected={expected_hash}"
        )
    return ",".join(sorted(observed_hashes)) if observed_hashes else "not-recorded", "pass"


def write_gate_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Decide a residual portfolio oracle gate.")
    parser.add_argument("--instance-oracle", type=Path, default=DEFAULT_INSTANCE_ORACLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Checkpoint evaluated by the oracle diagnostic. Recorded with SHA256 when provided.",
    )
    parser.add_argument(
        "--training-config-audit",
        type=Path,
        default=None,
        help="Optional replay training-config audit CSV. When provided, it must exist and have no failures.",
    )
    parser.add_argument("--expected-total", type=int, default=49)
    parser.add_argument("--fail-max", type=int, default=2)
    parser.add_argument("--pass-min", type=int, default=5)
    parser.add_argument("--gate-name", default="all-49")
    parser.add_argument("--allow-diagnostic-total", action="store_true")
    parser.add_argument(
        "--record-json",
        type=Path,
        default=None,
        help="Optional structured gate decision record for final protocol audit.",
    )
    args = parser.parse_args()

    oracle_path = args.instance_oracle.resolve()
    if not oracle_path.exists():
        raise FileNotFoundError(oracle_path)
    checkpoint_path = args.checkpoint.resolve() if args.checkpoint else None
    if checkpoint_path is not None and not checkpoint_path.exists():
        raise FileNotFoundError(checkpoint_path)
    training_config_audit_path = args.training_config_audit.resolve() if args.training_config_audit else None
    training_config_audit_checks = 0
    training_config_audit_failures = 0
    if training_config_audit_path is not None:
        training_config_audit_checks, training_config_audit_failures = validate_training_config_audit(
            training_config_audit_path
        )
    oracle = pd.read_csv(oracle_path)
    oracle_checkpoint_hash, oracle_checkpoint_check = validate_oracle_checkpoint_provenance(
        oracle,
        checkpoint_path=checkpoint_path,
    )
    solved_any = validate_oracle_summary(
        oracle,
        expected_total=int(args.expected_total),
        allow_diagnostic_total=bool(args.allow_diagnostic_total),
    )

    total = int(len(oracle))
    solved = int(solved_any.sum())
    label, action = decision_label(
        total=total,
        solved=solved,
        expected_total=args.expected_total,
        fail_max=args.fail_max,
        pass_min=args.pass_min,
    )
    gate_record = {
        "kind": "residual_portfolio_gate_decision",
        "gate_name": str(args.gate_name),
        "source": display_path(oracle_path),
        "source_sha256": file_sha256(oracle_path),
        "checkpoint": display_path(checkpoint_path) if checkpoint_path else "not-recorded",
        "checkpoint_sha256": file_sha256(checkpoint_path) if checkpoint_path else "not-recorded",
        "oracle_checkpoint_sha256": oracle_checkpoint_hash,
        "oracle_checkpoint_provenance_check": oracle_checkpoint_check,
        "training_config_audit": display_path(training_config_audit_path) if training_config_audit_path else "not-provided",
        "training_config_audit_sha256": file_sha256(training_config_audit_path) if training_config_audit_path else "not-provided",
        "training_config_audit_checks": training_config_audit_checks if training_config_audit_path else "not-provided",
        "training_config_audit_failures": training_config_audit_failures if training_config_audit_path else "not-provided",
        "expected_total": int(args.expected_total),
        "total": total,
        "oracle_solved": solved,
        "fail_max": int(args.fail_max),
        "pass_min": int(args.pass_min),
        "allow_diagnostic_total": bool(args.allow_diagnostic_total),
        "decision": label,
        "action": action,
    }
    positives = oracle[solved_any].copy()
    by_size = (
        oracle.assign(solved_any=solved_any).groupby("size", sort=True)["solved_any"]
        .agg(instances="count", oracle_solved="sum")
        .reset_index()
    )

    lines = [
        "# Residual Portfolio Gate Decision",
        "",
        f"Scope: pre-registered oracle diagnostic `{args.gate_name}` for the",
        "current March-trained checkpoint on a March/CaDiCaL both-unknown",
        "residual pilot.",
        "",
        f"- source: `{display_path(oracle_path)}`",
        f"- source sha256: `{file_sha256(oracle_path)}`",
        f"- checkpoint: `{display_path(checkpoint_path) if checkpoint_path else 'not-recorded'}`",
        f"- checkpoint sha256: `{file_sha256(checkpoint_path) if checkpoint_path else 'not-recorded'}`",
        f"- oracle checkpoint sha256: `{oracle_checkpoint_hash}`",
        f"- oracle checkpoint provenance check: `{oracle_checkpoint_check}`",
        f"- training config audit: `{display_path(training_config_audit_path) if training_config_audit_path else 'not-provided'}`",
        f"- training config audit sha256: `{file_sha256(training_config_audit_path) if training_config_audit_path else 'not-provided'}`",
        f"- training config audit checks: `{training_config_audit_checks if training_config_audit_path else 'not-provided'}`",
        f"- training config audit failures: `{training_config_audit_failures if training_config_audit_path else 'not-provided'}`",
        f"- expected residual instances: `{args.expected_total}`",
        f"- total residual instances: `{total}`",
        f"- oracle solved: `{solved}`",
        f"- fail if oracle solved <= `{args.fail_max}`",
        f"- pass if oracle solved >= `{args.pass_min}`",
        f"- decision: `{label}`",
        f"- action: {action}",
        "",
        "## By Size",
        "",
        *markdown_table(by_size, ["size", "instances", "oracle_solved"]),
        "",
        "## Oracle Positives",
        "",
        *markdown_table(
            positives,
            [
                "family",
                "size",
                "file_key",
                "solved_samples",
                "best_time",
                "best_sample_seed",
                "best_sample_id",
            ],
        ),
        "",
        "## Protocol Consequence",
        "",
    ]
    if label == "fail":
        lines.extend(
            [
                "The current checkpoint is not a viable top-conference performance",
                "model under the residual portfolio protocol. The next work item is",
                "to generate a larger residual pool and train on residual-targeted",
                "objectives before returning to selector experiments.",
            ]
        )
    elif label == "pass":
        lines.extend(
            [
                "The checkpoint has enough sampled coverage to justify selector",
                "work, but the all-49 pilot remains diagnostic. The next work item",
                "is to lock a larger residual dev/held-out split and evaluate a",
                "fixed selected neural portfolio against same-budget non-neural",
                "rerun controls.",
            ]
        )
    else:
        lines.append("No paper-level performance claim is supported by this gate alone.")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.record_json is not None:
        write_gate_record(args.record_json.resolve(), gate_record)
    print(f"decision={label} total={total} oracle_solved={solved}")
    print(display_path(output))


if __name__ == "__main__":
    main()
