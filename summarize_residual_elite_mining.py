from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_residual_elite_replay_manifest import raw_sample_grid_issues


KEY_COLUMNS = ["family", "size", "file_key"]


def instance_key_set(frame: pd.DataFrame) -> set[tuple[str, int, str]]:
    if frame.empty:
        return set()
    return set(
        zip(
            frame["family"].astype(str),
            pd.to_numeric(frame["size"], errors="raise").astype(int),
            frame["file_key"].astype(str),
        )
    )


def filter_to_instance_keys(frame: pd.DataFrame, keys: set[tuple[str, int, str]]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    row_keys = list(
        zip(
            frame["family"].astype(str),
            pd.to_numeric(frame["size"], errors="raise").astype(int),
            frame["file_key"].astype(str),
        )
    )
    return frame.loc[[key in keys for key in row_keys]].copy()


def load_expected(input_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(input_csv)
    required = set(KEY_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {sorted(missing)}")
    return frame


def instance_raw_path(summary_path: Path) -> Path:
    if not summary_path.name.endswith("_summary.csv"):
        raise ValueError(f"Unexpected summary filename: {summary_path}")
    return summary_path.with_name(summary_path.name.replace("_summary.csv", "_raw.csv"))


def check_raw_grid(summary_row: pd.Series, raw_path: Path) -> tuple[bool, str]:
    if not raw_path.exists():
        return False, f"missing_raw={raw_path}"
    try:
        raw = pd.read_csv(raw_path)
    except Exception as exc:
        return False, f"raw_read_error={exc}"

    required = {"family", "size", "file_key", "sample_seed"}
    missing = sorted(required - set(raw.columns))
    if missing:
        return False, f"raw_missing_key_columns={missing}"
    expected_key = (
        str(summary_row["family"]),
        int(summary_row["size"]),
        str(summary_row["file_key"]),
        int(summary_row["sample_seed"]),
    )
    raw_keys = {
        (str(row.family), int(row.size), str(row.file_key), int(row.sample_seed))
        for row in raw[["family", "size", "file_key", "sample_seed"]].drop_duplicates().itertuples(index=False)
    }
    if raw_keys != {expected_key}:
        return False, f"raw_key_mismatch expected={expected_key} observed={sorted(raw_keys)}"

    issues = raw_sample_grid_issues(raw)
    if issues:
        return False, "; ".join(issues[:3])
    expected_samples = int(summary_row["samples"]) if "samples" in summary_row and pd.notna(summary_row["samples"]) else None
    if expected_samples is not None and len(raw) != expected_samples:
        return False, f"raw_row_count_mismatch expected={expected_samples} observed={len(raw)}"
    return True, ""


def load_completed(instances_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(instances_dir.glob("*_summary.csv")):
        frame = pd.read_csv(path)
        frame["summary_path"] = str(path)
        raw_path = instance_raw_path(path)
        raw_checks = [check_raw_grid(row, raw_path) for _, row in frame.iterrows()]
        frame["raw_path"] = str(raw_path)
        frame["raw_grid_complete"] = [ok for ok, _ in raw_checks]
        frame["raw_grid_issue"] = [issue for _, issue in raw_checks]
        frames.append(frame)
    if not frames:
        return pd.DataFrame(
            columns=[
                "family",
                "size",
                "file_key",
                "sample_seed",
                "solved_samples",
                "solved_any",
                "best_time",
                "best_sample_id",
                "summary_path",
                "raw_path",
                "raw_grid_complete",
                "raw_grid_issue",
            ]
        )
    completed = pd.concat(frames, ignore_index=True)
    completed["solved_samples"] = pd.to_numeric(completed["solved_samples"], errors="coerce").fillna(0).astype(int)
    completed["solved_any"] = completed["solved_samples"] > 0
    return completed


def summarize(expected: pd.DataFrame, completed: pd.DataFrame, min_positive_instances: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "raw_grid_complete" not in completed.columns:
        raise ValueError(
            "Completed mining frame is missing raw_grid_complete. "
            "Use load_completed() so progress readiness is based on audited raw artifacts."
        )
    expected_keys = expected[KEY_COLUMNS].drop_duplicates().copy()
    expected_key_set = instance_key_set(expected_keys)
    summary_completed_keys = (
        completed[KEY_COLUMNS].drop_duplicates().copy()
        if not completed.empty
        else pd.DataFrame(columns=KEY_COLUMNS)
    )
    summary_key_set = instance_key_set(summary_completed_keys)
    completed_usable = completed[completed["raw_grid_complete"].eq(True)].copy()
    completed_keys = (
        completed_usable[KEY_COLUMNS].drop_duplicates().copy()
        if not completed_usable.empty
        else pd.DataFrame(columns=KEY_COLUMNS)
    )
    raw_complete_key_set = instance_key_set(completed_keys)
    summary_expected_key_set = summary_key_set & expected_key_set
    raw_complete_expected_key_set = raw_complete_key_set & expected_key_set
    unexpected_summary_key_set = summary_key_set - expected_key_set
    unexpected_raw_complete_key_set = raw_complete_key_set - expected_key_set

    remaining_key_set = expected_key_set - raw_complete_expected_key_set
    remaining = filter_to_instance_keys(expected_keys, remaining_key_set)

    completed_usable_expected = filter_to_instance_keys(completed_usable, raw_complete_expected_key_set)
    positives = completed_usable_expected[completed_usable_expected["solved_any"]].copy()
    positive_instances = positives[KEY_COLUMNS].drop_duplicates().shape[0] if not positives.empty else 0
    completed_instances = len(raw_complete_expected_key_set)
    summary_completed_instances = len(summary_expected_key_set)
    expected_instances = len(expected_key_set)
    raw_incomplete_instances = len(summary_expected_key_set - raw_complete_expected_key_set)
    unexpected_artifact_instances = len(unexpected_summary_key_set)
    unexpected_raw_complete_instances = len(unexpected_raw_complete_key_set)
    solved_samples = int(completed_usable_expected["solved_samples"].sum()) if not completed_usable_expected.empty else 0
    completion_fraction = completed_instances / expected_instances if expected_instances else 0.0
    positive_floor_met = positive_instances >= min_positive_instances
    complete_mining = completed_instances == expected_instances and unexpected_artifact_instances == 0
    raw_artifacts_complete = complete_mining and raw_incomplete_instances == 0 and unexpected_raw_complete_instances == 0
    if complete_mining and positive_floor_met:
        decision = "ready_for_formal_elite_manifest"
    elif complete_mining:
        decision = "complete_but_sparse"
    else:
        decision = "continue_mining"

    summary = pd.DataFrame(
        [
            {
                "expected_instances": expected_instances,
                "completed_instances": completed_instances,
                "summary_completed_instances": summary_completed_instances,
                "raw_complete_instances": completed_instances,
                "raw_incomplete_instances": raw_incomplete_instances,
                "unexpected_artifact_instances": unexpected_artifact_instances,
                "unexpected_raw_complete_instances": unexpected_raw_complete_instances,
                "remaining_instances": len(remaining_key_set),
                "completion_fraction": completion_fraction,
                "positive_instances": positive_instances,
                "solved_samples": solved_samples,
                "min_positive_instances": int(min_positive_instances),
                "positive_floor_met": bool(positive_floor_met),
                "complete_mining": bool(complete_mining),
                "raw_artifacts_complete": bool(raw_artifacts_complete),
                "decision": decision,
            }
        ]
    )
    return summary, remaining


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
                values.append(f"{value:.4g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(path: Path, summary: pd.DataFrame, positives: pd.DataFrame, remaining: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Residual Elite Mining Progress",
        "",
        "This is a progress summary for residual-train/dev elite mining.",
        "It does not run solvers and is not a paper claim.",
        "",
        "## Summary",
        "",
        *markdown_table(
            summary,
            [
                "expected_instances",
                "completed_instances",
                "summary_completed_instances",
                "raw_complete_instances",
                "raw_incomplete_instances",
                "unexpected_artifact_instances",
                "unexpected_raw_complete_instances",
                "remaining_instances",
                "completion_fraction",
                "positive_instances",
                "solved_samples",
                "min_positive_instances",
                "positive_floor_met",
                "complete_mining",
                "raw_artifacts_complete",
                "decision",
            ],
        ),
        "",
        "## Positive Instances",
        "",
        *markdown_table(
            positives.sort_values(["size", "file_key"]) if not positives.empty else positives,
            ["family", "size", "file_key", "sample_seed", "solved_samples", "best_time", "best_sample_id"],
        ),
        "",
        "## Next Remaining Instances",
        "",
        *markdown_table(remaining.head(20), ["family", "size", "file_key"]),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize residual elite-mining progress without running solvers.")
    parser.add_argument("--input", type=Path, required=True, help="Expected residual split CSV.")
    parser.add_argument("--instances-dir", type=Path, required=True, help="Directory containing per-instance summary CSVs.")
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--remaining-csv", type=Path, default=None)
    parser.add_argument("--doc", type=Path, default=None)
    parser.add_argument("--min-positive-instances", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected = load_expected(args.input)
    completed = load_completed(args.instances_dir)
    summary, remaining = summarize(
        expected=expected,
        completed=completed,
        min_positive_instances=args.min_positive_instances,
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_csv, index=False)
    if args.remaining_csv:
        args.remaining_csv.parent.mkdir(parents=True, exist_ok=True)
        remaining.to_csv(args.remaining_csv, index=False)
    expected_key_set = instance_key_set(expected[KEY_COLUMNS].drop_duplicates().copy())
    completed_usable = completed[completed["raw_grid_complete"].eq(True)].copy() if "raw_grid_complete" in completed else completed
    positives = filter_to_instance_keys(completed_usable[completed_usable["solved_any"]].copy(), expected_key_set)
    if args.doc:
        write_doc(args.doc, summary=summary, positives=positives, remaining=remaining)
    row = summary.iloc[0]
    print(
        " ".join(
            [
                f"completed={int(row.completed_instances)}/{int(row.expected_instances)}",
                f"positive_instances={int(row.positive_instances)}",
                f"solved_samples={int(row.solved_samples)}",
                f"decision={row.decision}",
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
