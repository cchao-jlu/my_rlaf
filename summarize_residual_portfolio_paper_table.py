from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


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


def duplicate_instance_count(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"Frame is missing instance-key columns: {missing}")
    return int(frame.duplicated(columns).sum())


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_csv(path: Path | None, required: bool = True) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return pd.DataFrame()
    return pd.read_csv(path)


def candidate_counts(candidate_manifest: pd.DataFrame, candidate_metadata_path: Path | None) -> dict[str, int | str]:
    if candidate_manifest.empty:
        return {
            "full_candidate_instances": "not_reported",
            "candidate_train_instances": "not_reported",
            "candidate_dev_instances": "not_reported",
            "candidate_heldout_instances": "not_reported",
            "candidate_generation_seed": "not_reported",
            "candidate_split_seed": "not_reported",
            "candidate_manifest_sha256": "not_reported",
        }
    if "split" not in candidate_manifest.columns:
        raise ValueError("Candidate manifest must contain split.")
    counts = candidate_manifest.groupby("split", sort=True).size()
    result: dict[str, int | str] = {
        "full_candidate_instances": int(len(candidate_manifest)),
        "candidate_train_instances": int(counts.get("candidate_train", 0)),
        "candidate_dev_instances": int(counts.get("candidate_dev", 0)),
        "candidate_heldout_instances": int(counts.get("candidate_heldout", 0)),
    }
    if candidate_metadata_path is not None and candidate_metadata_path.exists():
        with candidate_metadata_path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
        result["candidate_generation_seed"] = int(metadata["generation_seed"]) if "generation_seed" in metadata else "not_reported"
        result["candidate_split_seed"] = int(metadata["split_seed"]) if "split_seed" in metadata else "not_reported"
        result["candidate_manifest_sha256"] = metadata.get("manifest_sha256", "not_reported")
    else:
        result["candidate_generation_seed"] = "not_reported"
        result["candidate_split_seed"] = "not_reported"
        result["candidate_manifest_sha256"] = "not_reported"
    return result


def split_counts(split_manifest: pd.DataFrame, split_metadata_path: Path | None) -> dict[str, int | str]:
    if split_manifest.empty:
        return {
            "residual_train_instances": "not_reported",
            "residual_dev_instances": "not_reported",
            "residual_heldout_instances": "not_reported",
            "residual_split_source": "not_reported",
            "residual_split_input_sha256": "not_reported",
            "residual_split_candidate_manifest_sha256": "not_reported",
        }
    if "split" not in split_manifest.columns:
        raise ValueError("Split manifest must contain split.")
    counts = split_manifest.groupby("split", sort=True).size()
    result: dict[str, int | str] = {
        "residual_train_instances": int(counts.get("residual_train", 0)),
        "residual_dev_instances": int(counts.get("residual_dev", 0)),
        "residual_heldout_instances": int(counts.get("residual_heldout", 0)),
    }
    if split_metadata_path is not None and split_metadata_path.exists():
        with split_metadata_path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
        result["residual_split_source"] = metadata.get("split_source", "not_reported")
        result["residual_split_input_sha256"] = metadata.get("input_sha256", "not_reported")
        result["residual_split_candidate_manifest_sha256"] = metadata.get("candidate_manifest_sha256", "not_reported")
    else:
        result["residual_split_source"] = "not_reported"
        result["residual_split_input_sha256"] = "not_reported"
        result["residual_split_candidate_manifest_sha256"] = "not_reported"
    return result


def strong_gate_counts(combined: pd.DataFrame) -> dict[str, int]:
    if combined.empty:
        return {
            "strong_gate_candidate_instances": 0,
            "march_solved": 0,
            "cadical_solved": 0,
            "strong_solved_after_nominal_limit": 0,
            "union_solved": 0,
            "both_unknown_residual": 0,
        }
    required = {"solver_name", "family", "size", "file_key"}
    missing = required - set(combined.columns)
    if missing:
        raise ValueError(f"Strong gate combined CSV is missing columns: {sorted(missing)}")
    frame = combined.copy()
    if "solved" in frame.columns:
        frame["solved"] = parse_bool_series(frame["solved"], "solved")
    elif "Result" in frame.columns:
        frame["solved"] = frame["Result"].astype(str).isin(SOLVED)
    else:
        raise ValueError("Strong gate combined CSV must contain either solved or Result.")
    late_solved = (
        int(parse_bool_series(frame["solved_after_nominal_limit"], "solved_after_nominal_limit").sum())
        if "solved_after_nominal_limit" in frame.columns
        else 0
    )
    pivot = frame.pivot_table(
        index=["family", "size", "file_key"],
        columns="solver_name",
        values="solved",
        aggfunc="first",
        fill_value=False,
    )
    if not {"march", "cadical"}.issubset(pivot.columns):
        raise ValueError("Strong gate combined CSV must contain both march and cadical rows.")
    march = pivot["march"].astype(bool)
    cadical = pivot["cadical"].astype(bool)
    return {
        "strong_gate_candidate_instances": int(len(pivot)),
        "march_solved": int(march.sum()),
        "cadical_solved": int(cadical.sum()),
        "strong_solved_after_nominal_limit": late_solved,
        "union_solved": int((march | cadical).sum()),
        "both_unknown_residual": int((~march & ~cadical).sum()),
    }


def oracle_count(frame: pd.DataFrame) -> int | str:
    if frame.empty:
        return "not_run"
    if "solved_any" not in frame.columns:
        raise ValueError("Oracle summary must contain solved_any.")
    if duplicate_instance_count(frame, ["family", "size", "file_key"]):
        raise ValueError("Oracle summary contains duplicate instance keys.")
    return int(parse_bool_series(frame["solved_any"], "solved_any").sum())


def selected_neural_counts(frame: pd.DataFrame) -> dict[str, int | float | str]:
    if frame.empty:
        return {
            "fixed_neural_residual_solves": "not_run",
            "fixed_neural_instances": 0,
            "fixed_neural_mean_allocated_budget": "not_run",
            "fixed_neural_mean_budget": "not_run",
            "fixed_neural_mean_probe_budget": "not_run",
            "fixed_neural_mean_generation_wall_time": "not_run",
            "fixed_neural_mean_probe_wall_time": "not_run",
            "fixed_neural_mean_full_allocated_budget": "not_run",
            "fixed_neural_mean_full_budget": "not_run",
            "fixed_neural_mean_full_wall_time": "not_run",
            "fixed_neural_mean_total_wall_time": "not_run",
        }
    required = {"size", "file_key", "solved_any_strict60", "total_cpu_capped"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Neural summary is missing columns: {sorted(missing)}")
    frame = frame.copy()
    frame["solved_any_strict60"] = parse_bool_series(frame["solved_any_strict60"], "solved_any_strict60")
    agg_kwargs = {
        "solved": ("solved_any_strict60", "any"),
        "total_cpu": ("total_cpu_capped", "mean"),
    }
    if "total_cpu_allocated" in frame.columns:
        agg_kwargs["total_cpu_allocated"] = ("total_cpu_allocated", "mean")
    per_instance = frame.groupby(["size", "file_key"], sort=True).agg(**agg_kwargs)
    result = {
        "fixed_neural_residual_solves": int(per_instance["solved"].sum()),
        "fixed_neural_instances": int(len(per_instance)),
        "fixed_neural_mean_allocated_budget": float(per_instance["total_cpu_allocated"].mean())
        if "total_cpu_allocated" in per_instance.columns
        else "not_reported",
        "fixed_neural_mean_budget": float(per_instance["total_cpu"].mean()),
    }
    if "probe_cpu_total" in frame.columns:
        result["fixed_neural_mean_probe_budget"] = float(
            pd.to_numeric(frame.groupby(["size", "file_key"])["probe_cpu_total"].mean(), errors="coerce").mean()
        )
    else:
        result["fixed_neural_mean_probe_budget"] = "not_reported"
    if "full_cpu_capped" in frame.columns:
        result["fixed_neural_mean_full_budget"] = float(
            pd.to_numeric(frame.groupby(["size", "file_key"])["full_cpu_capped"].mean(), errors="coerce").mean()
        )
    else:
        result["fixed_neural_mean_full_budget"] = "not_reported"
    if "full_cpu_allocated" in frame.columns:
        result["fixed_neural_mean_full_allocated_budget"] = float(
            pd.to_numeric(frame.groupby(["size", "file_key"])["full_cpu_allocated"].mean(), errors="coerce").mean()
        )
    else:
        result["fixed_neural_mean_full_allocated_budget"] = "not_reported"
    for column, output_key in [
        ("neural_generation_wall_time", "fixed_neural_mean_generation_wall_time"),
        ("probe_wall_time_total", "fixed_neural_mean_probe_wall_time"),
        ("full_wall_time_total", "fixed_neural_mean_full_wall_time"),
        ("total_wall_time", "fixed_neural_mean_total_wall_time"),
    ]:
        if column in frame.columns:
            result[output_key] = float(
                pd.to_numeric(frame.groupby(["size", "file_key"])[column].mean(), errors="coerce").mean()
            )
        else:
            result[output_key] = "not_reported"
    return result


def non_neural_counts(frame: pd.DataFrame) -> dict[str, int | float | str]:
    if frame.empty:
        return {
            "fixed_non_neural_residual_solves": "not_run",
            "fixed_non_neural_instances": 0,
            "fixed_non_neural_mean_budget": "not_run",
            "fixed_non_neural_mean_wall_time": "not_run",
        }
    required = {"size", "file_key", "solved_any", "budget_cpu_total"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Non-neural summary is missing columns: {sorted(missing)}")
    if duplicate_instance_count(frame, ["size", "file_key"]):
        raise ValueError("Non-neural summary contains duplicate instance keys.")
    solved_any = parse_bool_series(frame["solved_any"], "solved_any")
    return {
        "fixed_non_neural_residual_solves": int(solved_any.sum()),
        "fixed_non_neural_instances": int(frame[["size", "file_key"]].drop_duplicates().shape[0]),
        "fixed_non_neural_mean_budget": float(pd.to_numeric(frame["budget_cpu_total"], errors="coerce").mean()),
        "fixed_non_neural_mean_wall_time": float(pd.to_numeric(frame["wall_time_total"], errors="coerce").mean())
        if "wall_time_total" in frame.columns
        else "not_reported",
    }


def compare_overlap(neural: pd.DataFrame, non_neural: pd.DataFrame) -> dict[str, int | str]:
    if neural.empty or non_neural.empty:
        return {
            "neural_only_over_non_neural": "not_run",
            "non_neural_only_over_neural": "not_run",
        }
    neural_frame = neural.copy()
    neural_frame["solved_any_strict60"] = parse_bool_series(
        neural_frame["solved_any_strict60"],
        "solved_any_strict60",
    )
    non_neural_frame = non_neural.copy()
    if duplicate_instance_count(non_neural_frame, ["size", "file_key"]):
        raise ValueError("Non-neural summary contains duplicate instance keys.")
    non_neural_frame["solved_any"] = parse_bool_series(non_neural_frame["solved_any"], "solved_any")
    neural_instance = neural_frame.groupby(["size", "file_key"], sort=True)["solved_any_strict60"].any()
    non_neural_instance = non_neural_frame.set_index(["size", "file_key"])["solved_any"]
    common = neural_instance.index.intersection(non_neural_instance.index)
    if len(common) != len(neural_instance) or len(common) != len(non_neural_instance):
        raise ValueError("Neural and non-neural summaries do not cover the same held-out instances.")
    neural_common = neural_instance.loc[common].astype(bool)
    non_neural_common = non_neural_instance.loc[common].astype(bool)
    return {
        "neural_only_over_non_neural": int((neural_common & ~non_neural_common).sum()),
        "non_neural_only_over_neural": int((~neural_common & non_neural_common).sum()),
    }


def budget_match_counts(neural: pd.DataFrame, non_neural: pd.DataFrame) -> dict[str, float | str]:
    if neural.empty or non_neural.empty:
        return {
            "same_budget_max_per_instance_diff": "not_run",
            "same_budget_mean_per_instance_diff": "not_run",
        }
    if "total_cpu_allocated" not in neural.columns or "budget_cpu_total" not in non_neural.columns:
        return {
            "same_budget_max_per_instance_diff": "not_reported",
            "same_budget_mean_per_instance_diff": "not_reported",
        }
    neural_budget = pd.to_numeric(
        neural.groupby(["size", "file_key"], sort=True)["total_cpu_allocated"].mean(),
        errors="coerce",
    )
    non_neural_budget = pd.to_numeric(
        non_neural.groupby(["size", "file_key"], sort=True)["budget_cpu_total"].mean(),
        errors="coerce",
    )
    common = neural_budget.index.intersection(non_neural_budget.index)
    if len(common) != len(neural_budget) or len(common) != len(non_neural_budget):
        raise ValueError("Cannot compare budgets: neural and non-neural summaries cover different instances.")
    diffs = (neural_budget.loc[common] - non_neural_budget.loc[common]).abs()
    return {
        "same_budget_max_per_instance_diff": float(diffs.max()) if not diffs.empty else 0.0,
        "same_budget_mean_per_instance_diff": float(diffs.mean()) if not diffs.empty else 0.0,
    }


def coverage_counts(split_manifest: pd.DataFrame, neural: pd.DataFrame, non_neural: pd.DataFrame) -> dict[str, int | str]:
    result: dict[str, int | str] = {}
    if split_manifest.empty or "split" not in split_manifest.columns:
        result["heldout_residual_manifest_instances"] = "not_reported"
        result["heldout_neural_missing_instances"] = "not_reported"
        result["heldout_non_neural_missing_instances"] = "not_reported"
        return result
    heldout = split_manifest[split_manifest["split"].astype(str) == "residual_heldout"]
    heldout_ids = {f"{int(row.size)}:{row.file_key}" for row in heldout.itertuples(index=False)}
    result["heldout_residual_manifest_instances"] = int(len(heldout_ids))
    if neural.empty:
        result["heldout_neural_missing_instances"] = "not_run"
    else:
        neural_ids = {f"{int(row.size)}:{row.file_key}" for row in neural.itertuples(index=False)}
        result["heldout_neural_missing_instances"] = int(len(heldout_ids - neural_ids))
    if non_neural.empty:
        result["heldout_non_neural_missing_instances"] = "not_run"
    else:
        non_neural_ids = {f"{int(row.size)}:{row.file_key}" for row in non_neural.itertuples(index=False)}
        result["heldout_non_neural_missing_instances"] = int(len(heldout_ids - non_neural_ids))
    return result


def markdown_table(rows: list[dict[str, object]]) -> list[str]:
    lines = ["| quantity | value |", "| --- | --- |"]
    for row in rows:
        value = row["value"]
        if isinstance(value, float):
            value = f"{value:.3f}"
        lines.append(f"| {row['quantity']} | {value} |")
    return lines


def write_doc(rows: list[dict[str, object]], paths: dict[str, Path | None], doc_path: Path) -> None:
    lines = [
        "# Residual Portfolio Paper Table",
        "",
        "Scope: denominator-preserving summary for the residual portfolio mainline.",
        "Oracle coverage is diagnostic; the paper claim must use fixed selected",
        "neural portfolio versus fixed same-budget non-neural portfolio.",
        "",
        "## Main Table",
        "",
        *markdown_table(rows),
        "",
        "## Inputs",
        "",
    ]
    for label, path in paths.items():
        lines.append(f"- {label}: `{display_path(path) if path else 'none'}`")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize residual portfolio artifacts into a paper-table skeleton.")
    parser.add_argument("--strong-combined", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, default=None)
    parser.add_argument("--candidate-metadata", type=Path, default=None)
    parser.add_argument("--split-manifest", type=Path, default=None)
    parser.add_argument("--split-metadata", type=Path, default=None)
    parser.add_argument("--oracle-summary", type=Path, default=None)
    parser.add_argument("--neural-summary", type=Path, default=None)
    parser.add_argument("--non-neural-summary", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=ROOT / "runs/analysis/residual_portfolio_paper_table.csv")
    parser.add_argument("--doc", type=Path, default=ROOT / "docs/residual_portfolio_paper_table.md")
    args = parser.parse_args()

    strong = load_csv(args.strong_combined)
    candidate_manifest = load_csv(args.candidate_manifest, required=False)
    split_manifest = load_csv(args.split_manifest, required=False)
    oracle = load_csv(args.oracle_summary, required=False)
    neural = load_csv(args.neural_summary, required=False)
    non_neural = load_csv(args.non_neural_summary, required=False)

    counts = {}
    counts.update(candidate_counts(candidate_manifest, args.candidate_metadata))
    counts.update(strong_gate_counts(strong))
    counts.update(split_counts(split_manifest, args.split_metadata))
    counts["oracle_neural_coverage"] = oracle_count(oracle)
    counts.update(selected_neural_counts(neural))
    counts.update(non_neural_counts(non_neural))
    counts.update(compare_overlap(neural, non_neural))
    counts.update(budget_match_counts(neural, non_neural))
    counts.update(coverage_counts(split_manifest, neural, non_neural))

    rows = [{"quantity": key, "value": value} for key, value in counts.items()]
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_csv, index=False)
    write_doc(
        rows=rows,
        paths={
            "strong_combined": args.strong_combined.resolve(),
            "candidate_manifest": args.candidate_manifest.resolve() if args.candidate_manifest else None,
            "candidate_metadata": args.candidate_metadata.resolve() if args.candidate_metadata else None,
            "split_manifest": args.split_manifest.resolve() if args.split_manifest else None,
            "split_metadata": args.split_metadata.resolve() if args.split_metadata else None,
            "oracle_summary": args.oracle_summary.resolve() if args.oracle_summary else None,
            "neural_summary": args.neural_summary.resolve() if args.neural_summary else None,
            "non_neural_summary": args.non_neural_summary.resolve() if args.non_neural_summary else None,
            "output_csv": output_csv,
        },
        doc_path=args.doc.resolve(),
    )
    print(pd.DataFrame(rows).to_string(index=False))
    print(display_path(output_csv))
    print(display_path(args.doc.resolve()))


if __name__ == "__main__":
    main()
