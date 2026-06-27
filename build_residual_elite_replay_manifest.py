from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def solver_time_column(frame: pd.DataFrame) -> str:
    if "CPU time" in frame.columns:
        return "CPU time"
    if "time" in frame.columns:
        return "time"
    raise KeyError("Expected either 'CPU time' or 'time' in raw solver samples.")


def load_split_map(split_csv: Path | None) -> dict[tuple[str, int, str], dict[str, str]]:
    if split_csv is None:
        return {}
    frame = pd.read_csv(split_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Split CSV is missing columns: {sorted(missing)}")
    mapping = {}
    for row in frame.itertuples(index=False):
        key = (str(row.family), int(row.size), str(row.file_key))
        mapping[key] = {
            "split": str(getattr(row, "split", "")),
            "cnf_path": str(getattr(row, "cnf_path", "")),
            "row_id": str(getattr(row, "row_id", "")),
        }
    return mapping


def load_split_frame(split_csv: Path | None) -> pd.DataFrame | None:
    if split_csv is None:
        return None
    frame = pd.read_csv(split_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Split CSV is missing columns: {sorted(missing)}")
    return frame


def load_raw_samples(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        frame["source_raw_csv"] = str(path)
        frame["source_raw_sha256"] = file_sha256(path)
        frames.append(frame)
    if not frames:
        raise ValueError("At least one raw sample CSV is required.")
    raw = pd.concat(frames, ignore_index=True)
    required = {
        "family",
        "size",
        "file_key",
        "sample_seed",
        "sample_id",
        "Result",
        "num_samples_generated",
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Raw sample CSV is missing columns: {sorted(missing)}")
    return raw


def instance_keys(frame: pd.DataFrame) -> set[tuple[str, int, str]]:
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Frame is missing instance-key columns: {sorted(missing)}")
    return {
        (str(row.family), int(row.size), str(row.file_key))
        for row in frame[["family", "size", "file_key"]].drop_duplicates().itertuples(index=False)
    }


def raw_sample_grid_issues(raw: pd.DataFrame) -> list[str]:
    required = {"family", "size", "file_key", "sample_seed", "sample_id", "num_samples_generated"}
    missing = sorted(required - set(raw.columns))
    if missing:
        return [f"missing_grid_columns={missing}"]

    frame = raw.copy()
    for column in ["sample_seed", "sample_id", "num_samples_generated"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    invalid_numeric = int(frame[["sample_seed", "sample_id", "num_samples_generated"]].isna().any(axis=1).sum())
    if invalid_numeric:
        return [f"invalid_numeric_sample_grid_rows={invalid_numeric}"]

    frame["sample_seed"] = frame["sample_seed"].astype(int)
    frame["sample_id"] = frame["sample_id"].astype(int)
    frame["num_samples_generated"] = frame["num_samples_generated"].astype(int)

    issues: list[str] = []
    seed_sets = (
        frame.groupby(["family", "size", "file_key"], sort=True)["sample_seed"]
        .apply(lambda values: tuple(sorted(set(int(value) for value in values))))
        .to_dict()
    )
    distinct_seed_sets = sorted(set(seed_sets.values()))
    if len(distinct_seed_sets) > 1:
        examples = [
            f"{family}/{size}/{file_key}:seeds={list(seeds)}"
            for (family, size, file_key), seeds in list(seed_sets.items())[:3]
        ]
        issues.append(f"inconsistent_sample_seed_sets={len(distinct_seed_sets)} examples={examples}")

    for (family, size, file_key, sample_seed), group in frame.groupby(
        ["family", "size", "file_key", "sample_seed"],
        sort=True,
    ):
        num_samples_values = sorted(set(int(value) for value in group["num_samples_generated"]))
        if len(num_samples_values) != 1:
            issues.append(
                f"{family}/{size}/{file_key}/seed{sample_seed}:"
                f"inconsistent_num_samples_generated={num_samples_values}"
            )
            continue
        num_samples = num_samples_values[0]
        if num_samples <= 0:
            issues.append(f"{family}/{size}/{file_key}/seed{sample_seed}:nonpositive_num_samples={num_samples}")
            continue
        observed = [int(value) for value in group["sample_id"]]
        observed_set = set(observed)
        expected_set = set(range(num_samples))
        duplicate_count = len(observed) - len(observed_set)
        missing_count = len(expected_set - observed_set)
        extra_count = len(observed_set - expected_set)
        if duplicate_count or missing_count or extra_count:
            issues.append(
                f"{family}/{size}/{file_key}/seed{sample_seed}:"
                f"duplicates={duplicate_count} missing_sample_ids={missing_count} "
                f"out_of_range_sample_ids={extra_count} expected={num_samples} observed_rows={len(observed)}"
            )
    return issues


def parse_expected_sample_seeds(raw: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if raw.strip() and not seeds:
        raise ValueError("Expected sample seed list cannot be empty.")
    return seeds


def enforce_expected_sampling(
    raw: pd.DataFrame,
    expected_sample_seeds: tuple[int, ...],
    expected_num_samples: int,
) -> None:
    required = {"sample_seed", "num_samples_generated"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Raw sample CSV is missing sampling columns: {missing}")

    sample_seeds = pd.to_numeric(raw["sample_seed"], errors="coerce")
    num_samples = pd.to_numeric(raw["num_samples_generated"], errors="coerce")
    if sample_seeds.isna().any() or num_samples.isna().any():
        raise ValueError("Raw sample CSV contains non-numeric sample_seed or num_samples_generated values.")

    if expected_sample_seeds:
        observed = tuple(sorted(set(sample_seeds.astype(int))))
        expected = tuple(sorted(set(expected_sample_seeds)))
        if observed != expected:
            raise ValueError(
                "Raw sample seed set does not match the formal protocol: "
                f"observed={observed} expected={expected}."
            )

    if expected_num_samples > 0:
        observed_num_samples = tuple(sorted(set(num_samples.astype(int))))
        if observed_num_samples != (int(expected_num_samples),):
            raise ValueError(
                "Raw num_samples_generated does not match the formal protocol: "
                f"observed={observed_num_samples} expected={expected_num_samples}."
            )


def enforce_raw_checkpoint_provenance(raw: pd.DataFrame, checkpoint: Path | None) -> None:
    if checkpoint is None or "source_checkpoint_sha256" not in raw.columns:
        return
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    expected_hash = file_sha256(checkpoint)
    observed_hashes = set(raw["source_checkpoint_sha256"].dropna().astype(str))
    observed_hashes.discard("")
    if observed_hashes and observed_hashes != {expected_hash}:
        raise ValueError(
            "Raw sample checkpoint hash does not match the formal checkpoint: "
            f"observed={sorted(observed_hashes)} expected={expected_hash}."
        )


def enforce_raw_completeness(raw: pd.DataFrame, split_frame: pd.DataFrame | None, require_raw_complete: bool) -> None:
    if not require_raw_complete:
        return
    if split_frame is None:
        raise ValueError("--require-raw-complete requires --split-csv.")
    split_keys = instance_keys(split_frame)
    raw_keys = instance_keys(raw)
    missing = sorted(split_keys - raw_keys)
    extra = sorted(raw_keys - split_keys)
    if missing or extra:
        raise ValueError(
            "Raw sample coverage does not exactly match the split CSV: "
            f"missing_instances={len(missing)} extra_instances={len(extra)}. "
            "Run summarize-only after mining finishes and use that complete raw snapshot "
            "for the formal elite manifest."
        )
    grid_issues = raw_sample_grid_issues(raw)
    if grid_issues:
        shown = "; ".join(grid_issues[:5])
        if len(grid_issues) > 5:
            shown += f"; ... total_issues={len(grid_issues)}"
        raise ValueError(
            "Raw sample grid is incomplete or inconsistent: "
            f"{shown}. Run strict summarize-only after mining finishes; do not use "
            "a truncated raw snapshot for the formal elite manifest."
        )


def build_manifest(
    raw: pd.DataFrame,
    split_map: dict[tuple[str, int, str], dict[str, str]],
    checkpoint: Path | None,
    max_per_instance: int,
) -> pd.DataFrame:
    if max_per_instance <= 0:
        raise ValueError("max_per_instance must be positive.")

    time_col = solver_time_column(raw)
    frame = raw.copy()
    if "solved" in frame.columns:
        solved = frame["solved"].astype(str).str.lower().isin({"true", "1"})
        solved = solved | frame["Result"].astype(str).isin(SOLVED)
    else:
        solved = frame["Result"].astype(str).isin(SOLVED)
    frame = frame[solved].copy()

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "family",
                "size",
                "file_key",
                "split",
                "row_id",
                "cnf_path",
                "sample_seed",
                "solver_seed",
                "num_samples_generated",
                "sample_id",
                "elite_rank_in_instance",
                "Result",
                "CPU time",
                "dead_ends_in_main",
                "decisions",
                "source_raw_csv",
                "source_raw_sha256",
                "source_checkpoint",
                "source_checkpoint_sha256",
            ]
        )

    frame["_time"] = pd.to_numeric(frame[time_col], errors="coerce")
    sort_columns = ["family", "size", "file_key", "_time", "sample_seed", "sample_id"]
    frame = frame.sort_values(sort_columns, kind="mergesort")
    frame["elite_rank_in_instance"] = (
        frame.groupby(["family", "size", "file_key"], sort=False).cumcount() + 1
    )
    frame = frame[frame["elite_rank_in_instance"] <= max_per_instance].copy()

    checkpoint_value = str(checkpoint) if checkpoint is not None else ""
    checkpoint_hash = file_sha256(checkpoint) if checkpoint is not None and checkpoint.exists() else ""

    rows = []
    for _, row in frame.iterrows():
        key = (str(row["family"]), int(row["size"]), str(row["file_key"]))
        split_info = split_map.get(key, {})
        raw_file = str(row["file"]) if "file" in row else ""
        cnf_path = split_info.get("cnf_path") or raw_file
        rows.append(
            {
                "family": key[0],
                "size": key[1],
                "file_key": key[2],
                "split": split_info.get("split", ""),
                "row_id": split_info.get("row_id", ""),
                "cnf_path": cnf_path,
                "sample_seed": int(row["sample_seed"]),
                "solver_seed": int(row["solver_seed"]) if "solver_seed" in row else -1,
                "num_samples_generated": int(row["num_samples_generated"]),
                "sample_id": int(row["sample_id"]),
                "elite_rank_in_instance": int(row["elite_rank_in_instance"]),
                "Result": str(row["Result"]),
                "CPU time": float(row[time_col]),
                "dead_ends_in_main": float(row["dead_ends_in_main"]) if "dead_ends_in_main" in row else float("nan"),
                "decisions": float(row["decisions"]) if "decisions" in row else float("nan"),
                "source_raw_csv": str(row["source_raw_csv"]),
                "source_raw_sha256": str(row["source_raw_sha256"]),
                "source_checkpoint": checkpoint_value,
                "source_checkpoint_sha256": checkpoint_hash,
            }
        )

    return pd.DataFrame(rows)


def positive_instance_count(manifest: pd.DataFrame) -> int:
    if manifest.empty:
        return 0
    return manifest[["family", "size", "file_key"]].drop_duplicates().shape[0]


def enforce_positive_floor(manifest: pd.DataFrame, min_positive_instances: int) -> None:
    if min_positive_instances <= 0:
        return
    positive_instances = positive_instance_count(manifest)
    if positive_instances < min_positive_instances:
        raise ValueError(
            "Elite replay manifest has too few positive instances: "
            f"{positive_instances} < {min_positive_instances}. "
            "Continue residual-train/dev mining or use a larger mining seed budget; "
            "do not train formal elite replay from a sparse manifest."
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
    max_per_instance: int,
    min_positive_instances: int,
    require_raw_complete: bool,
    expected_sample_seeds: tuple[int, ...],
    expected_num_samples: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_rows = pd.DataFrame(
        [
            {"source_raw_csv": str(raw), "source_raw_sha256": file_sha256(raw)}
            for raw in raw_paths
        ]
    )
    instance_summary = (
        manifest.groupby(["split", "family", "size"], dropna=False)
        .agg(elite_rows=("sample_id", "count"), positive_instances=("file_key", "nunique"))
        .reset_index()
        if not manifest.empty
        else pd.DataFrame(columns=["split", "family", "size", "elite_rows", "positive_instances"])
    )
    lines = [
        "# Residual Elite Replay Manifest",
        "",
        "This manifest contains solved sampled-March restarts for model-side",
        "elite replay / behavior-cloning training. It is a training artifact,",
        "not an oracle-selector result.",
        "",
        f"- checkpoint: `{checkpoint if checkpoint is not None else ''}`",
        f"- checkpoint sha256: `{file_sha256(checkpoint) if checkpoint is not None and checkpoint.exists() else ''}`",
        f"- split csv: `{split_csv if split_csv is not None else ''}`",
        f"- max per instance: `{max_per_instance}`",
        f"- min positive instances: `{min_positive_instances}`",
        f"- require raw complete: `{require_raw_complete}`",
        f"- expected sample seeds: `{','.join(str(seed) for seed in expected_sample_seeds)}`",
        f"- expected num samples: `{expected_num_samples}`",
        f"- manifest rows: `{len(manifest)}`",
        f"- positive instances: `{positive_instance_count(manifest)}`",
        "",
        "## Raw Sources",
        "",
        *markdown_table(source_rows, ["source_raw_csv", "source_raw_sha256"]),
        "",
        "## Split Summary",
        "",
        *markdown_table(instance_summary, ["split", "family", "size", "elite_rows", "positive_instances"]),
        "",
        "## Fastest Elites",
        "",
        *markdown_table(
            manifest.sort_values("CPU time").head(20) if not manifest.empty else manifest,
            ["split", "family", "size", "file_key", "sample_seed", "sample_id", "elite_rank_in_instance", "CPU time"],
        ),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a solved-sample elite replay manifest.")
    parser.add_argument("--raw-samples", type=Path, nargs="+", required=True)
    parser.add_argument("--split-csv", type=Path, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--doc", type=Path, default=None)
    parser.add_argument("--max-per-instance", type=int, default=4)
    parser.add_argument(
        "--min-positive-instances",
        type=int,
        default=0,
        help="Optional protocol guard; refuse to write if the manifest has fewer positive instances.",
    )
    parser.add_argument(
        "--require-raw-complete",
        action="store_true",
        help="Require raw samples to cover exactly the instances in --split-csv before writing.",
    )
    parser.add_argument(
        "--expected-sample-seeds",
        default="",
        help="Optional comma-separated formal sample-seed set; refuse raw artifacts with a different set.",
    )
    parser.add_argument(
        "--expected-num-samples",
        type=int,
        default=0,
        help="Optional formal num_samples_generated value; refuse raw artifacts with a different value.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_paths = [path.resolve() for path in args.raw_samples]
    split_csv = args.split_csv.resolve() if args.split_csv else None
    checkpoint = args.checkpoint.resolve() if args.checkpoint else None
    raw = load_raw_samples(raw_paths)
    expected_sample_seeds = parse_expected_sample_seeds(args.expected_sample_seeds)
    enforce_expected_sampling(
        raw=raw,
        expected_sample_seeds=expected_sample_seeds,
        expected_num_samples=int(args.expected_num_samples),
    )
    enforce_raw_checkpoint_provenance(raw=raw, checkpoint=checkpoint)
    split_frame = load_split_frame(split_csv)
    enforce_raw_completeness(
        raw=raw,
        split_frame=split_frame,
        require_raw_complete=bool(args.require_raw_complete),
    )
    manifest = build_manifest(
        raw=raw,
        split_map=load_split_map(split_csv),
        checkpoint=checkpoint,
        max_per_instance=args.max_per_instance,
    )
    enforce_positive_floor(manifest, min_positive_instances=args.min_positive_instances)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.output_csv, index=False)
    if args.doc:
        write_doc(
            path=args.doc,
            manifest=manifest,
            raw_paths=raw_paths,
            split_csv=split_csv,
            checkpoint=checkpoint,
            max_per_instance=args.max_per_instance,
            min_positive_instances=args.min_positive_instances,
            require_raw_complete=bool(args.require_raw_complete),
            expected_sample_seeds=expected_sample_seeds,
            expected_num_samples=int(args.expected_num_samples),
        )
    print(
        f"elite_rows={len(manifest)} positive_instances="
        f"{positive_instance_count(manifest)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
