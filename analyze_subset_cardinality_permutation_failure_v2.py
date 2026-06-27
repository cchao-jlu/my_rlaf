from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

VARIANT_SUMMARY = ROOT / "runs/analysis/symmetry_adapter_objective_subset_variant_summary_v2.csv"
PAIR_SUMMARY = ROOT / "runs/analysis/symmetry_adapter_objective_subset_pair_summary_v2.csv"
ORBIT_CONTRIB = ROOT / "runs/analysis/symmetry_adapter_objective_subset_orbit_contrib_v2.csv"
OVERADAPTATION = ROOT / "runs/analysis/symmetry_adapter_objective_overadaptation_orbits_v2.csv"
VARIABLE_ROWS = ROOT / "runs/analysis/symmetry_subset_bw12_variable_rows_v2.csv"
PROXY_ROWS = ROOT / "runs/analysis/symmetry_adapter_objective_fix_v1_proxy_rows.csv"

OUT_VALID_VARIABLES = ROOT / "runs/analysis/subset_cardinality_bw12_perm_failure_valid_orbit_variables_v2.csv"
OUT_SUMMARY = ROOT / "runs/analysis/subset_cardinality_bw12_perm_failure_diagnosis_v2.csv"
DOC = ROOT / "docs/subset_cardinality_bw12_permutation_failure_v2.md"

VALID_ORBIT = "subset_cardinality_refined_o06_size2"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> list[str]:
    if frame.empty:
        return ["_None._"]
    view = frame.head(max_rows).copy()
    columns = list(view.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in view.iterrows():
        values: list[str] = []
        for column in columns:
            value = row[column]
            if isinstance(value, (float, np.floating)):
                values.append("nan" if math.isnan(float(value)) else f"{float(value):.5g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    if len(frame) > max_rows:
        lines.append(f"| ... | {len(frame) - max_rows} more rows |" + " |" * max(0, len(columns) - 2))
    return lines


def direction(decisions_delta: float, conflicts_delta: float) -> str:
    worse = decisions_delta > 0.0 or conflicts_delta > 0.0
    better = decisions_delta < 0.0 or conflicts_delta < 0.0
    if worse and better:
        return "mixed"
    if worse:
        return "worse"
    if better:
        return "better"
    return "flat"


def build_valid_orbit_variables(variable_rows: pd.DataFrame) -> pd.DataFrame:
    valid = variable_rows[variable_rows["orbit"].astype(str).eq(VALID_ORBIT)].copy()
    valid["event_l2_rank_in_variant_repeat"] = valid.groupby(["variant", "repeat_id"])["event_l2"].rank(method="dense")
    return valid.sort_values(["variant", "repeat_id", "original_var"]).reset_index(drop=True)


def build_summary(
    variant_summary: pd.DataFrame,
    pair_summary: pd.DataFrame,
    orbit_contrib: pd.DataFrame,
    overadaptation: pd.DataFrame,
    valid_variables: pd.DataFrame,
    proxy_rows: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    proxy_by_case = (
        proxy_rows.set_index("case_id").to_dict("index")
        if not proxy_rows.empty and "case_id" in proxy_rows.columns
        else {}
    )
    for _, variant in variant_summary.iterrows():
        name = str(variant["variant"])
        valid_group = valid_variables[valid_variables["variant"].astype(str).eq(name)].copy()
        valid_orbit_rows = orbit_contrib[
            orbit_contrib["variant"].astype(str).eq(name)
            & orbit_contrib["event_row_valid_reason"].astype(str).eq("valid")
        ].copy()
        invalid_group = orbit_contrib[
            orbit_contrib["variant"].astype(str).eq(name)
            & ~orbit_contrib["event_row_valid_reason"].astype(str).eq("valid")
        ].copy()
        over_rows = overadaptation[
            overadaptation["variant"].astype(str).eq(name)
            & overadaptation["orbit"].astype(str).eq(VALID_ORBIT)
        ].copy()
        case_id = f"subset_cardinality_bw12::{name}"
        proxy = proxy_by_case.get(case_id, {})
        decisions_delta = float(variant["decisions_delta_mean"])
        conflicts_delta = float(variant["conflicts_delta_mean"])
        rows.append(
            {
                "variant": name,
                "search_direction": direction(decisions_delta, conflicts_delta),
                "repeat_rows": int(variant["repeat_rows"]),
                "search_worse_rows": int(variant["search_worse_rows"]),
                "decisions_delta_mean": decisions_delta,
                "conflicts_delta_mean": conflicts_delta,
                "valid_event_gain_max": float(variant["event_identity_gain_max_valid"]),
                "valid_adapter_gain_max": float(variant["adapter_identity_gain_max_valid"]),
                "valid_adapter_to_event_ratio": (
                    float(variant["adapter_identity_gain_max_valid"])
                    / max(float(variant["event_identity_gain_max_valid"]), 1.0e-9)
                ),
                "invalid_event_gain_max": float(variant["event_identity_gain_max_invalid"]),
                "invalid_adapter_gain_max": float(variant["adapter_identity_gain_max_invalid"]),
                "valid_orbit_event_l2_min": float(valid_group["event_l2"].min()) if not valid_group.empty else np.nan,
                "valid_orbit_event_l2_max": float(valid_group["event_l2"].max()) if not valid_group.empty else np.nan,
                "valid_orbit_delta_mu_min": float(valid_group["delta_mu"].min()) if not valid_group.empty else np.nan,
                "valid_orbit_delta_mu_max": float(valid_group["delta_mu"].max()) if not valid_group.empty else np.nan,
                "valid_orbit_rows": int(variant["valid_orbit_rows"]),
                "invalid_orbit_rows": int(variant["invalid_orbit_rows"]),
                "invalid_rows_static_mu_not_collapsed": int(
                    invalid_group[invalid_group["event_row_valid_reason"].astype(str).eq("static_mu_not_collapsed")]["rows"].sum()
                )
                if not invalid_group.empty
                else 0,
                "objective_proxy_label": proxy.get("proxy_label", ""),
                "objective_proxy_score": proxy.get("objective_score", np.nan),
                "objective_permutation_penalty": proxy.get("permutation_inconsistency_penalty", np.nan),
                "objective_invalid_orbit_penalty": proxy.get("invalid_orbit_identity_penalty", np.nan),
                "overadaptation_valid_rows": int(len(over_rows)),
            }
        )
    summary = pd.DataFrame(rows)
    for _, pair in pair_summary.iterrows():
        left = str(pair["left_variant"])
        right = str(pair["right_variant"])
        for variant in [left, right]:
            mask = summary["variant"].astype(str).eq(variant)
            prefix = f"pair_{left}_vs_{right}"
            summary.loc[mask, f"{prefix}_search_mismatch_rows"] = int(pair["search_direction_mismatch_rows"])
            summary.loc[mask, f"{prefix}_adapted_mu_spearman"] = float(pair["mean_adapted_mu_spearman"])
            summary.loc[mask, f"{prefix}_delta_mu_spearman"] = float(pair["mean_delta_mu_spearman"])
            summary.loc[mask, f"{prefix}_valid_adapter_gain_abs_diff"] = float(pair["valid_mean_adapter_gain_abs_diff"])
    return summary.sort_values("variant").reset_index(drop=True)


def write_doc(
    summary: pd.DataFrame,
    pair_summary: pd.DataFrame,
    orbit_contrib: pd.DataFrame,
    valid_variables: pd.DataFrame,
) -> None:
    valid_view = valid_variables[
        [
            "variant",
            "repeat_id",
            "original_var",
            "event_l2",
            "static_mu",
            "adapted_mu",
            "delta_mu",
            "primary_delta_final_decisions",
            "primary_delta_final_conflicts",
        ]
    ].copy()
    contrib_view = orbit_contrib[
        [
            "variant",
            "event_row_valid_reason",
            "rows",
            "search_worse_rows",
            "event_identity_gain_mean",
            "event_identity_gain_max",
            "adapter_identity_gain_mean",
            "adapter_identity_gain_max",
            "adapted_mu_range_max",
            "static_mu_range_max",
        ]
    ].copy()
    lines = [
        "# subset_cardinality_bw12 Permutation Failure Diagnosis v2",
        "",
        "## Scope",
        "",
        "This is an adapter objective / permutation robustness diagnosis. It does not run a full benchmark, does not train a gate/selector, and does not make a speedup claim.",
        "",
        "The question is why `subset_cardinality_bw12::perm_seed1730` has strong event signal and adapter separation but worse final decisions/conflicts.",
        "",
        "## Variant Summary",
        "",
        *markdown_table(summary),
        "",
        "## Pairwise Permutation Alignment",
        "",
        *markdown_table(pair_summary),
        "",
        "## Valid/Invalid Orbit Contribution",
        "",
        *markdown_table(contrib_view),
        "",
        "## Valid Orbit Variable Rows",
        "",
        *markdown_table(valid_view),
        "",
        "## Diagnosis",
        "",
        "- This is not an event-missing case: all three variants have valid event-positive rows on the same refined size-2 orbit.",
        "- `perm_seed1730` worsens decisions/conflicts in 3/3 repeats while `base` and `perm_seed1731` improve search counts.",
        "- Pairwise alignment is weakest for `base` vs `perm_seed1730`: adapted-mu Spearman is 0.415 and delta-mu Spearman is 0.238, with search-direction mismatch on all orbit pair rows.",
        "- Invalid rows are still large in raw maxima: `static_mu_not_collapsed` rows dominate event gain, so positive objectives must use valid orbit masks and keep invalid rows diagnostic-only.",
        "- Magnitude alone is insufficient: `perm_seed1731` also has a large valid adapter/event ratio but improves search. The objective needs permutation consistency plus magnitude restraint and non-symmetric/no-valid-orbit guards.",
        "",
        "## Objective Implication",
        "",
        "`perm_seed1730` should be treated as a hard negative for the adapter objective: valid event evidence is present, but the adapter delta is permutation-non-robust and search-worsening. This supports Objective Fix v1 rather than broader runtime expansion.",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    variant_summary = read_csv(VARIANT_SUMMARY)
    pair_summary = read_csv(PAIR_SUMMARY)
    orbit_contrib = read_csv(ORBIT_CONTRIB)
    overadaptation = read_csv(OVERADAPTATION)
    variable_rows = read_csv(VARIABLE_ROWS)
    proxy_rows = read_csv(PROXY_ROWS) if PROXY_ROWS.exists() else pd.DataFrame()

    valid_variables = build_valid_orbit_variables(variable_rows)
    summary = build_summary(
        variant_summary=variant_summary,
        pair_summary=pair_summary,
        orbit_contrib=orbit_contrib,
        overadaptation=overadaptation,
        valid_variables=valid_variables,
        proxy_rows=proxy_rows,
    )
    OUT_VALID_VARIABLES.parent.mkdir(parents=True, exist_ok=True)
    valid_variables.to_csv(OUT_VALID_VARIABLES, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    write_doc(summary, pair_summary, orbit_contrib, valid_variables)
    print(f"wrote {OUT_VALID_VARIABLES}")
    print(f"wrote {OUT_SUMMARY}")
    print(f"wrote {DOC}")


if __name__ == "__main__":
    main()
