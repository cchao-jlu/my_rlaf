from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_residual_elite_replay_manifest import parse_expected_sample_seeds
from summarize_residual_elite_mining import KEY_COLUMNS, load_completed, load_expected, markdown_table


GRID_COLUMNS = KEY_COLUMNS + ["sample_seed"]


def grid_key_set(frame: pd.DataFrame) -> set[tuple[str, int, str, int]]:
    if frame.empty:
        return set()
    return set(
        zip(
            frame["family"].astype(str),
            pd.to_numeric(frame["size"], errors="raise").astype(int),
            frame["file_key"].astype(str),
            pd.to_numeric(frame["sample_seed"], errors="raise").astype(int),
        )
    )


def filter_to_grid_keys(frame: pd.DataFrame, keys: set[tuple[str, int, str, int]]) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    row_keys = list(
        zip(
            frame["family"].astype(str),
            pd.to_numeric(frame["size"], errors="raise").astype(int),
            frame["file_key"].astype(str),
            pd.to_numeric(frame["sample_seed"], errors="raise").astype(int),
        )
    )
    return frame.loc[[key in keys for key in row_keys]].copy()


def expected_grid(expected: pd.DataFrame, sample_seeds: tuple[int, ...]) -> pd.DataFrame:
    if not sample_seeds:
        raise ValueError("expected_sample_seeds is required for multiseed mining progress.")
    expected_keys = expected[KEY_COLUMNS].drop_duplicates().copy()
    rows = []
    for row in expected_keys.itertuples(index=False):
        for sample_seed in sample_seeds:
            rows.append(
                {
                    "family": str(row.family),
                    "size": int(row.size),
                    "file_key": str(row.file_key),
                    "sample_seed": int(sample_seed),
                }
            )
    return pd.DataFrame(rows, columns=GRID_COLUMNS)


def instance_count_from_grid_keys(keys: set[tuple[str, int, str, int]]) -> int:
    return len({(family, size, file_key) for family, size, file_key, _ in keys})


def all_seed_instance_count(keys: set[tuple[str, int, str, int]], sample_seeds: tuple[int, ...]) -> int:
    expected_seed_set = set(sample_seeds)
    by_instance: dict[tuple[str, int, str], set[int]] = {}
    for family, size, file_key, sample_seed in keys:
        by_instance.setdefault((family, size, file_key), set()).add(sample_seed)
    return sum(1 for seeds in by_instance.values() if seeds == expected_seed_set)


def summarize(
    expected: pd.DataFrame,
    completed: pd.DataFrame,
    expected_sample_seeds: tuple[int, ...],
    min_positive_instances: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "raw_grid_complete" not in completed.columns:
        raise ValueError(
            "Completed mining frame is missing raw_grid_complete. "
            "Use load_completed() so progress readiness is based on audited raw artifacts."
        )

    grid = expected_grid(expected, expected_sample_seeds)
    expected_grid_keys = grid_key_set(grid)
    expected_instances = expected[KEY_COLUMNS].drop_duplicates().shape[0]
    expected_seed_pairs = len(expected_grid_keys)

    summary_grid_keys = grid_key_set(completed)
    completed_usable = completed[completed["raw_grid_complete"].eq(True)].copy()
    raw_complete_grid_keys = grid_key_set(completed_usable)

    summary_expected_grid_keys = summary_grid_keys & expected_grid_keys
    raw_complete_expected_grid_keys = raw_complete_grid_keys & expected_grid_keys
    unexpected_summary_grid_keys = summary_grid_keys - expected_grid_keys
    unexpected_raw_complete_grid_keys = raw_complete_grid_keys - expected_grid_keys
    raw_incomplete_grid_keys = summary_expected_grid_keys - raw_complete_expected_grid_keys
    remaining_grid_keys = expected_grid_keys - raw_complete_expected_grid_keys

    duplicate_summary_seed_pairs = 0
    duplicate_raw_complete_seed_pairs = 0
    if not completed.empty:
        duplicate_summary_seed_pairs = int(len(completed) - len(summary_grid_keys))
    if not completed_usable.empty:
        duplicate_raw_complete_seed_pairs = int(len(completed_usable) - len(raw_complete_grid_keys))

    completed_usable_expected = filter_to_grid_keys(completed_usable, raw_complete_expected_grid_keys)
    completed_unique = completed_usable_expected.drop_duplicates(GRID_COLUMNS, keep="first")
    positives = completed_unique[completed_unique["solved_any"].astype(bool)].copy()
    positive_seed_pairs = positives[GRID_COLUMNS].drop_duplicates().shape[0] if not positives.empty else 0
    positive_instances = positives[KEY_COLUMNS].drop_duplicates().shape[0] if not positives.empty else 0
    solved_samples = int(pd.to_numeric(completed_unique["solved_samples"], errors="coerce").fillna(0).sum())

    completed_seed_pairs = len(raw_complete_expected_grid_keys)
    summary_completed_seed_pairs = len(summary_expected_grid_keys)
    completed_instances_any_seed = instance_count_from_grid_keys(raw_complete_expected_grid_keys)
    completed_instances_all_seeds = all_seed_instance_count(raw_complete_expected_grid_keys, expected_sample_seeds)
    completion_fraction = completed_seed_pairs / expected_seed_pairs if expected_seed_pairs else 0.0
    positive_floor_met = positive_instances >= min_positive_instances
    complete_mining = (
        completed_seed_pairs == expected_seed_pairs
        and len(unexpected_summary_grid_keys) == 0
        and duplicate_summary_seed_pairs == 0
    )
    raw_artifacts_complete = (
        complete_mining
        and len(raw_incomplete_grid_keys) == 0
        and len(unexpected_raw_complete_grid_keys) == 0
        and duplicate_raw_complete_seed_pairs == 0
    )
    if raw_artifacts_complete and positive_floor_met:
        decision = "ready_for_formal_multiseed_manifest"
    elif raw_artifacts_complete:
        decision = "complete_but_sparse"
    else:
        decision = "continue_mining"

    summary = pd.DataFrame(
        [
            {
                "expected_instances": int(expected_instances),
                "expected_sample_seeds": ",".join(str(seed) for seed in expected_sample_seeds),
                "expected_seed_pairs": int(expected_seed_pairs),
                "completed_seed_pairs": int(completed_seed_pairs),
                "summary_completed_seed_pairs": int(summary_completed_seed_pairs),
                "raw_complete_seed_pairs": int(completed_seed_pairs),
                "raw_incomplete_seed_pairs": int(len(raw_incomplete_grid_keys)),
                "unexpected_artifact_seed_pairs": int(len(unexpected_summary_grid_keys)),
                "unexpected_raw_complete_seed_pairs": int(len(unexpected_raw_complete_grid_keys)),
                "duplicate_summary_seed_pairs": int(duplicate_summary_seed_pairs),
                "duplicate_raw_complete_seed_pairs": int(duplicate_raw_complete_seed_pairs),
                "remaining_seed_pairs": int(len(remaining_grid_keys)),
                "completed_instances_any_seed": int(completed_instances_any_seed),
                "completed_instances_all_seeds": int(completed_instances_all_seeds),
                "completion_fraction": float(completion_fraction),
                "positive_instances": int(positive_instances),
                "positive_seed_pairs": int(positive_seed_pairs),
                "solved_samples": int(solved_samples),
                "min_positive_instances": int(min_positive_instances),
                "positive_floor_met": bool(positive_floor_met),
                "complete_mining": bool(complete_mining),
                "raw_artifacts_complete": bool(raw_artifacts_complete),
                "decision": decision,
            }
        ]
    )
    remaining = filter_to_grid_keys(grid, remaining_grid_keys).sort_values(GRID_COLUMNS).reset_index(drop=True)
    return summary, remaining, positives.sort_values(GRID_COLUMNS).reset_index(drop=True)


def write_doc(path: Path, summary: pd.DataFrame, positives: pd.DataFrame, remaining: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Residual Multiseed Mining Progress",
        "",
        "This is a progress summary for residual train/dev multi-seed mining.",
        "It does not run solvers and is not a paper claim.",
        "",
        "## Summary",
        "",
        *markdown_table(
            summary,
            [
                "expected_instances",
                "expected_sample_seeds",
                "expected_seed_pairs",
                "completed_seed_pairs",
                "summary_completed_seed_pairs",
                "raw_complete_seed_pairs",
                "raw_incomplete_seed_pairs",
                "unexpected_artifact_seed_pairs",
                "unexpected_raw_complete_seed_pairs",
                "duplicate_summary_seed_pairs",
                "duplicate_raw_complete_seed_pairs",
                "remaining_seed_pairs",
                "completed_instances_any_seed",
                "completed_instances_all_seeds",
                "completion_fraction",
                "positive_instances",
                "positive_seed_pairs",
                "solved_samples",
                "min_positive_instances",
                "positive_floor_met",
                "complete_mining",
                "raw_artifacts_complete",
                "decision",
            ],
        ),
        "",
        "## Positive Seed Pairs",
        "",
        *markdown_table(
            positives,
            ["family", "size", "file_key", "sample_seed", "solved_samples", "best_time", "best_sample_id"],
        ),
        "",
        "## Next Remaining Seed Pairs",
        "",
        *markdown_table(remaining.head(30), GRID_COLUMNS),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize residual multi-seed mining progress without running solvers.")
    parser.add_argument("--input", type=Path, required=True, help="Expected residual split CSV.")
    parser.add_argument("--instances-dir", type=Path, required=True, help="Directory containing per-instance summary CSVs.")
    parser.add_argument("--expected-sample-seeds", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--remaining-csv", type=Path, default=None)
    parser.add_argument("--positives-csv", type=Path, default=None)
    parser.add_argument("--doc", type=Path, default=None)
    parser.add_argument("--min-positive-instances", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_sample_seeds = parse_expected_sample_seeds(args.expected_sample_seeds)
    expected = load_expected(args.input)
    completed = load_completed(args.instances_dir)
    summary, remaining, positives = summarize(
        expected=expected,
        completed=completed,
        expected_sample_seeds=expected_sample_seeds,
        min_positive_instances=int(args.min_positive_instances),
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_csv, index=False)
    if args.remaining_csv:
        args.remaining_csv.parent.mkdir(parents=True, exist_ok=True)
        remaining.to_csv(args.remaining_csv, index=False)
    if args.positives_csv:
        args.positives_csv.parent.mkdir(parents=True, exist_ok=True)
        positives.to_csv(args.positives_csv, index=False)
    if args.doc:
        write_doc(args.doc, summary=summary, positives=positives, remaining=remaining)
    row = summary.iloc[0]
    print(
        " ".join(
            [
                f"completed_seed_pairs={int(row.completed_seed_pairs)}/{int(row.expected_seed_pairs)}",
                f"completed_instances_all_seeds={int(row.completed_instances_all_seeds)}/{int(row.expected_instances)}",
                f"positive_instances={int(row.positive_instances)}",
                f"positive_seed_pairs={int(row.positive_seed_pairs)}",
                f"solved_samples={int(row.solved_samples)}",
                f"decision={row.decision}",
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
