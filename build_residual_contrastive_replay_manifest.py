from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

from build_residual_elite_replay_manifest import (
    SOLVED,
    enforce_expected_sampling,
    enforce_positive_floor,
    enforce_raw_checkpoint_provenance,
    enforce_raw_completeness,
    file_sha256,
    load_raw_samples,
    load_split_frame,
    load_split_map,
    parse_expected_sample_seeds,
    solver_time_column,
)


def solved_mask(frame: pd.DataFrame) -> pd.Series:
    solved = frame["Result"].astype(str).isin(SOLVED)
    if "solved" in frame.columns:
        solved = solved | frame["solved"].astype(str).str.lower().isin({"true", "1", "yes"})
    return solved


def progress_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in ["dead_ends_in_main", "decisions"]:
        if column not in out.columns:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    return out


def sort_negatives(frame: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    frame = progress_columns(frame)
    if mode == "low_progress":
        return frame.sort_values(["dead_ends_in_main", "decisions", "sample_seed", "sample_id"], kind="mergesort")
    if mode == "high_progress":
        return frame.sort_values(
            ["dead_ends_in_main", "decisions", "sample_seed", "sample_id"],
            ascending=[False, False, True, True],
            kind="mergesort",
        )
    if mode == "random":
        rng = random.Random(seed)
        order = list(frame.index)
        rng.shuffle(order)
        return frame.loc[order]
    raise ValueError(f"Unknown negative selection mode: {mode}")


def row_to_manifest(
    row: pd.Series,
    split_info: dict[str, str],
    checkpoint: Path | None,
    role: str,
    rank: int,
) -> dict:
    time_col = "CPU time" if "CPU time" in row.index else "time"
    raw_file = str(row["file"]) if "file" in row.index else ""
    cnf_path = split_info.get("cnf_path") or raw_file
    checkpoint_value = str(checkpoint) if checkpoint is not None else ""
    checkpoint_hash = file_sha256(checkpoint) if checkpoint is not None and checkpoint.exists() else ""
    return {
        "family": str(row["family"]),
        "size": int(row["size"]),
        "file_key": str(row["file_key"]),
        "split": split_info.get("split", ""),
        "row_id": split_info.get("row_id", ""),
        "cnf_path": cnf_path,
        "sample_role": role,
        "target_label": 1 if role == "positive" else 0,
        "rank_in_role": int(rank),
        "sample_seed": int(row["sample_seed"]),
        "solver_seed": int(row["solver_seed"]) if "solver_seed" in row.index else -1,
        "num_samples_generated": int(row["num_samples_generated"]),
        "sample_id": int(row["sample_id"]),
        "Result": str(row["Result"]),
        "CPU time": float(row[time_col]),
        "dead_ends_in_main": float(row["dead_ends_in_main"]) if "dead_ends_in_main" in row.index else float("nan"),
        "decisions": float(row["decisions"]) if "decisions" in row.index else float("nan"),
        "source_raw_csv": str(row["source_raw_csv"]),
        "source_raw_sha256": str(row["source_raw_sha256"]),
        "source_checkpoint": checkpoint_value,
        "source_checkpoint_sha256": checkpoint_hash,
    }


def build_manifest(
    raw: pd.DataFrame,
    split_map: dict[tuple[str, int, str], dict[str, str]],
    checkpoint: Path | None,
    max_positives_per_instance: int,
    max_negatives_per_instance: int,
    negative_selection: str,
    random_seed: int,
) -> pd.DataFrame:
    if max_positives_per_instance <= 0:
        raise ValueError("max_positives_per_instance must be positive.")
    if max_negatives_per_instance <= 0:
        raise ValueError("max_negatives_per_instance must be positive.")

    time_col = solver_time_column(raw)
    frame = raw.copy()
    frame["_solved"] = solved_mask(frame)
    rows = []
    for key, group in frame.groupby(["family", "size", "file_key"], sort=True):
        family, size, file_key = str(key[0]), int(key[1]), str(key[2])
        positives = group[group["_solved"]].copy()
        negatives = group[~group["_solved"]].copy()
        if positives.empty or negatives.empty:
            continue

        positives = positives.sort_values([time_col, "sample_seed", "sample_id"], kind="mergesort")
        positives = positives.head(max_positives_per_instance)
        negatives = sort_negatives(negatives, mode=negative_selection, seed=random_seed)
        negatives = negatives.head(max_negatives_per_instance)
        split_info = split_map.get((family, size, file_key), {})

        for rank, (_, row) in enumerate(positives.iterrows(), start=1):
            rows.append(row_to_manifest(row, split_info, checkpoint=checkpoint, role="positive", rank=rank))
        for rank, (_, row) in enumerate(negatives.iterrows(), start=1):
            rows.append(row_to_manifest(row, split_info, checkpoint=checkpoint, role="negative", rank=rank))

    columns = [
        "family",
        "size",
        "file_key",
        "split",
        "row_id",
        "cnf_path",
        "sample_role",
        "target_label",
        "rank_in_role",
        "sample_seed",
        "solver_seed",
        "num_samples_generated",
        "sample_id",
        "Result",
        "CPU time",
        "dead_ends_in_main",
        "decisions",
        "source_raw_csv",
        "source_raw_sha256",
        "source_checkpoint",
        "source_checkpoint_sha256",
    ]
    return pd.DataFrame(rows, columns=columns)


def positive_instance_count(manifest: pd.DataFrame) -> int:
    if manifest.empty:
        return 0
    positives = manifest[manifest["target_label"].astype(int).eq(1)]
    return positives[["family", "size", "file_key"]].drop_duplicates().shape[0]


def contrastive_group_count(manifest: pd.DataFrame) -> int:
    if manifest.empty:
        return 0
    counts = manifest.groupby(["family", "size", "file_key"])["target_label"].agg(
        has_positive=lambda values: any(int(value) == 1 for value in values),
        has_negative=lambda values: any(int(value) == 0 for value in values),
    )
    return int((counts["has_positive"] & counts["has_negative"]).sum())


def enforce_contrastive_floor(manifest: pd.DataFrame, min_positive_instances: int) -> None:
    if min_positive_instances <= 0:
        return
    positives = positive_instance_count(manifest)
    groups = contrastive_group_count(manifest)
    if positives < min_positive_instances or groups < min_positive_instances:
        raise ValueError(
            "Contrastive replay manifest has too few positive contrastive instances: "
            f"positive_instances={positives} contrastive_groups={groups} "
            f"required={min_positive_instances}."
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
                values.append(f"{value:.4g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(
    path: Path,
    manifest: pd.DataFrame,
    raw_paths: list[Path],
    split_csv: Path | None,
    checkpoint: Path | None,
    max_positives_per_instance: int,
    max_negatives_per_instance: int,
    negative_selection: str,
    min_positive_instances: int,
    require_raw_complete: bool,
    expected_sample_seeds: tuple[int, ...],
    expected_num_samples: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_rows = pd.DataFrame(
        [{"source_raw_csv": str(raw), "source_raw_sha256": file_sha256(raw)} for raw in raw_paths]
    )
    role_summary = (
        manifest.groupby(["split", "family", "size", "sample_role"], dropna=False)
        .agg(rows=("sample_id", "count"), instances=("file_key", "nunique"))
        .reset_index()
        if not manifest.empty
        else pd.DataFrame(columns=["split", "family", "size", "sample_role", "rows", "instances"])
    )
    fastest = manifest.sort_values(["target_label", "CPU time"], ascending=[False, True]).head(20)
    lines = [
        "# Residual Contrastive Replay Manifest",
        "",
        "This manifest contains solved sampled-March restarts and same-CNF failed",
        "samples for model-side contrastive residual-policy training. It is a",
        "training artifact, not an oracle-selector result.",
        "",
        f"- checkpoint: `{checkpoint if checkpoint is not None else ''}`",
        f"- checkpoint sha256: `{file_sha256(checkpoint) if checkpoint is not None and checkpoint.exists() else ''}`",
        f"- split csv: `{split_csv if split_csv is not None else ''}`",
        f"- max positives per instance: `{max_positives_per_instance}`",
        f"- max negatives per instance: `{max_negatives_per_instance}`",
        f"- negative selection: `{negative_selection}`",
        f"- min positive instances: `{min_positive_instances}`",
        f"- require raw complete: `{require_raw_complete}`",
        f"- expected sample seeds: `{','.join(str(seed) for seed in expected_sample_seeds)}`",
        f"- expected num samples: `{expected_num_samples}`",
        f"- manifest rows: `{len(manifest)}`",
        f"- positive instances: `{positive_instance_count(manifest)}`",
        f"- contrastive groups: `{contrastive_group_count(manifest)}`",
        "",
        "## Raw Sources",
        "",
        *markdown_table(source_rows, ["source_raw_csv", "source_raw_sha256"]),
        "",
        "## Role Summary",
        "",
        *markdown_table(role_summary, ["split", "family", "size", "sample_role", "rows", "instances"]),
        "",
        "## Selected Samples",
        "",
        *markdown_table(
            fastest,
            ["split", "family", "size", "file_key", "sample_role", "sample_seed", "sample_id", "CPU time"],
        ),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a residual contrastive replay manifest.")
    parser.add_argument("--raw-samples", type=Path, nargs="+", required=True)
    parser.add_argument("--split-csv", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--doc", type=Path, default=None)
    parser.add_argument("--max-positives-per-instance", type=int, default=2)
    parser.add_argument("--max-negatives-per-instance", type=int, default=4)
    parser.add_argument("--negative-selection", choices=["low_progress", "high_progress", "random"], default="low_progress")
    parser.add_argument("--random-seed", type=int, default=1729)
    parser.add_argument("--min-positive-instances", type=int, default=0)
    parser.add_argument("--require-raw-complete", action="store_true")
    parser.add_argument("--expected-sample-seeds", default="")
    parser.add_argument("--expected-num-samples", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_paths = [path.resolve() for path in args.raw_samples]
    split_csv = args.split_csv.resolve() if args.split_csv else None
    checkpoint = args.checkpoint.resolve() if args.checkpoint else None
    raw = load_raw_samples(raw_paths)
    expected_sample_seeds = parse_expected_sample_seeds(args.expected_sample_seeds)
    enforce_expected_sampling(raw, expected_sample_seeds, int(args.expected_num_samples))
    enforce_raw_checkpoint_provenance(raw, checkpoint)
    split_frame = load_split_frame(split_csv)
    enforce_raw_completeness(raw, split_frame, require_raw_complete=bool(args.require_raw_complete))
    manifest = build_manifest(
        raw=raw,
        split_map=load_split_map(split_csv),
        checkpoint=checkpoint,
        max_positives_per_instance=int(args.max_positives_per_instance),
        max_negatives_per_instance=int(args.max_negatives_per_instance),
        negative_selection=str(args.negative_selection),
        random_seed=int(args.random_seed),
    )
    enforce_positive_floor(
        manifest[manifest["target_label"].astype(int).eq(1)],
        min_positive_instances=int(args.min_positive_instances),
    )
    enforce_contrastive_floor(manifest, min_positive_instances=int(args.min_positive_instances))
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.output_csv, index=False)
    if args.doc:
        write_doc(
            path=args.doc,
            manifest=manifest,
            raw_paths=raw_paths,
            split_csv=split_csv,
            checkpoint=checkpoint,
            max_positives_per_instance=int(args.max_positives_per_instance),
            max_negatives_per_instance=int(args.max_negatives_per_instance),
            negative_selection=str(args.negative_selection),
            min_positive_instances=int(args.min_positive_instances),
            require_raw_complete=bool(args.require_raw_complete),
            expected_sample_seeds=expected_sample_seeds,
            expected_num_samples=int(args.expected_num_samples),
        )
    print(
        f"rows={len(manifest)} positive_instances={positive_instance_count(manifest)} "
        f"contrastive_groups={contrastive_group_count(manifest)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
