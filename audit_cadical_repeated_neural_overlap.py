from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/cadical_repeated_neural_overlap"
DOC_PATH = ROOT / "docs/cadical_repeated_neural_overlap_audit.md"

NEURAL_PATH = ROOT / "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv"
CADICAL_PATH = ROOT / "runs/analysis/cadical_repeat_stability/instance_summary.csv"

LOCAL_OPEN_SET = {"3sat_188.cnf", "3sat_196.cnf", "3sat_46.cnf", "3sat_66.cnf"}


def bool_text(value: object) -> str:
    return "yes" if bool(value) else "no"


def load_frame() -> pd.DataFrame:
    neural = pd.read_csv(NEURAL_PATH, dtype={"pattern": str})
    neural["pattern"] = neural["pattern"].astype(str).str.zfill(4)
    cadical = pd.read_csv(CADICAL_PATH)
    frame = neural.merge(cadical, on="file_key", how="left")
    if frame["cadical_solved_repeats"].isna().any():
        missing = frame.loc[frame["cadical_solved_repeats"].isna(), "file_key"].tolist()
        raise ValueError(f"Missing repeated CaDiCaL rows: {missing}")

    frame["cadical_solved_repeats"] = frame["cadical_solved_repeats"].astype(int)
    frame["cadical_solved_any"] = frame["cadical_solved_repeats"] > 0
    frame["cadical_solved_all"] = frame["cadical_solved_repeats"] == 3
    frame["cadical_unsolved_all"] = frame["cadical_solved_repeats"] == 0
    return frame


def subset_columns() -> list[str]:
    return [
        "file_key",
        "one_shot_solved",
        "online_solved",
        "old_compact_solved",
        "local_correction_solved",
        "cadical_solved_repeats",
        "cadical_solved_any",
        "cadical_solved_all",
        "cadical_time_mean",
        "cadical_time_min",
        "cadical_time_max",
        "results",
        "pattern",
        "one_shot_time_mean",
        "online_time_mean",
        "old_compact_time_mean",
        "local_correction_time_mean",
        "local_minus_online_time_mean",
        "local_minus_old_time_mean",
    ]


def write_subset(frame: pd.DataFrame, name: str, mask: pd.Series) -> pd.DataFrame:
    subset = frame.loc[mask, subset_columns()].sort_values("file_key").copy()
    subset.to_csv(OUT_DIR / f"{name}.csv", index=False)
    return subset


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
            if isinstance(value, bool):
                values.append(bool_text(value))
            elif isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_frame()

    masks = {
        "cadical_any_solved_local_unsolved": frame["cadical_solved_any"]
        & ~frame["local_correction_solved"],
        "cadical_all_solved_local_unsolved": frame["cadical_solved_all"]
        & ~frame["local_correction_solved"],
        "local_solved_cadical_unsolved_all": frame["local_correction_solved"]
        & frame["cadical_unsolved_all"],
        "local_solved_cadical_not_all": frame["local_correction_solved"]
        & ~frame["cadical_solved_all"],
        "online_solved_cadical_unsolved_all": frame["online_solved"] & frame["cadical_unsolved_all"],
        "online_solved_cadical_not_all": frame["online_solved"] & ~frame["cadical_solved_all"],
        "local_only_solved_cadical_unsolved_all": frame["local_correction_solved"]
        & ~frame["online_solved"]
        & frame["cadical_unsolved_all"],
        "oneshot_timeout_recovered_by_online": ~frame["one_shot_solved"] & frame["online_solved"],
        "local_open_set": frame["file_key"].isin(LOCAL_OPEN_SET),
    }
    subsets = {name: write_subset(frame, name, mask) for name, mask in masks.items()}

    local_strict = subsets["local_solved_cadical_unsolved_all"]
    online_strict = subsets["online_solved_cadical_unsolved_all"]
    recovered = subsets["oneshot_timeout_recovered_by_online"]
    local_open = subsets["local_open_set"]

    summary_rows = [
        {
            "question": "CaDiCaL solved in any repeat / Local unsolved",
            "count": len(subsets["cadical_any_solved_local_unsolved"]),
            "interpretation": "CaDiCaL covers these neural-workflow misses in at least one 60s repeat.",
        },
        {
            "question": "CaDiCaL solved in all repeats / Local unsolved",
            "count": len(subsets["cadical_all_solved_local_unsolved"]),
            "interpretation": "Stable CaDiCaL-only coverage against Local Boundary Correction.",
        },
        {
            "question": "Local solved / CaDiCaL unsolved in all repeats",
            "count": len(local_strict),
            "interpretation": "Strict repeated-baseline neural complementarity.",
        },
        {
            "question": "Local solved / CaDiCaL not solved in all repeats",
            "count": len(subsets["local_solved_cadical_not_all"]),
            "interpretation": "Boundary-sensitive complementarity including CaDiCaL variance cases.",
        },
        {
            "question": "Online solved / CaDiCaL unsolved in all repeats",
            "count": len(online_strict),
            "interpretation": "Strict repeated-baseline complementarity for the selector alone.",
        },
        {
            "question": "Online solved / CaDiCaL not solved in all repeats",
            "count": len(subsets["online_solved_cadical_not_all"]),
            "interpretation": "Selector complementarity if CaDiCaL runtime-boundary cases are included.",
        },
        {
            "question": "Local-only over Online / CaDiCaL unsolved in all repeats",
            "count": len(subsets["local_only_solved_cadical_unsolved_all"]),
            "interpretation": "Strict boundary-correction contribution beyond Online and repeated CaDiCaL.",
        },
        {
            "question": "One-shot timeout recovered by Online",
            "count": len(recovered),
            "interpretation": (
                f"CaDiCaL solved {int(recovered['cadical_solved_any'].sum())}/{len(recovered)} "
                "in at least one repeat and "
                f"{int(recovered['cadical_solved_all'].sum())}/{len(recovered)} in all repeats."
            ),
        },
        {
            "question": "Local Correction open set",
            "count": len(local_open),
            "interpretation": (
                f"CaDiCaL solved {int(local_open['cadical_solved_any'].sum())}/{len(local_open)} "
                "in at least one repeat and "
                f"{int(local_open['cadical_solved_all'].sum())}/{len(local_open)} in all repeats."
            ),
        },
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "summary.csv", index=False)

    union_rows = []
    for paper_name, solved_col in [
        ("One-shot", "one_shot_solved"),
        ("Online-Consistent Selector", "online_solved"),
        ("Old Compact", "old_compact_solved"),
        ("+ Local Boundary Correction", "local_correction_solved"),
    ]:
        method_solved = frame[solved_col]
        cad_any = frame["cadical_solved_any"]
        cad_all = frame["cadical_solved_all"]
        union_rows.append(
            {
                "method": paper_name,
                "method_solved": int(method_solved.sum()),
                "cadical_any_solved": int(cad_any.sum()),
                "union_vs_cadical_any": int((method_solved | cad_any).sum()),
                "method_only_vs_cadical_any": int((method_solved & ~cad_any).sum()),
                "cadical_any_only": int((cad_any & ~method_solved).sum()),
                "cadical_all_solved": int(cad_all.sum()),
                "union_vs_cadical_all": int((method_solved | cad_all).sum()),
                "method_only_vs_cadical_all": int((method_solved & ~cad_all).sum()),
                "cadical_all_only": int((cad_all & ~method_solved).sum()),
            }
        )
    union = pd.DataFrame(union_rows)
    union.to_csv(OUT_DIR / "portfolio_union_repeated_cadical.csv", index=False)

    frame.to_csv(OUT_DIR / "combined.csv", index=False)

    doc_lines = [
        "# Repeated CaDiCaL / Neural Overlap Audit",
        "",
        "Scope: decision audit only. This uses the existing full400 3-seed neural",
        "summary and the existing three CaDiCaL 60s repeats. It does not modify",
        "models, selectors, thresholds, Local Boundary Correction, or solver configs.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv",
        "runs/analysis/cadical_repeat_stability/instance_summary.csv",
        "```",
        "",
        "Definitions:",
        "",
        "- Neural solved means solved in all three solver-seed runs for that method.",
        "- CaDiCaL solved-any means solved in at least one of three 60s repeats.",
        "- CaDiCaL solved-all means solved in all three 60s repeats.",
        "- Strict neural complementarity means neural solved and CaDiCaL unsolved in all three repeats.",
        "",
        "## Summary",
        "",
        "| Question | Count | Interpretation |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        doc_lines.append(f"| {row['question']} | {row['count']} | {row['interpretation']} |")

    doc_lines.extend(
        [
            "",
            "## Portfolio Union Under Repeated CaDiCaL",
            "",
            "| Method | Method solved | CaDiCaL any | Union vs any | Method only vs any | CaDiCaL any only | CaDiCaL all | Union vs all | Method only vs all | CaDiCaL all only |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in union.iterrows():
        doc_lines.append(
            f"| {row['method']} | {row['method_solved']} | {row['cadical_any_solved']} | "
            f"{row['union_vs_cadical_any']} | {row['method_only_vs_cadical_any']} | "
            f"{row['cadical_any_only']} | {row['cadical_all_solved']} | "
            f"{row['union_vs_cadical_all']} | {row['method_only_vs_cadical_all']} | "
            f"{row['cadical_all_only']} |"
        )

    doc_lines.extend(
        [
            "",
            "## Local Solved / CaDiCaL Unsolved In All Repeats",
            "",
            *markdown_table(
                local_strict,
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "local_correction_solved",
                    "cadical_solved_repeats",
                    "results",
                    "pattern",
                ],
            ),
            "",
            "## Online Solved / CaDiCaL Unsolved In All Repeats",
            "",
            *markdown_table(
                online_strict,
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "cadical_solved_repeats",
                    "results",
                    "pattern",
                ],
            ),
            "",
            "## Local-Only Boundary Complement",
            "",
            *markdown_table(
                subsets["local_only_solved_cadical_unsolved_all"],
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "old_compact_solved",
                    "local_correction_solved",
                    "cadical_solved_repeats",
                    "results",
                    "local_minus_online_time_mean",
                    "pattern",
                ],
            ),
            "",
            "## One-Shot Timeout Recovered By Online",
            "",
            *markdown_table(
                recovered,
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "cadical_solved_repeats",
                    "results",
                    "cadical_time_min",
                    "cadical_time_max",
                    "pattern",
                ],
            ),
            "",
            "## Local Correction Open Set",
            "",
            *markdown_table(
                local_open,
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "old_compact_solved",
                    "local_correction_solved",
                    "cadical_solved_repeats",
                    "results",
                    "cadical_time_min",
                    "cadical_time_max",
                    "local_minus_online_time_mean",
                    "pattern",
                ],
            ),
            "",
            "## Decision",
            "",
            "- Strict neural/CaDiCaL complementarity is nonzero but small. Local solves",
            "  3 instances that CaDiCaL times out on in all three repeats:",
            "  `3sat_140.cnf`, `3sat_147.cnf`, and `3sat_188.cnf`. Online solves",
            "  2 such instances: `3sat_140.cnf` and `3sat_147.cnf`.",
            "- The strict boundary-correction contribution beyond Online and repeated",
            "  CaDiCaL is one instance: `3sat_188.cnf`. This supports cautious",
            "  complementarity / portfolio framing, not robust solved-count",
            "  dominance over CaDiCaL.",
            "- The larger boundary-sensitive complementarity count comes from CaDiCaL",
            "  runtime variance. Local solves 5 instances that CaDiCaL does not solve",
            "  in all repeats, but 2 of the 5 are solved by CaDiCaL in at least one",
            "  repeat.",
            "- Online's recovered one-shot timeouts do not establish complementarity",
            "  against CaDiCaL: CaDiCaL solves all 5 in all three repeats.",
            "- Local Boundary Correction's open set is mixed. CaDiCaL solves",
            "  `3sat_46.cnf` and `3sat_196.cnf` in all repeats, solves neither",
            "  `3sat_188.cnf` nor `3sat_66.cnf`, and Local only solves `3sat_188.cnf`",
            "  among those CaDiCaL-strict-unsolved points.",
            "- Therefore Local Boundary Correction should remain a neural-workflow",
            "  boundary ablation. The top-conference path, if pursued, should be",
            "  framed as boundary-sensitive neural/CDCL complementarity and risk",
            "  control, not standalone performance superiority over CaDiCaL.",
            "",
            "Generated artifacts:",
            "",
            "```text",
            "runs/analysis/cadical_repeated_neural_overlap/combined.csv",
            "runs/analysis/cadical_repeated_neural_overlap/summary.csv",
            "runs/analysis/cadical_repeated_neural_overlap/portfolio_union_repeated_cadical.csv",
            "runs/analysis/cadical_repeated_neural_overlap/cadical_any_solved_local_unsolved.csv",
            "runs/analysis/cadical_repeated_neural_overlap/cadical_all_solved_local_unsolved.csv",
            "runs/analysis/cadical_repeated_neural_overlap/local_solved_cadical_unsolved_all.csv",
            "runs/analysis/cadical_repeated_neural_overlap/local_solved_cadical_not_all.csv",
            "runs/analysis/cadical_repeated_neural_overlap/online_solved_cadical_unsolved_all.csv",
            "runs/analysis/cadical_repeated_neural_overlap/online_solved_cadical_not_all.csv",
            "runs/analysis/cadical_repeated_neural_overlap/local_only_solved_cadical_unsolved_all.csv",
            "runs/analysis/cadical_repeated_neural_overlap/oneshot_timeout_recovered_by_online.csv",
            "runs/analysis/cadical_repeated_neural_overlap/local_open_set.csv",
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")

    print(summary.to_string(index=False))
    print(union.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
