from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd
from omegaconf import OmegaConf


SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, name: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def positive_instance_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    return frame[["family", "size", "file_key"]].drop_duplicates().shape[0]


def required_columns(frame: pd.DataFrame, columns: set[str], label: str) -> list[dict[str, str]]:
    missing = sorted(columns - set(frame.columns))
    return [check(not missing, f"{label}_has_required_columns", f"missing={missing}")]


def load_raw_sources(manifest: pd.DataFrame) -> pd.DataFrame:
    if manifest.empty or "source_raw_csv" not in manifest:
        return pd.DataFrame()
    frames = []
    for raw_path in sorted(set(manifest["source_raw_csv"].astype(str))):
        path = Path(raw_path)
        if not path.exists():
            continue
        raw = pd.read_csv(path)
        raw["_source_raw_csv"] = str(path)
        frames.append(raw)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def solved_sample_keys(frame: pd.DataFrame) -> set[tuple[str, int, str, int, int, int]]:
    if frame.empty:
        return set()
    required = {"family", "size", "file_key", "sample_seed", "num_samples_generated", "sample_id", "Result"}
    if required - set(frame.columns):
        return set()
    solved = frame[frame["Result"].astype(str).isin(SOLVED)].copy()
    return {
        (
            str(row.family),
            int(row.size),
            str(row.file_key),
            int(row.sample_seed),
            int(row.num_samples_generated),
            int(row.sample_id),
        )
        for row in solved.itertuples(index=False)
    }


def manifest_sample_keys(frame: pd.DataFrame) -> set[tuple[str, int, str, int, int, int]]:
    required = {"family", "size", "file_key", "sample_seed", "num_samples_generated", "sample_id"}
    if frame.empty or required - set(frame.columns):
        return set()
    return {
        (
            str(row.family),
            int(row.size),
            str(row.file_key),
            int(row.sample_seed),
            int(row.num_samples_generated),
            int(row.sample_id),
        )
        for row in frame.itertuples(index=False)
    }


def instance_keys(frame: pd.DataFrame) -> set[tuple[str, int, str]]:
    required = {"family", "size", "file_key"}
    if frame.empty or required - set(frame.columns):
        return set()
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
    if len(set(seed_sets.values())) > 1:
        issues.append(f"inconsistent_sample_seed_sets={len(set(seed_sets.values()))}")

    for (family, size, file_key, sample_seed), group in frame.groupby(
        ["family", "size", "file_key", "sample_seed"],
        sort=True,
    ):
        num_samples_values = sorted(set(int(value) for value in group["num_samples_generated"]))
        if len(num_samples_values) != 1:
            issues.append(f"{family}/{size}/{file_key}/seed{sample_seed}:inconsistent_num_samples")
            continue
        num_samples = num_samples_values[0]
        observed = [int(value) for value in group["sample_id"]]
        observed_set = set(observed)
        expected_set = set(range(num_samples))
        duplicate_count = len(observed) - len(observed_set)
        missing_count = len(expected_set - observed_set)
        extra_count = len(observed_set - expected_set)
        if duplicate_count or missing_count or extra_count:
            issues.append(
                f"{family}/{size}/{file_key}/seed{sample_seed}:"
                f"duplicates={duplicate_count} missing={missing_count} out_of_range={extra_count}"
            )
    return issues


def parse_expected_sample_seeds(raw: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if raw.strip() and not seeds:
        raise ValueError("Expected sample seed list cannot be empty.")
    return seeds


def sampling_protocol_checks(
    raw: pd.DataFrame,
    expected_sample_seeds: tuple[int, ...],
    expected_num_samples: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    required = {"sample_seed", "num_samples_generated"}
    missing = sorted(required - set(raw.columns))
    rows.append(check(not missing, "manifest_raw_sources_have_sampling_columns", f"missing={missing}"))
    if missing or raw.empty:
        return rows

    sample_seeds = pd.to_numeric(raw["sample_seed"], errors="coerce")
    num_samples = pd.to_numeric(raw["num_samples_generated"], errors="coerce")
    valid_numeric = not sample_seeds.isna().any() and not num_samples.isna().any()
    rows.append(
        check(
            valid_numeric,
            "manifest_raw_sources_sampling_values_numeric",
            f"invalid_rows={int((sample_seeds.isna() | num_samples.isna()).sum())}",
        )
    )
    if not valid_numeric:
        return rows

    if expected_sample_seeds:
        observed_seeds = tuple(sorted(set(sample_seeds.astype(int))))
        expected_seeds = tuple(sorted(set(expected_sample_seeds)))
        rows.append(
            check(
                observed_seeds == expected_seeds,
                "manifest_raw_sources_sample_seeds_match_expected",
                f"observed={observed_seeds} expected={expected_seeds}",
            )
        )
    if expected_num_samples > 0:
        observed_num_samples = tuple(sorted(set(num_samples.astype(int))))
        rows.append(
            check(
                observed_num_samples == (int(expected_num_samples),),
                "manifest_raw_sources_num_samples_match_expected",
                f"observed={observed_num_samples} expected={expected_num_samples}",
            )
        )
    return rows


def raw_checkpoint_provenance_checks(raw: pd.DataFrame, checkpoint: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if "source_checkpoint_sha256" not in raw.columns:
        rows.append(
            check(
                True,
                "manifest_raw_sources_checkpoint_hash_matches_when_recorded",
                "source_checkpoint_sha256 not recorded in raw sources",
            )
        )
        return rows
    expected_hash = file_sha256(checkpoint)
    observed_hashes = set(raw["source_checkpoint_sha256"].dropna().astype(str))
    observed_hashes.discard("")
    rows.append(
        check(
            not observed_hashes or observed_hashes == {expected_hash},
            "manifest_raw_sources_checkpoint_hash_matches_when_recorded",
            f"observed={sorted(observed_hashes)} expected={expected_hash}",
        )
    )
    return rows


def audit_manifest(
    manifest_path: Path,
    split_csv: Path,
    checkpoint: Path,
    expected_split: str,
    min_positive_instances: int,
    max_per_instance: int,
    expected_sample_seeds: tuple[int, ...] = (),
    expected_num_samples: int = 0,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not manifest_path.exists():
        return [check(False, "manifest_exists", f"missing={manifest_path}")]
    if not split_csv.exists():
        return [check(False, "split_csv_exists", f"missing={split_csv}")]
    if not checkpoint.exists():
        return [check(False, "checkpoint_exists", f"missing={checkpoint}")]

    manifest = pd.read_csv(manifest_path)
    split = pd.read_csv(split_csv)
    rows.append(check(True, "manifest_exists", str(manifest_path)))
    rows.append(check(True, "split_csv_exists", str(split_csv)))
    rows.append(check(True, "checkpoint_exists", str(checkpoint)))

    manifest_required = {
        "family",
        "size",
        "file_key",
        "split",
        "row_id",
        "cnf_path",
        "sample_seed",
        "num_samples_generated",
        "sample_id",
        "elite_rank_in_instance",
        "Result",
        "source_raw_csv",
        "source_raw_sha256",
        "source_checkpoint",
        "source_checkpoint_sha256",
    }
    split_required = {"family", "size", "file_key", "split", "row_id", "cnf_path"}
    rows.extend(required_columns(manifest, manifest_required, "manifest"))
    rows.extend(required_columns(split, split_required, "split_csv"))
    if any(row["status"] == "fail" for row in rows):
        return rows

    positive_instances = positive_instance_count(manifest)
    rows.append(
        check(
            positive_instances >= min_positive_instances,
            "manifest_positive_instances_meet_floor",
            f"positive_instances={positive_instances} min={min_positive_instances}",
        )
    )
    rows.append(
        check(
            set(manifest["split"].astype(str)) == {expected_split},
            "manifest_split_matches_expected",
            f"observed={sorted(set(manifest['split'].astype(str)))} expected={expected_split}",
        )
    )
    rows.append(
        check(
            set(split["split"].astype(str)) == {expected_split},
            "split_csv_matches_expected_split",
            f"observed={sorted(set(split['split'].astype(str)))} expected={expected_split}",
        )
    )

    manifest_keys = set(zip(manifest["family"].astype(str), manifest["size"].astype(int), manifest["file_key"].astype(str)))
    split_keys = set(zip(split["family"].astype(str), split["size"].astype(int), split["file_key"].astype(str)))
    rows.append(
        check(
            manifest_keys.issubset(split_keys),
            "manifest_instances_subset_of_split",
            f"manifest_instances={len(manifest_keys)} split_instances={len(split_keys)}",
        )
    )
    split_row_ids = set(split["row_id"].astype(str))
    rows.append(
        check(
            set(manifest["row_id"].astype(str)).issubset(split_row_ids),
            "manifest_row_ids_subset_of_split",
            f"manifest_row_ids={manifest['row_id'].nunique()} split_row_ids={len(split_row_ids)}",
        )
    )
    missing_cnf = sum(1 for path in manifest["cnf_path"].astype(str) if not Path(path).exists())
    rows.append(check(missing_cnf == 0, "manifest_cnf_paths_exist", f"missing_cnf_paths={missing_cnf}"))

    expected_checkpoint_hash = file_sha256(checkpoint)
    rows.append(
        check(
            set(manifest["source_checkpoint"].astype(str)) == {str(checkpoint.resolve())}
            or set(manifest["source_checkpoint"].astype(str)) == {str(checkpoint)},
            "manifest_checkpoint_path_matches",
            f"expected={checkpoint}",
        )
    )
    rows.append(
        check(
            set(manifest["source_checkpoint_sha256"].astype(str)) == {expected_checkpoint_hash},
            "manifest_checkpoint_hash_matches",
            f"expected={expected_checkpoint_hash}",
        )
    )

    raw_paths = sorted(set(manifest["source_raw_csv"].astype(str)))
    missing_raw = [path for path in raw_paths if not Path(path).exists()]
    rows.append(check(not missing_raw, "manifest_raw_sources_exist", f"missing={missing_raw}"))
    raw_hash_mismatches = []
    for raw_path, raw_hash in sorted(set(zip(manifest["source_raw_csv"].astype(str), manifest["source_raw_sha256"].astype(str)))):
        path = Path(raw_path)
        if path.exists() and file_sha256(path) != raw_hash:
            raw_hash_mismatches.append(raw_path)
    rows.append(check(not raw_hash_mismatches, "manifest_raw_hashes_match", f"mismatches={raw_hash_mismatches}"))

    rank_counts = manifest.groupby(["family", "size", "file_key"], sort=True)["elite_rank_in_instance"].max()
    too_many = int((pd.to_numeric(rank_counts, errors="coerce") > max_per_instance).sum())
    rows.append(
        check(
            too_many == 0,
            "manifest_respects_max_per_instance",
            f"instances_over_limit={too_many} max_per_instance={max_per_instance}",
        )
    )
    sample_ids = pd.to_numeric(manifest["sample_id"], errors="coerce")
    num_samples = pd.to_numeric(manifest["num_samples_generated"], errors="coerce")
    invalid_sample_ids = int(((sample_ids < 0) | (sample_ids >= num_samples)).sum())
    rows.append(check(invalid_sample_ids == 0, "manifest_sample_ids_in_range", f"invalid={invalid_sample_ids}"))
    rows.append(
        check(
            manifest["Result"].astype(str).isin(SOLVED).all(),
            "manifest_rows_are_solved",
            f"unsolved_rows={int((~manifest['Result'].astype(str).isin(SOLVED)).sum())}",
        )
    )

    raw = load_raw_sources(manifest)
    rows.append(check(not raw.empty, "manifest_raw_sources_load", f"raw_rows={len(raw)}"))
    rows.extend(
        sampling_protocol_checks(
            raw=raw,
            expected_sample_seeds=expected_sample_seeds,
            expected_num_samples=expected_num_samples,
        )
    )
    rows.extend(raw_checkpoint_provenance_checks(raw=raw, checkpoint=checkpoint))
    missing_raw_instances = len(instance_keys(split) - instance_keys(raw))
    extra_raw_instances = len(instance_keys(raw) - instance_keys(split))
    rows.append(
        check(
            missing_raw_instances == 0 and extra_raw_instances == 0,
            "manifest_raw_sources_cover_split_exactly",
            f"missing_instances={missing_raw_instances} extra_instances={extra_raw_instances}",
        )
    )
    grid_issues = raw_sample_grid_issues(raw)
    rows.append(
        check(
            not grid_issues,
            "manifest_raw_sources_have_complete_sample_grid",
            f"issues={grid_issues[:5]} total_issues={len(grid_issues)}",
        )
    )
    raw_keys = solved_sample_keys(raw)
    missing_raw_samples = len(manifest_sample_keys(manifest) - raw_keys)
    rows.append(
        check(
            missing_raw_samples == 0,
            "manifest_rows_match_solved_raw_samples",
            f"missing_raw_samples={missing_raw_samples}",
        )
    )
    return rows


def config_value(config, key: str, default=""):
    current = config
    for part in key.split("."):
        if not hasattr(current, part):
            return default
        current = getattr(current, part)
    return current


def path_matches_config(observed: str, expected: Path) -> bool:
    if observed == str(expected):
        return True
    try:
        return Path(observed).resolve() == expected.resolve()
    except (OSError, RuntimeError):
        return False


def config_bool_value(config, key: str, default=False) -> bool:
    value = config_value(config, key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return bool(value)


def audit_training_config(
    config_path: Path,
    checkpoint: Path,
    train_manifest: Path | None,
    dev_manifest: Path | None,
    min_train_positive_instances: int,
    min_dev_positive_instances: int,
    expected_train_split: str = "residual_train",
    expected_dev_split: str = "residual_dev",
    expected_train_sample_seeds: str = "",
    expected_dev_sample_seeds: str = "",
    expected_train_num_samples: int = 0,
    expected_dev_num_samples: int = 0,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not config_path.exists():
        return [check(False, "training_config_exists", f"missing={config_path}")]
    rows.append(check(True, "training_config_exists", str(config_path)))
    config = OmegaConf.load(config_path)
    has_elite_replay = hasattr(config, "elite_replay")
    rows.append(check(has_elite_replay, "training_config_has_elite_replay", str(config_path)))
    if not has_elite_replay:
        return rows

    expected_checkpoint_hash = file_sha256(checkpoint) if checkpoint.exists() else ""
    observed_checkpoint_hash = str(config_value(config, "elite_replay.source_checkpoint_sha256"))
    rows.append(
        check(
            observed_checkpoint_hash == expected_checkpoint_hash,
            "training_config_checkpoint_hash_matches",
            f"observed={observed_checkpoint_hash} expected={expected_checkpoint_hash}",
        )
    )

    if train_manifest is not None:
        train = pd.read_csv(train_manifest) if train_manifest.exists() else pd.DataFrame()
        rows.append(check(train_manifest.exists(), "training_config_train_manifest_exists", str(train_manifest)))
        rows.append(
            check(
                path_matches_config(str(config_value(config, "elite_replay.train_manifest")), train_manifest),
                "training_config_train_manifest_path_matches",
                f"observed={config_value(config, 'elite_replay.train_manifest')} expected={train_manifest}",
            )
        )
        rows.append(
            check(
                str(config_value(config, "elite_replay.train_manifest_sha256")) == (file_sha256(train_manifest) if train_manifest.exists() else ""),
                "training_config_train_manifest_hash_matches",
                f"expected={file_sha256(train_manifest) if train_manifest.exists() else ''}",
            )
        )
        rows.append(
            check(
                int(config_value(config, "elite_replay.train_elite_rows", -1)) == len(train),
                "training_config_train_elite_rows_match",
                f"observed={config_value(config, 'elite_replay.train_elite_rows', -1)} expected={len(train)}",
            )
        )
        rows.append(
            check(
                int(config_value(config, "elite_replay.train_positive_instances", -1)) == positive_instance_count(train),
                "training_config_train_positive_instances_match",
                f"observed={config_value(config, 'elite_replay.train_positive_instances', -1)} expected={positive_instance_count(train)}",
            )
        )
    rows.append(
        check(
            int(config_value(config, "elite_replay.min_train_positive_instances", -1)) == min_train_positive_instances,
            "training_config_min_train_positive_floor_matches",
            f"observed={config_value(config, 'elite_replay.min_train_positive_instances', -1)} expected={min_train_positive_instances}",
        )
    )
    rows.append(
        check(
            str(config_value(config, "elite_replay.expected_train_split", "")) == expected_train_split,
            "training_config_expected_train_split_matches",
            f"observed={config_value(config, 'elite_replay.expected_train_split', '')} expected={expected_train_split}",
        )
    )
    rows.append(
        check(
            str(config_value(config, "elite_replay.expected_train_sample_seeds", "")) == expected_train_sample_seeds,
            "training_config_expected_train_sample_seeds_match",
            f"observed={config_value(config, 'elite_replay.expected_train_sample_seeds', '')} expected={expected_train_sample_seeds}",
        )
    )
    rows.append(
        check(
            int(config_value(config, "elite_replay.expected_train_num_samples", -1)) == int(expected_train_num_samples),
            "training_config_expected_train_num_samples_match",
            f"observed={config_value(config, 'elite_replay.expected_train_num_samples', -1)} expected={expected_train_num_samples}",
        )
    )

    if dev_manifest is not None:
        dev = pd.read_csv(dev_manifest) if dev_manifest.exists() else pd.DataFrame()
        rows.append(check(dev_manifest.exists(), "training_config_dev_manifest_exists", str(dev_manifest)))
        rows.append(
            check(
                path_matches_config(str(config_value(config, "elite_replay.dev_manifest")), dev_manifest),
                "training_config_dev_manifest_path_matches",
                f"observed={config_value(config, 'elite_replay.dev_manifest')} expected={dev_manifest}",
            )
        )
        rows.append(
            check(
                str(config_value(config, "elite_replay.dev_manifest_sha256")) == (file_sha256(dev_manifest) if dev_manifest.exists() else ""),
                "training_config_dev_manifest_hash_matches",
                f"expected={file_sha256(dev_manifest) if dev_manifest.exists() else ''}",
            )
        )
        rows.append(
            check(
                int(config_value(config, "elite_replay.dev_elite_rows", -1)) == len(dev),
                "training_config_dev_elite_rows_match",
                f"observed={config_value(config, 'elite_replay.dev_elite_rows', -1)} expected={len(dev)}",
            )
        )
        rows.append(
            check(
                int(config_value(config, "elite_replay.dev_positive_instances", -1)) == positive_instance_count(dev),
                "training_config_dev_positive_instances_match",
                f"observed={config_value(config, 'elite_replay.dev_positive_instances', -1)} expected={positive_instance_count(dev)}",
            )
        )
    rows.append(
        check(
            int(config_value(config, "elite_replay.min_dev_positive_instances", -1)) == min_dev_positive_instances,
            "training_config_min_dev_positive_floor_matches",
            f"observed={config_value(config, 'elite_replay.min_dev_positive_instances', -1)} expected={min_dev_positive_instances}",
        )
    )
    rows.append(
        check(
            str(config_value(config, "elite_replay.expected_dev_split", "")) == expected_dev_split,
            "training_config_expected_dev_split_matches",
            f"observed={config_value(config, 'elite_replay.expected_dev_split', '')} expected={expected_dev_split}",
        )
    )
    rows.append(
        check(
            str(config_value(config, "elite_replay.expected_dev_sample_seeds", "")) == expected_dev_sample_seeds,
            "training_config_expected_dev_sample_seeds_match",
            f"observed={config_value(config, 'elite_replay.expected_dev_sample_seeds', '')} expected={expected_dev_sample_seeds}",
        )
    )
    rows.append(
        check(
            int(config_value(config, "elite_replay.expected_dev_num_samples", -1)) == int(expected_dev_num_samples),
            "training_config_expected_dev_num_samples_match",
            f"observed={config_value(config, 'elite_replay.expected_dev_num_samples', -1)} expected={expected_dev_num_samples}",
        )
    )
    partial_training = config_bool_value(config, "elite_replay.allow_partial_manifest_training", False)
    limit_train_rows = int(config_value(config, "elite_replay.limit_train_rows", 0))
    limit_dev_rows = int(config_value(config, "elite_replay.limit_dev_rows", 0))
    rows.append(
        check(
            not partial_training,
            "training_config_disallows_partial_manifest_training",
            f"allow_partial_manifest_training={partial_training}",
        )
    )
    rows.append(
        check(
            limit_train_rows == 0 and limit_dev_rows == 0,
            "training_config_uses_full_manifests",
            f"limit_train_rows={limit_train_rows} limit_dev_rows={limit_dev_rows}",
        )
    )
    return rows


def write_doc(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Residual Elite Replay Manifest Audit",
        "",
        "This audit checks training/dev elite manifest readiness without running solvers.",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        detail = str(row["detail"]).replace("\n", " ")
        lines.append(f"| {row['check']} | {row['status']} | {detail} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit residual elite replay manifest readiness.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-csv", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--expected-split", required=True)
    parser.add_argument("--min-positive-instances", type=int, default=8)
    parser.add_argument("--max-per-instance", type=int, default=4)
    parser.add_argument("--expected-sample-seeds", default="")
    parser.add_argument("--expected-num-samples", type=int, default=0)
    parser.add_argument("--training-config", type=Path, default=None)
    parser.add_argument("--train-manifest", type=Path, default=None)
    parser.add_argument("--dev-manifest", type=Path, default=None)
    parser.add_argument("--min-train-positive-instances", type=int, default=0)
    parser.add_argument("--min-dev-positive-instances", type=int, default=0)
    parser.add_argument("--expected-train-split", default="residual_train")
    parser.add_argument("--expected-dev-split", default="residual_dev")
    parser.add_argument("--expected-train-sample-seeds", default="")
    parser.add_argument("--expected-dev-sample-seeds", default="")
    parser.add_argument("--expected-train-num-samples", type=int, default=0)
    parser.add_argument("--expected-dev-num-samples", type=int, default=0)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--doc", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = audit_manifest(
        manifest_path=args.manifest.resolve(),
        split_csv=args.split_csv.resolve(),
        checkpoint=args.checkpoint.resolve(),
        expected_split=args.expected_split,
        min_positive_instances=args.min_positive_instances,
        max_per_instance=args.max_per_instance,
        expected_sample_seeds=parse_expected_sample_seeds(args.expected_sample_seeds),
        expected_num_samples=int(args.expected_num_samples),
    )
    if args.training_config is not None:
        rows.extend(
            audit_training_config(
                config_path=args.training_config.resolve(),
                checkpoint=args.checkpoint.resolve(),
                train_manifest=args.train_manifest.resolve() if args.train_manifest else None,
                dev_manifest=args.dev_manifest.resolve() if args.dev_manifest else None,
                min_train_positive_instances=args.min_train_positive_instances,
                min_dev_positive_instances=args.min_dev_positive_instances,
                expected_train_split=args.expected_train_split,
                expected_dev_split=args.expected_dev_split,
                expected_train_sample_seeds=str(args.expected_train_sample_seeds),
                expected_dev_sample_seeds=str(args.expected_dev_sample_seeds),
                expected_train_num_samples=int(args.expected_train_num_samples),
                expected_dev_num_samples=int(args.expected_dev_num_samples),
            )
        )
    result = pd.DataFrame(rows)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_csv, index=False)
    if args.doc:
        write_doc(args.doc, rows)
    failures = int((result["status"] == "fail").sum()) if not result.empty else 0
    print(f"checks={len(result)} failures={failures}", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
