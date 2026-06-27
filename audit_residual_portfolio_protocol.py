from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}
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
UNRECORDED_ARTIFACT_VALUES = {"", "nan", "none", "null", "not-recorded", "not-provided", "missing"}


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


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def row_ids(frame: pd.DataFrame) -> set[str]:
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns for row ids: {sorted(missing)}")
    return {f"{row.family}:{int(row.size)}:{row.file_key}" for row in frame.itertuples(index=False)}


def row_cnf_path(row: pd.Series, cnf_root: Path | None) -> Path | None:
    if "cnf_path" in row and pd.notna(row["cnf_path"]):
        return Path(str(row["cnf_path"]))
    if "file" in row and pd.notna(row["file"]):
        return Path(str(row["file"]))
    if cnf_root is None:
        return None
    return cnf_root / str(row["family"]) / str(int(row["size"])) / str(row["file_key"])


def cnf_hashes(frame: pd.DataFrame, cnf_root: Path | None) -> set[str] | None:
    hashes = set()
    for _, row in frame.iterrows():
        path = row_cnf_path(row, cnf_root)
        if path is None or not path.exists():
            return None
        hashes.add(file_sha256(path))
    return hashes


def check(condition: bool, name: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def load_optional(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_record_path(value) -> Path | None:
    normalized = str(value).strip()
    if normalized.lower() in UNRECORDED_ARTIFACT_VALUES:
        return None
    path = Path(normalized)
    if path.is_absolute():
        return path
    return ROOT / path


def parse_record_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def audit_strong_gate(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return [check(False, "strong_combined_exists", f"missing: {path}")]
    frame = pd.read_csv(path)
    rows = [check(True, "strong_combined_exists", display_path(path))]
    rows.append(check("solved" in frame.columns, "strong_uses_strict_solved_column", "combined.csv must contain strict solved"))
    rows.append(
        check(
            "solved_after_nominal_limit" in frame.columns,
            "strong_reports_late_solves",
            "late solved rows must be reported, not folded into strict solved",
        )
    )
    if {"Result", "solved", "time", "nominal_limit"}.issubset(frame.columns):
        returned = frame["Result"].astype(str).isin(SOLVED)
        strict_expected = returned & pd.to_numeric(frame["time"], errors="coerce").le(
            pd.to_numeric(frame["nominal_limit"], errors="coerce")
        )
        strict_actual = parse_bool_series(frame["solved"], "solved")
        mismatches = int((strict_expected != strict_actual).sum())
        rows.append(check(mismatches == 0, "strong_strict60_consistent", f"mismatches={mismatches}"))
    return rows


def audit_candidate_manifest(
    manifest_path: Path | None,
    metadata_path: Path | None,
    expected_total: int | None,
    expected_generation_seed: int | None,
    expected_split_seed: int | None,
    require_files: bool,
) -> list[dict[str, str]]:
    if manifest_path is None:
        return [check(True, "candidate_manifest_not_requested", "no candidate manifest path provided")]
    if not manifest_path.exists():
        return [check(False, "candidate_manifest_exists", f"missing: {manifest_path}")]
    manifest = pd.read_csv(manifest_path)
    rows = [check(True, "candidate_manifest_exists", display_path(manifest_path))]
    required = {"family", "size", "file_key", "cnf_path", "row_id", "split"}
    missing = required - set(manifest.columns)
    rows.append(check(not missing, "candidate_manifest_has_required_columns", f"missing={sorted(missing)}"))
    required_splits = {"candidate_train", "candidate_dev", "candidate_heldout"}
    splits = set(manifest.get("split", pd.Series(dtype=str)).astype(str))
    rows.append(check(required_splits.issubset(splits), "candidate_has_train_dev_heldout", f"splits={sorted(splits)}"))
    duplicate_ids = int(manifest.get("row_id", pd.Series(dtype=str)).duplicated().sum()) if "row_id" in manifest else -1
    rows.append(check(duplicate_ids == 0, "candidate_row_ids_unique", f"duplicates={duplicate_ids}"))
    if expected_total is not None:
        rows.append(
            check(
                int(len(manifest)) == int(expected_total),
                "candidate_total_matches_expected",
                f"expected={expected_total} observed={len(manifest)}",
            )
        )
    missing_files = 0
    if "cnf_path" in manifest:
        for path in manifest["cnf_path"].astype(str):
            if not Path(path).exists():
                missing_files += 1
    rows.append(
        check(
            missing_files == 0 or not require_files,
            "candidate_cnf_files_exist",
            f"missing_files={missing_files} require_files={require_files}",
        )
    )

    if metadata_path is None:
        rows.append(check(False, "candidate_metadata_provided", "missing --candidate-metadata"))
        return rows
    if not metadata_path.exists():
        rows.append(check(False, "candidate_metadata_exists", f"missing: {metadata_path}"))
        return rows
    rows.append(check(True, "candidate_metadata_exists", display_path(metadata_path)))
    with metadata_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    rows.append(check(metadata.get("kind") == "full_candidate_split", "candidate_metadata_kind", f"kind={metadata.get('kind')}"))
    rows.append(
        check(
            int(metadata.get("manifest_rows", -1)) == int(len(manifest)),
            "candidate_metadata_manifest_rows_match",
            f"metadata={metadata.get('manifest_rows')} manifest={len(manifest)}",
        )
    )
    actual_manifest_hash = file_sha256(manifest_path)
    rows.append(
        check(
            metadata.get("manifest_sha256") == actual_manifest_hash,
            "candidate_metadata_manifest_hash_match",
            f"metadata={metadata.get('manifest_sha256')} actual={actual_manifest_hash}",
        )
    )
    expected_counts = {str(split): int(count) for split, count in manifest.groupby("split", sort=True).size().items()}
    rows.append(
        check(
            metadata.get("split_counts") == expected_counts,
            "candidate_metadata_split_counts_match",
            f"metadata={metadata.get('split_counts')} manifest={expected_counts}",
        )
    )
    if expected_generation_seed is not None:
        rows.append(
            check(
                int(metadata.get("generation_seed", -1)) == int(expected_generation_seed),
                "candidate_generation_seed_matches_expected",
                f"expected={expected_generation_seed} metadata={metadata.get('generation_seed')}",
            )
        )
    if expected_split_seed is not None:
        rows.append(
            check(
                int(metadata.get("split_seed", -1)) == int(expected_split_seed),
                "candidate_split_seed_matches_expected",
                f"expected={expected_split_seed} metadata={metadata.get('split_seed')}",
            )
        )
    rows.append(
        check(
            "missing_files" in metadata,
            "candidate_metadata_records_missing_files_at_write",
            f"metadata_at_write={metadata.get('missing_files')} observed_now={missing_files}",
        )
    )
    return rows


def audit_split_metadata(
    manifest: pd.DataFrame,
    metadata_path: Path | None,
    input_csv: Path | None,
    excluded_csv: Path | None,
    candidate_manifest_csv: Path | None,
) -> list[dict[str, str]]:
    if metadata_path is None:
        return [check(False, "split_metadata_provided", "missing --split-metadata")]
    if not metadata_path.exists():
        return [check(False, "split_metadata_exists", f"missing: {metadata_path}")]
    rows = [check(True, "split_metadata_exists", display_path(metadata_path))]
    with metadata_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    rows.append(
        check(
            int(metadata.get("manifest_rows", -1)) == int(len(manifest)),
            "split_metadata_manifest_rows_match",
            f"metadata={metadata.get('manifest_rows')} manifest={len(manifest)}",
        )
    )
    expected_counts = {str(split): int(count) for split, count in manifest.groupby("split", sort=True).size().items()}
    rows.append(
        check(
            metadata.get("split_counts") == expected_counts,
            "split_metadata_counts_match",
            f"metadata={metadata.get('split_counts')} manifest={expected_counts}",
        )
    )
    if input_csv is not None and input_csv.exists():
        actual_hash = file_sha256(input_csv)
        rows.append(
            check(
                metadata.get("input_sha256") == actual_hash,
                "split_metadata_input_hash_match",
                f"metadata={metadata.get('input_sha256')} actual={actual_hash}",
            )
        )
    else:
        rows.append(check(False, "split_metadata_input_hash_match", f"missing input csv: {input_csv}"))
    if excluded_csv is not None and excluded_csv.exists():
        actual_exclude_hash = file_sha256(excluded_csv)
        rows.append(
            check(
                metadata.get("exclude_sha256") == actual_exclude_hash,
                "split_metadata_exclude_hash_match",
                f"metadata={metadata.get('exclude_sha256')} actual={actual_exclude_hash}",
            )
        )
    if candidate_manifest_csv is not None:
        if candidate_manifest_csv.exists():
            actual_candidate_hash = file_sha256(candidate_manifest_csv)
            rows.append(
                check(
                    metadata.get("candidate_manifest_sha256") == actual_candidate_hash,
                    "split_metadata_candidate_manifest_hash_match",
                    f"metadata={metadata.get('candidate_manifest_sha256')} actual={actual_candidate_hash}",
                )
            )
            rows.append(
                check(
                    metadata.get("split_source") == "candidate_manifest",
                    "split_metadata_uses_candidate_manifest",
                    f"split_source={metadata.get('split_source')}",
                )
            )
        else:
            rows.append(
                check(
                    False,
                    "split_metadata_candidate_manifest_hash_match",
                    f"missing candidate manifest: {candidate_manifest_csv}",
                )
            )
    return rows


def audit_split(
    manifest_path: Path | None,
    excluded_csv: Path | None,
    exclude_cnf_root: Path | None,
    split_metadata_path: Path | None,
    split_input_csv: Path | None,
    candidate_manifest_csv: Path | None,
) -> list[dict[str, str]]:
    if manifest_path is None:
        return [check(True, "split_manifest_not_requested", "no split manifest path provided")]
    if not manifest_path.exists():
        return [check(False, "split_manifest_exists", f"missing: {manifest_path}")]
    manifest = pd.read_csv(manifest_path)
    rows = [check(True, "split_manifest_exists", display_path(manifest_path))]
    required_splits = {"residual_train", "residual_dev", "residual_heldout"}
    splits = set(manifest.get("split", pd.Series(dtype=str)).astype(str))
    rows.append(check(required_splits.issubset(splits), "split_has_train_dev_heldout", f"splits={sorted(splits)}"))
    split_ids = {}
    for split, group in manifest.groupby("split"):
        split_ids[str(split)] = row_ids(group)
    overlap_count = 0
    split_names = sorted(split_ids)
    for i, left in enumerate(split_names):
        for right in split_names[i + 1 :]:
            overlap_count += len(split_ids[left] & split_ids[right])
    rows.append(check(overlap_count == 0, "splits_are_disjoint", f"overlap_rows={overlap_count}"))
    if excluded_csv is not None and excluded_csv.exists():
        excluded = pd.read_csv(excluded_csv)
        manifest_hashes = cnf_hashes(manifest, cnf_root=None)
        excluded_hashes = cnf_hashes(excluded, cnf_root=exclude_cnf_root)
        if manifest_hashes is not None and excluded_hashes is not None:
            excluded_overlap = len(manifest_hashes & excluded_hashes)
            rows.append(
                check(
                    excluded_overlap == 0,
                    "pilot_excluded_from_split",
                    f"overlap_cnf_sha256={excluded_overlap}",
                )
            )
        else:
            excluded_overlap = len(row_ids(manifest) & row_ids(excluded))
            rows.append(
                check(
                    excluded_overlap == 0,
                    "pilot_excluded_from_split",
                    f"overlap_rows={excluded_overlap} hash_check=unavailable",
                )
            )
    else:
        rows.append(check(False, "pilot_excluded_from_split", f"missing exclude csv: {excluded_csv}"))
    if candidate_manifest_csv is not None and candidate_manifest_csv.exists():
        candidate = pd.read_csv(candidate_manifest_csv)
        required = {"family", "size", "file_key", "split"}
        missing = required - set(candidate.columns)
        if missing:
            rows.append(check(False, "residual_split_projects_candidate_split", f"missing candidate columns={sorted(missing)}"))
        else:
            split_for = {
                f"{row.family}:{int(row.size)}:{row.file_key}": str(row.split).replace("candidate_", "residual_", 1)
                for row in candidate.itertuples(index=False)
            }
            bad_rows = 0
            missing_rows = 0
            for row in manifest.itertuples(index=False):
                row_id = f"{row.family}:{int(row.size)}:{row.file_key}"
                expected = split_for.get(row_id)
                if expected is None:
                    missing_rows += 1
                elif str(row.split) != expected:
                    bad_rows += 1
            rows.append(
                check(
                    bad_rows == 0 and missing_rows == 0,
                    "residual_split_projects_candidate_split",
                    f"bad_rows={bad_rows} missing_rows={missing_rows}",
                )
            )
    elif candidate_manifest_csv is not None:
        rows.append(check(False, "residual_split_projects_candidate_split", f"missing: {candidate_manifest_csv}"))
    rows.extend(
        audit_split_metadata(
            manifest=manifest,
            metadata_path=split_metadata_path,
            input_csv=split_input_csv,
            excluded_csv=excluded_csv,
            candidate_manifest_csv=candidate_manifest_csv,
        )
    )
    return rows


def audit_selector_spec(neural: pd.DataFrame, selector_spec_path: Path | None) -> list[dict[str, str]]:
    if selector_spec_path is None:
        return [check(False, "selector_spec_provided", "missing --selector-spec for held-out neural run")]
    if not selector_spec_path.exists():
        return [check(False, "selector_spec_exists", f"missing: {selector_spec_path}")]
    rows = [check(True, "selector_spec_exists", display_path(selector_spec_path))]
    with selector_spec_path.open(encoding="utf-8") as handle:
        spec = json.load(handle)
    required_keys = {
        "checkpoint",
        "policy",
        "top_k",
        "probe_cpu_lim",
        "full_cpu_lim",
        "num_samples",
        "sample_seeds",
        "solver_seed",
        "probe_solved_cap",
    }
    missing = required_keys - set(spec)
    rows.append(check(not missing, "selector_spec_has_required_fields", f"missing={sorted(missing)}"))
    source = str(spec.get("selector_spec_source", ""))
    rows.append(
        check(
            bool(source),
            "selector_spec_reports_source",
            f"selector_spec_source={source or 'missing'}",
        )
    )
    if source:
        source_spec: dict | None = None
        rows.append(
            check(
                "dev" in source.lower() and "heldout" not in source.lower(),
                "selector_spec_source_is_dev",
                f"selector_spec_source={source}",
            )
        )
        source_split = str(spec.get("selector_spec_source_split", "")).lower()
        rows.append(
            check(
                source_split == "dev",
                "selector_spec_source_split_is_dev",
                f"selector_spec_source_split={spec.get('selector_spec_source_split', 'missing')}",
            )
        )
        if "selector_spec_source_sha256" in spec:
            source_path = Path(source)
            if not source_path.is_absolute():
                source_path = ROOT / source_path
            if source_path.exists():
                actual_hash = file_sha256(source_path)
                expected_hash = str(spec["selector_spec_source_sha256"])
                rows.append(
                    check(
                        expected_hash == actual_hash,
                        "selector_spec_source_hash_matches",
                        f"expected={expected_hash} actual={actual_hash}",
                    )
                )
                with source_path.open(encoding="utf-8") as handle:
                    source_spec = json.load(handle)
            else:
                rows.append(
                    check(False, "selector_spec_source_hash_matches", f"missing source selector spec: {source_path}")
                )
        else:
            rows.append(check(False, "selector_spec_source_hash_matches", "missing selector_spec_source_sha256"))
        if source_spec is not None and "checkpoint_sha256" in source_spec:
            observed_checkpoint_hash = str(spec.get("checkpoint_sha256", ""))
            expected_checkpoint_hash = str(source_spec.get("checkpoint_sha256", ""))
            rows.append(
                check(
                    bool(observed_checkpoint_hash) and observed_checkpoint_hash == expected_checkpoint_hash,
                    "selector_spec_checkpoint_hash_matches_source",
                    f"observed={observed_checkpoint_hash or 'missing'} expected={expected_checkpoint_hash or 'missing'}",
                )
            )
        elif source_spec is not None:
            rows.append(
                check(
                    False,
                    "selector_spec_checkpoint_hash_matches_source",
                    "source selector spec missing checkpoint_sha256",
                )
            )
    kind = str(spec.get("kind", ""))
    rows.append(
        check(
            kind == "fixed_early_trace_neural_selector",
            "selector_spec_kind",
            f"kind={kind}",
        )
    )
    if missing or neural.empty:
        return rows

    checks = [
        ("selector_policy", "policy", str),
        ("top_k", "top_k", int),
        ("probe_cpu_lim", "probe_cpu_lim", float),
        ("num_samples_generated", "num_samples", int),
        ("solver_seed", "solver_seed", int),
    ]
    if "adaptive_top_k_a" in spec:
        checks.append(("adaptive_top_k_a", "adaptive_top_k_a", int))
    if "adaptive_top_k_b" in spec:
        checks.append(("adaptive_top_k_b", "adaptive_top_k_b", int))
    if "probe_solved_cap" in spec:
        checks.append(("probe_solved_cap", "probe_solved_cap", int))
    if "full_cpu_lim" in neural.columns:
        checks.append(("full_cpu_lim", "full_cpu_lim", float))
    for column, key, cast in checks:
        if column not in neural.columns:
            rows.append(check(False, f"selector_spec_matches_{column}", f"missing neural column {column}"))
            continue
        values = {cast(value) for value in neural[column].dropna().unique()}
        expected = cast(spec[key])
        rows.append(
            check(
                values == {expected},
                f"selector_spec_matches_{column}",
                f"expected={expected} observed={sorted(values)}",
            )
        )
    if "sample_seed" in neural.columns:
        observed_seeds = {int(value) for value in neural["sample_seed"].dropna().unique()}
        expected_seeds = {int(value) for value in spec["sample_seeds"]}
        rows.append(
            check(
                observed_seeds.issubset(expected_seeds),
                "selector_spec_matches_sample_seeds",
                f"expected={sorted(expected_seeds)} observed={sorted(observed_seeds)}",
            )
        )
    else:
        rows.append(check(False, "selector_spec_matches_sample_seeds", "missing neural column sample_seed"))
    for column, key in [("adaptive_threshold_a", "adaptive_threshold_a"), ("adaptive_threshold_b", "adaptive_threshold_b")]:
        expected = spec.get(key)
        if expected is None:
            continue
        if column not in neural.columns:
            rows.append(check(False, f"selector_spec_matches_{column}", f"missing neural column {column}"))
            continue
        values = {float(value) for value in neural[column].dropna().unique()}
        rows.append(
            check(
                values == {float(expected)},
                f"selector_spec_matches_{column}",
                f"expected={float(expected)} observed={sorted(values)}",
            )
        )
    if {"selector_rule", "effective_top_k", "probe_solved_samples", "max_probe_deadends"}.issubset(neural.columns):
        bad_rows = 0
        for row in neural.itertuples(index=False):
            probe_solved = int(getattr(row, "probe_solved_samples"))
            max_deadends = float(getattr(row, "max_probe_deadends"))
            effective_top_k = int(getattr(row, "effective_top_k"))
            selector_rule = str(getattr(row, "selector_rule"))
            default_top_k = int(spec["top_k"])
            threshold_a = spec.get("adaptive_threshold_a")
            threshold_b = spec.get("adaptive_threshold_b")
            if threshold_a is None or threshold_b is None:
                expected_rule = "fixed_top_k"
                expected_top_k = default_top_k
            elif probe_solved > 0:
                expected_rule = "probe_solved_first"
                expected_top_k = 0
            elif max_deadends >= float(threshold_a):
                expected_rule = "adaptive_top_k_a"
                expected_top_k = int(spec.get("adaptive_top_k_a", 8))
            elif max_deadends >= float(threshold_b):
                expected_rule = "adaptive_top_k_b"
                expected_top_k = int(spec.get("adaptive_top_k_b", 4))
            else:
                expected_rule = "adaptive_default_top_k"
                expected_top_k = default_top_k
            if selector_rule != expected_rule or effective_top_k != expected_top_k:
                bad_rows += 1
        rows.append(check(bad_rows == 0, "selector_spec_recomputes_effective_top_k", f"bad_rows={bad_rows}"))
    else:
        rows.append(
            check(
                False,
                "selector_spec_recomputes_effective_top_k",
                "missing selector_rule/effective_top_k/probe_solved_samples/max_probe_deadends",
            )
        )
    return rows


def audit_neural_budget_fields(neural: pd.DataFrame) -> list[dict[str, str]]:
    rows = []
    required_columns = {
        "probe_cpu_total": "neural summary should include allocated probe CPU",
        "full_cpu_capped": "neural summary should include capped selected full-run CPU",
        "total_cpu_allocated": "neural summary should include total allocated CPU for same-budget controls",
        "full_cpu_allocated": "neural summary should include allocated selected full-run CPU",
        "neural_generation_wall_time": "neural summary should include GNN/sample generation wall-clock overhead",
        "probe_wall_time_total": "neural summary should include probe wall-clock overhead",
        "full_wall_time_total": "neural summary should include selected full-run wall-clock time",
        "total_wall_time": "neural summary should include total residual wall-clock time",
    }
    for column, detail in required_columns.items():
        rows.append(check(column in neural.columns, f"heldout_neural_reports_{column}", detail))
    if {"neural_generation_wall_time", "probe_wall_time_total", "full_wall_time_total", "total_wall_time"}.issubset(
        neural.columns
    ):
        expected = (
            pd.to_numeric(neural["neural_generation_wall_time"], errors="coerce").fillna(0.0)
            + pd.to_numeric(neural["probe_wall_time_total"], errors="coerce").fillna(0.0)
            + pd.to_numeric(neural["full_wall_time_total"], errors="coerce").fillna(0.0)
        )
        actual = pd.to_numeric(neural["total_wall_time"], errors="coerce")
        bad_rows = int((actual.sub(expected).abs() > 1e-6).sum())
        rows.append(check(bad_rows == 0, "heldout_neural_total_wall_time_consistent", f"bad_rows={bad_rows}"))
    return rows


def parse_schedule_entries(raw: str) -> list[tuple[str, float]]:
    entries = []
    for part in str(raw).split(","):
        item = part.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid schedule entry: {item!r}")
        solver, limit_raw = item.split(":", 1)
        entries.append((solver.strip(), float(limit_raw)))
    return entries


def format_schedule(entries: list[tuple[str, float]]) -> str:
    return ",".join(f"{solver}:{limit:g}" for solver, limit in entries)


def schedule_from_budget(total_budget: float, solver_cycle: list[str], attempt_limit: float) -> list[tuple[str, float]]:
    if total_budget <= 0 or attempt_limit <= 0 or not solver_cycle:
        return []
    entries = []
    remaining = float(total_budget)
    idx = 0
    while remaining > 1e-9:
        solver = solver_cycle[idx % len(solver_cycle)]
        limit = min(float(attempt_limit), remaining)
        entries.append((solver, limit))
        remaining -= limit
        idx += 1
    return entries


def audit_non_neural_schedule(non_neural: pd.DataFrame, schedule_path: Path | None) -> list[dict[str, str]]:
    if schedule_path is None:
        return [check(True, "non_neural_schedule_not_requested", "no non-neural schedule artifact provided")]
    if not schedule_path.exists():
        return [check(False, "non_neural_schedule_exists", f"missing: {schedule_path}")]
    rows = [check(True, "non_neural_schedule_exists", display_path(schedule_path))]
    schedule_frame = pd.read_csv(schedule_path)
    if "schedule" not in schedule_frame.columns or schedule_frame.empty:
        rows.append(check(False, "non_neural_schedule_has_value", "missing schedule column or empty artifact"))
        return rows
    rows.append(
        check(
            "neural_summary" in schedule_frame.columns,
            "non_neural_schedule_reports_source",
            "schedule artifact should report the dev neural summary source",
        )
    )
    rows.append(
        check(
            "source_split" in schedule_frame.columns,
            "non_neural_schedule_reports_source_split",
            "schedule artifact must explicitly record the split used to derive the budget",
        )
    )
    if "source_split" in schedule_frame.columns:
        source_split = str(schedule_frame.iloc[0]["source_split"]).lower()
        rows.append(
            check(
                source_split == "dev",
                "non_neural_schedule_source_split_is_dev",
                f"source_split={schedule_frame.iloc[0]['source_split']}",
            )
        )
    if "neural_summary" in schedule_frame.columns:
        source = str(schedule_frame.iloc[0]["neural_summary"]).lower()
        rows.append(
            check(
                "heldout" not in source,
                "non_neural_schedule_not_from_heldout",
                f"source={schedule_frame.iloc[0]['neural_summary']}",
            )
        )
        source_path = Path(str(schedule_frame.iloc[0]["neural_summary"]))
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        if "neural_summary_sha256" in schedule_frame.columns:
            if source_path.exists():
                actual_hash = file_sha256(source_path)
                expected_hash = str(schedule_frame.iloc[0]["neural_summary_sha256"])
                rows.append(
                    check(
                        expected_hash == actual_hash,
                        "non_neural_schedule_source_hash_matches",
                        f"expected={expected_hash} actual={actual_hash}",
                    )
                )
            else:
                rows.append(
                    check(
                        False,
                        "non_neural_schedule_source_hash_matches",
                        f"missing source neural summary: {source_path}",
                    )
                )
        else:
            rows.append(
                check(
                    False,
                    "non_neural_schedule_source_hash_matches",
                    "missing neural_summary_sha256 column",
                )
            )
    expected = str(schedule_frame.iloc[0]["schedule"])
    entries = [entry.strip() for entry in expected.split(",") if entry.strip()]
    solver_names = [entry.split(":", 1)[0].strip() for entry in entries]
    has_march = any(name == "march" for name in solver_names)
    cadical_names = {name for name in solver_names if name.startswith("cadical")}
    has_cadical_variant = any(name != "cadical" for name in cadical_names)
    rows.append(
        check(
            has_march,
            "non_neural_schedule_contains_march",
            f"solvers={solver_names}",
        )
    )
    rows.append(
        check(
            bool(cadical_names),
            "non_neural_schedule_contains_cadical",
            f"solvers={solver_names}",
        )
    )
    rows.append(
        check(
            has_cadical_variant,
            "non_neural_schedule_contains_cadical_variant",
            f"cadical_solvers={sorted(cadical_names)}",
        )
    )
    if "schedule" not in non_neural.columns:
        rows.append(check(False, "non_neural_schedule_matches_artifact", "missing non-neural summary schedule column"))
        return rows
    observed = {str(value) for value in non_neural["schedule"].dropna().unique()}
    mode_values = {str(value) for value in non_neural.get("schedule_mode", pd.Series(dtype=str)).dropna().unique()}
    if "per_instance" in mode_values:
        if {"solver_cycle", "attempt_limit"}.issubset(schedule_frame.columns):
            solver_cycle = [
                part.strip()
                for part in str(schedule_frame.iloc[0]["solver_cycle"]).split(",")
                if part.strip()
            ]
            attempt_limit = float(schedule_frame.iloc[0]["attempt_limit"])
            if "budget_cpu_total" in non_neural.columns:
                bad_rows = 0
                for row in non_neural.itertuples(index=False):
                    budget = float(getattr(row, "budget_cpu_total"))
                    observed_schedule = str(getattr(row, "schedule"))
                    expected_schedule = format_schedule(
                        schedule_from_budget(
                            total_budget=budget,
                            solver_cycle=solver_cycle,
                            attempt_limit=attempt_limit,
                        )
                    )
                    if observed_schedule != expected_schedule:
                        bad_rows += 1
                rows.append(
                    check(
                        bad_rows == 0,
                        "non_neural_per_instance_schedules_follow_frozen_cycle",
                        f"bad_rows={bad_rows} solver_cycle={solver_cycle} attempt_limit={attempt_limit:g}",
                    )
                )
            else:
                rows.append(
                    check(
                        False,
                        "non_neural_per_instance_schedules_follow_frozen_cycle",
                        "missing non-neural budget_cpu_total column",
                    )
                )
        else:
            rows.append(
                check(
                    False,
                    "non_neural_per_instance_schedules_follow_frozen_cycle",
                    "schedule artifact missing solver_cycle or attempt_limit",
                )
            )
        rows.append(
            check(
                bool(observed),
                "non_neural_schedule_matches_artifact",
                f"per_instance schedules derived from frozen cycle; observed_count={len(observed)}",
            )
        )
    else:
        rows.append(
            check(
                observed == {expected},
                "non_neural_schedule_matches_artifact",
                f"expected={expected} observed={sorted(observed)}",
            )
        )
    return rows


def audit_non_neural_run_schedule_source(out_schedule_path: Path | None, schedule_path: Path | None) -> list[dict[str, str]]:
    if out_schedule_path is None:
        return [check(True, "non_neural_run_schedule_source_not_requested", "no non-neural run schedule.csv provided")]
    if not out_schedule_path.exists():
        return [check(False, "non_neural_run_schedule_source_exists", f"missing: {out_schedule_path}")]
    rows = [check(True, "non_neural_run_schedule_source_exists", display_path(out_schedule_path))]
    frame = pd.read_csv(out_schedule_path)
    if "schedule_source" not in frame.columns:
        rows.append(check(False, "non_neural_run_schedule_source_recorded", "missing schedule_source column"))
        return rows
    if schedule_path is None:
        rows.append(check(True, "non_neural_run_schedule_source_recorded", "schedule_source recorded"))
        return rows
    expected = display_path(schedule_path.resolve())
    observed = {str(value) for value in frame["schedule_source"].dropna().unique()}
    rows.append(
        check(
            observed == {expected},
            "non_neural_run_schedule_source_matches",
            f"expected={expected} observed={sorted(observed)}",
        )
    )
    return rows


def audit_gate_record(
    gate_record_path: Path | None,
    selector_spec_path: Path | None,
    require_gate_pass: bool,
) -> list[dict[str, str]]:
    if gate_record_path is None:
        return [
            check(
                not require_gate_pass,
                "gate_record_provided",
                "missing --gate-record",
            )
        ]
    if not gate_record_path.exists():
        return [check(False, "gate_record_exists", f"missing: {gate_record_path}")]
    rows = [check(True, "gate_record_exists", display_path(gate_record_path))]
    with gate_record_path.open(encoding="utf-8") as handle:
        record = json.load(handle)
    rows.append(
        check(
            str(record.get("kind", "")) == "residual_portfolio_gate_decision",
            "gate_record_kind",
            f"kind={record.get('kind')}",
        )
    )
    rows.append(
        check(
            str(record.get("decision", "")) == "pass",
            "gate_record_decision_pass",
            f"decision={record.get('decision')}",
        )
    )
    rows.append(
        check(
            record.get("allow_diagnostic_total") is False,
            "gate_record_not_diagnostic_total",
            f"allow_diagnostic_total={record.get('allow_diagnostic_total', 'missing')}",
        )
    )
    total = parse_record_int(record.get("total"))
    expected_total = parse_record_int(record.get("expected_total"))
    oracle_solved = parse_record_int(record.get("oracle_solved"))
    pass_min = parse_record_int(record.get("pass_min"))
    rows.append(
        check(
            total is not None
            and expected_total is not None
            and oracle_solved is not None
            and pass_min is not None,
            "gate_record_numeric_fields_parseable",
            "total={total} expected_total={expected_total} oracle_solved={oracle_solved} pass_min={pass_min}".format(
                total=record.get("total", "missing"),
                expected_total=record.get("expected_total", "missing"),
                oracle_solved=record.get("oracle_solved", "missing"),
                pass_min=record.get("pass_min", "missing"),
            ),
        )
    )
    rows.append(
        check(
            total is not None and expected_total is not None and total == expected_total and total > 0,
            "gate_record_denominator_matches",
            f"total={total} expected_total={expected_total}",
        )
    )
    rows.append(
        check(
            oracle_solved is not None and pass_min is not None and oracle_solved >= pass_min,
            "gate_record_oracle_solved_meets_pass_min",
            f"oracle_solved={oracle_solved} pass_min={pass_min}",
        )
    )

    source_path = resolve_record_path(record.get("source", ""))
    rows.append(
        check(
            source_path is not None or not require_gate_pass,
            "gate_record_oracle_source_provided",
            f"source={record.get('source', 'missing')}",
        )
    )
    oracle = pd.DataFrame()
    if source_path is not None:
        rows.append(
            check(
                source_path.exists(),
                "gate_record_oracle_source_exists",
                display_path(source_path) if source_path.exists() else f"missing: {source_path}",
            )
        )
        expected_hash = str(record.get("source_sha256", "")).strip()
        if source_path.exists():
            actual_hash = file_sha256(source_path)
            rows.append(
                check(
                    bool(expected_hash) and expected_hash == actual_hash,
                    "gate_record_oracle_source_hash_matches",
                    f"expected={expected_hash or 'missing'} actual={actual_hash}",
                )
            )
            try:
                oracle = pd.read_csv(source_path)
                oracle_missing = sorted({"family", "size", "file_key", "solved_any"} - set(oracle.columns))
                rows.append(
                    check(
                        not oracle_missing,
                        "gate_record_oracle_source_has_required_columns",
                        f"missing={oracle_missing}",
                    )
                )
                if not oracle_missing:
                    duplicate_keys = int(oracle.duplicated(["family", "size", "file_key"]).sum())
                    solved_any = parse_bool_series(oracle["solved_any"], "solved_any")
                    rows.append(
                        check(
                            duplicate_keys == 0,
                            "gate_record_oracle_source_instance_keys_unique",
                            f"duplicates={duplicate_keys}",
                        )
                    )
                    rows.append(
                        check(
                            total is not None and int(len(oracle)) == total,
                            "gate_record_oracle_source_total_matches_record",
                            f"source_total={len(oracle)} record_total={total}",
                        )
                    )
                    rows.append(
                        check(
                            oracle_solved is not None and int(solved_any.sum()) == oracle_solved,
                            "gate_record_oracle_source_solved_matches_record",
                            f"source_solved={int(solved_any.sum())} record_solved={oracle_solved}",
                        )
                    )
            except Exception as exc:
                rows.append(
                    check(
                        False,
                        "gate_record_oracle_source_parseable",
                        f"{type(exc).__name__}: {exc}",
                    )
                )
        else:
            rows.append(check(False, "gate_record_oracle_source_hash_matches", f"missing: {source_path}"))

    checkpoint_path = resolve_record_path(record.get("checkpoint", ""))
    rows.append(
        check(
            checkpoint_path is not None or not require_gate_pass,
            "gate_record_checkpoint_provided",
            f"checkpoint={record.get('checkpoint', 'missing')}",
        )
    )
    checkpoint_hash = ""
    if checkpoint_path is not None:
        rows.append(
            check(
                checkpoint_path.exists(),
                "gate_record_checkpoint_exists",
                display_path(checkpoint_path) if checkpoint_path.exists() else f"missing: {checkpoint_path}",
            )
        )
        expected_hash = str(record.get("checkpoint_sha256", "")).strip()
        if checkpoint_path.exists():
            checkpoint_hash = file_sha256(checkpoint_path)
            rows.append(
                check(
                    bool(expected_hash) and expected_hash == checkpoint_hash,
                    "gate_record_checkpoint_hash_matches",
                    f"expected={expected_hash or 'missing'} actual={checkpoint_hash}",
                )
            )
        else:
            rows.append(check(False, "gate_record_checkpoint_hash_matches", f"missing: {checkpoint_path}"))
    if require_gate_pass:
        rows.append(
            check(
                str(record.get("oracle_checkpoint_provenance_check", "")) == "pass",
                "gate_record_oracle_checkpoint_provenance_pass",
                f"oracle_checkpoint_provenance_check={record.get('oracle_checkpoint_provenance_check', 'missing')}",
            )
        )
    if not oracle.empty and checkpoint_hash:
        observed_checkpoint_hashes: set[str] = set()
        if "source_checkpoint_sha256" in oracle.columns:
            observed_checkpoint_hashes = {
                str(value).strip()
                for value in oracle["source_checkpoint_sha256"].dropna()
                if str(value).strip()
            }
        rows.append(
            check(
                observed_checkpoint_hashes == {checkpoint_hash},
                "gate_record_oracle_source_checkpoint_hash_matches",
                f"source_hashes={sorted(observed_checkpoint_hashes)} checkpoint={checkpoint_hash}",
            )
        )

    training_config_audit_path = resolve_record_path(record.get("training_config_audit", ""))
    rows.append(
        check(
            training_config_audit_path is not None or not require_gate_pass,
            "gate_record_training_config_audit_provided",
            f"training_config_audit={record.get('training_config_audit', 'missing')}",
        )
    )
    recorded_training_checks = parse_record_int(record.get("training_config_audit_checks"))
    recorded_training_failures = parse_record_int(record.get("training_config_audit_failures"))
    rows.append(
        check(
            recorded_training_checks is not None
            and recorded_training_checks >= len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
            "gate_record_training_config_audit_checks_recorded",
            f"recorded={record.get('training_config_audit_checks', 'missing')} required_min={len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)}",
        )
    )
    rows.append(
        check(
            recorded_training_failures == 0,
            "gate_record_training_config_audit_failures_zero",
            f"recorded={record.get('training_config_audit_failures', 'missing')}",
        )
    )
    if training_config_audit_path is not None:
        rows.append(
            check(
                training_config_audit_path.exists(),
                "gate_record_training_config_audit_exists",
                display_path(training_config_audit_path)
                if training_config_audit_path.exists()
                else f"missing: {training_config_audit_path}",
            )
        )
        expected_hash = str(record.get("training_config_audit_sha256", "")).strip()
        if training_config_audit_path.exists():
            actual_hash = file_sha256(training_config_audit_path)
            rows.append(
                check(
                    bool(expected_hash) and expected_hash == actual_hash,
                    "gate_record_training_config_audit_hash_matches",
                    f"expected={expected_hash or 'missing'} actual={actual_hash}",
                )
            )
            try:
                audit = pd.read_csv(training_config_audit_path)
                missing_columns = sorted({"check", "status"} - set(audit.columns))
                rows.append(
                    check(
                        not missing_columns,
                        "gate_record_training_config_audit_has_required_columns",
                        f"missing={missing_columns}",
                    )
                )
                if not missing_columns:
                    observed_checks = set(audit["check"].astype(str))
                    missing_checks = sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS - observed_checks)
                    actual_failures = int(audit["status"].astype(str).ne("pass").sum())
                    rows.append(
                        check(
                            not missing_checks,
                            "gate_record_training_config_audit_has_formal_checks",
                            f"missing={missing_checks}",
                        )
                    )
                    rows.append(
                        check(
                            actual_failures == 0,
                            "gate_record_training_config_audit_has_no_failures",
                            f"failures={actual_failures}",
                        )
                    )
                    rows.append(
                        check(
                            recorded_training_checks is not None and recorded_training_checks == int(len(audit)),
                            "gate_record_training_config_audit_check_count_matches_record",
                            f"recorded={recorded_training_checks} actual={len(audit)}",
                        )
                    )
                    rows.append(
                        check(
                            recorded_training_failures is not None
                            and recorded_training_failures == actual_failures,
                            "gate_record_training_config_audit_failure_count_matches_record",
                            f"recorded={recorded_training_failures} actual={actual_failures}",
                        )
                    )
            except Exception as exc:
                rows.append(
                    check(
                        False,
                        "gate_record_training_config_audit_parseable",
                        f"{type(exc).__name__}: {exc}",
                    )
                )
        else:
            rows.append(
                check(False, "gate_record_training_config_audit_hash_matches", f"missing: {training_config_audit_path}")
            )

    selector_checkpoint_hash = ""
    if selector_spec_path is not None and selector_spec_path.exists():
        with selector_spec_path.open(encoding="utf-8") as handle:
            selector_spec = json.load(handle)
        selector_checkpoint_hash = str(selector_spec.get("checkpoint_sha256", ""))
        rows.append(
            check(
                bool(selector_checkpoint_hash),
                "selector_spec_records_checkpoint_hash",
                f"checkpoint_sha256={selector_checkpoint_hash or 'missing'}",
            )
        )
        rows.append(
            check(
                selector_checkpoint_hash == str(record.get("checkpoint_sha256", "")),
                "selector_spec_checkpoint_matches_gate_record",
                f"selector={selector_checkpoint_hash} gate={record.get('checkpoint_sha256', '')}",
            )
        )
    elif require_gate_pass:
        rows.append(
            check(
                False,
                "selector_spec_checkpoint_matches_gate_record",
                f"missing selector spec: {selector_spec_path}",
            )
        )
    return rows


def audit_heldout(
    neural_path: Path | None,
    non_neural_path: Path | None,
    budget_tolerance: float,
    selector_spec_path: Path | None,
    non_neural_schedule_path: Path | None,
    non_neural_run_schedule_path: Path | None,
) -> list[dict[str, str]]:
    if neural_path is None and non_neural_path is None:
        return [check(True, "heldout_audit_not_requested", "no held-out summary paths provided")]
    neural = load_optional(neural_path)
    non_neural = load_optional(non_neural_path)
    rows = []
    if neural.empty:
        rows.append(check(False, "heldout_neural_exists", f"missing or empty: {neural_path}"))
    else:
        rows.append(check(True, "heldout_neural_exists", display_path(neural_path)))
    if non_neural.empty:
        rows.append(check(False, "heldout_non_neural_exists", f"missing or empty: {non_neural_path}"))
    else:
        rows.append(check(True, "heldout_non_neural_exists", display_path(non_neural_path)))
    if neural.empty or non_neural.empty:
        return rows

    neural_ids = {f"{int(row.size)}:{row.file_key}" for row in neural.itertuples(index=False)}
    non_neural_ids = {f"{int(row.size)}:{row.file_key}" for row in non_neural.itertuples(index=False)}
    neural_key_columns = ["size", "file_key", "sample_seed"] if "sample_seed" in neural.columns else ["size", "file_key"]
    neural_duplicate_instances = int(neural.duplicated(neural_key_columns).sum())
    non_neural_duplicate_instances = int(non_neural.duplicated(["size", "file_key"]).sum())
    rows.append(
        check(
            neural_duplicate_instances == 0,
            "heldout_neural_group_keys_unique",
            f"key_columns={neural_key_columns} duplicates={neural_duplicate_instances}",
        )
    )
    rows.append(
        check(
            non_neural_duplicate_instances == 0,
            "heldout_non_neural_instance_keys_unique",
            f"duplicates={non_neural_duplicate_instances}",
        )
    )
    rows.append(
        check(
            neural_ids == non_neural_ids,
            "heldout_same_instances",
            f"neural={len(neural_ids)} non_neural={len(non_neural_ids)} symmetric_diff={len(neural_ids ^ non_neural_ids)}",
        )
    )
    neural_budget_column = "total_cpu_allocated" if "total_cpu_allocated" in neural.columns else "total_cpu_capped"
    if {neural_budget_column}.issubset(neural.columns) and {"budget_cpu_total"}.issubset(non_neural.columns):
        neural_budget_by_instance = pd.to_numeric(
            neural.groupby(["size", "file_key"])[neural_budget_column].mean(),
            errors="coerce",
        )
        non_neural_budget_by_instance = pd.to_numeric(
            non_neural.groupby(["size", "file_key"])["budget_cpu_total"].mean(),
            errors="coerce",
        )
        budget_pairs = pd.concat(
            [
                neural_budget_by_instance.rename("neural"),
                non_neural_budget_by_instance.rename("non_neural"),
            ],
            axis=1,
            join="inner",
        )
        per_instance_diffs = (budget_pairs["neural"] - budget_pairs["non_neural"]).abs()
        max_instance_diff = float(per_instance_diffs.max()) if not per_instance_diffs.empty else float("inf")
        bad_instances = int((per_instance_diffs > budget_tolerance).sum()) if not per_instance_diffs.empty else -1
        rows.append(
            check(
                bad_instances == 0,
                "heldout_budget_match_per_instance",
                f"bad_instances={bad_instances} max_diff={max_instance_diff:.3f}",
            )
        )
        neural_budget = float(neural_budget_by_instance.mean())
        non_neural_budget = float(non_neural_budget_by_instance.mean())
        diff = abs(neural_budget - non_neural_budget)
        rows.append(
            check(
                diff <= budget_tolerance,
                "heldout_budget_match",
                f"neural_{neural_budget_column}_mean={neural_budget:.3f} non_neural_mean={non_neural_budget:.3f} diff={diff:.3f}",
            )
        )
    else:
        rows.append(check(False, "heldout_budget_match", f"missing {neural_budget_column} or budget_cpu_total"))
    rows.extend(audit_neural_budget_fields(neural))
    rows.extend(audit_selector_spec(neural=neural, selector_spec_path=selector_spec_path))
    rows.extend(audit_non_neural_schedule(non_neural=non_neural, schedule_path=non_neural_schedule_path))
    rows.extend(
        audit_non_neural_run_schedule_source(
            out_schedule_path=non_neural_run_schedule_path,
            schedule_path=non_neural_schedule_path,
        )
    )
    return rows


def write_doc(rows: list[dict[str, str]], doc_path: Path) -> None:
    lines = [
        "# Residual Portfolio Protocol Audit",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['detail']} |")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit residual portfolio protocol artifacts.")
    parser.add_argument("--strong-combined", type=Path, default=None)
    parser.add_argument("--candidate-manifest", type=Path, default=None)
    parser.add_argument("--candidate-metadata", type=Path, default=None)
    parser.add_argument("--expected-candidate-total", type=int, default=None)
    parser.add_argument("--expected-generation-seed", type=int, default=None)
    parser.add_argument("--expected-split-seed", type=int, default=None)
    parser.add_argument("--require-candidate-files", action="store_true")
    parser.add_argument("--split-manifest", type=Path, default=None)
    parser.add_argument("--split-metadata", type=Path, default=None)
    parser.add_argument("--split-input", type=Path, default=None)
    parser.add_argument("--exclude-csv", type=Path, default=None)
    parser.add_argument("--exclude-cnf-root", type=Path, default=None)
    parser.add_argument("--neural-summary", type=Path, default=None)
    parser.add_argument("--non-neural-summary", type=Path, default=None)
    parser.add_argument("--selector-spec", type=Path, default=None)
    parser.add_argument("--gate-record", type=Path, default=None)
    parser.add_argument("--require-gate-pass", action="store_true")
    parser.add_argument("--non-neural-schedule", type=Path, default=None)
    parser.add_argument("--non-neural-run-schedule", type=Path, default=None)
    parser.add_argument("--budget-tolerance", type=float, default=1.0)
    parser.add_argument("--output-csv", type=Path, default=ROOT / "runs/analysis/residual_portfolio_protocol_audit.csv")
    parser.add_argument("--doc", type=Path, default=ROOT / "docs/residual_portfolio_protocol_audit.md")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    rows.extend(audit_strong_gate(args.strong_combined))
    rows.extend(
        audit_candidate_manifest(
            args.candidate_manifest,
            args.candidate_metadata,
            args.expected_candidate_total,
            args.expected_generation_seed,
            args.expected_split_seed,
            args.require_candidate_files,
        )
    )
    rows.extend(
        audit_split(
            args.split_manifest,
            args.exclude_csv,
            args.exclude_cnf_root,
            args.split_metadata,
            args.split_input,
            args.candidate_manifest,
        )
    )
    rows.extend(
        audit_heldout(
            args.neural_summary,
            args.non_neural_summary,
            args.budget_tolerance,
            args.selector_spec,
            args.non_neural_schedule,
            args.non_neural_run_schedule,
        )
    )
    rows.extend(audit_gate_record(args.gate_record, args.selector_spec, args.require_gate_pass))

    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_csv, index=False)
    write_doc(rows, args.doc.resolve())
    print(pd.DataFrame(rows).to_string(index=False))
    print(display_path(output_csv))
    print(display_path(args.doc.resolve()))
    if not args.allow_incomplete and any(row["status"] != "pass" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
