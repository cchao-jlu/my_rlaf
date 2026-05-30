from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/cadical_neural_overlap"
DOC_PATH = ROOT / "docs/cadical_neural_overlap_audit.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}
LOCAL_OPEN_SET = {"3sat_188.cnf", "3sat_196.cnf", "3sat_46.cnf", "3sat_66.cnf"}


def load_overlap() -> pd.DataFrame:
    neural = pd.read_csv(ROOT / "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv")
    neural["pattern"] = neural["pattern"].astype(str).str.zfill(4)
    cadical = pd.read_csv(ROOT / "runs/cadical/solver_stats_full400_cpu60.csv")
    cadical["file_key"] = cadical["file"].astype(str).map(lambda value: Path(value).name)
    cadical["cadical_solved"] = cadical["Result"].astype(str).isin(SOLVED_RESULTS)
    cadical["cadical_result"] = cadical["Result"].astype(str)
    cadical["cadical_time"] = pd.to_numeric(cadical["time"], errors="coerce")
    cadical["cadical_wall_time"] = pd.to_numeric(cadical["wall_time"], errors="coerce")
    merged = neural.merge(
        cadical[
            [
                "file_key",
                "cadical_result",
                "cadical_solved",
                "cadical_time",
                "cadical_wall_time",
                "external_timeout",
                "returncode",
            ]
        ],
        on="file_key",
        how="left",
    )
    if merged["cadical_solved"].isna().any():
        missing = merged.loc[merged["cadical_solved"].isna(), "file_key"].tolist()
        raise ValueError(f"Missing CaDiCaL rows: {missing}")
    return merged


def write_subset(frame: pd.DataFrame, name: str, mask: pd.Series) -> pd.DataFrame:
    columns = [
        "file_key",
        "one_shot_solved",
        "online_solved",
        "old_compact_solved",
        "local_correction_solved",
        "cadical_solved",
        "cadical_result",
        "cadical_time",
        "one_shot_time_mean",
        "online_time_mean",
        "old_compact_time_mean",
        "local_correction_time_mean",
        "pattern",
        "local_minus_online_time_mean",
        "local_minus_old_time_mean",
    ]
    subset = frame.loc[mask, columns].sort_values("file_key").copy()
    subset.to_csv(OUT_DIR / f"{name}.csv", index=False)
    return subset


def fmt_bool(value: object) -> str:
    return "yes" if bool(value) else "no"


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(f"{value:.3f}")
            elif isinstance(value, bool):
                vals.append(fmt_bool(value))
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_overlap()

    masks = {
        "cadical_solved_local_unsolved": frame["cadical_solved"] & ~frame["local_correction_solved"],
        "local_solved_cadical_unsolved": frame["local_correction_solved"] & ~frame["cadical_solved"],
        "online_solved_cadical_unsolved": frame["online_solved"] & ~frame["cadical_solved"],
        "oneshot_timeout_recovered_by_online": ~frame["one_shot_solved"] & frame["online_solved"],
        "local_open_set": frame["file_key"].isin(LOCAL_OPEN_SET),
    }
    subsets = {name: write_subset(frame, name, mask) for name, mask in masks.items()}

    recovered = subsets["oneshot_timeout_recovered_by_online"]
    local_open = subsets["local_open_set"]

    summary_rows = [
        {
            "question": "CaDiCaL solved / Local unsolved",
            "count": len(subsets["cadical_solved_local_unsolved"]),
            "interpretation": "CaDiCaL covers many instances missed by the neural-guided Glucose workflow.",
        },
        {
            "question": "Local solved / CaDiCaL unsolved",
            "count": len(subsets["local_solved_cadical_unsolved"]),
            "interpretation": "Nonzero complementarity for a neural/CaDiCaL portfolio.",
        },
        {
            "question": "Online solved / CaDiCaL unsolved",
            "count": len(subsets["online_solved_cadical_unsolved"]),
            "interpretation": "Online alone has nonzero complementarity, but these are all already One-shot solved.",
        },
        {
            "question": "One-shot timeout recovered by Online",
            "count": len(recovered),
            "interpretation": f"CaDiCaL solved {int(recovered['cadical_solved'].sum())}/{len(recovered)} of these.",
        },
        {
            "question": "Local Correction open set",
            "count": len(local_open),
            "interpretation": f"CaDiCaL solved {int(local_open['cadical_solved'].sum())}/{len(local_open)} open-set instances.",
        },
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "summary.csv", index=False)
    frame.to_csv(OUT_DIR / "combined.csv", index=False)

    union_rows = []
    for method, paper_name, solved_col in [
        ("one_shot", "One-shot", "one_shot_solved"),
        ("online_consistent_boundary400", "Online-Consistent Selector", "online_solved"),
        ("old_compact", "Old Compact", "old_compact_solved"),
        ("local_reopen_guarded", "+ Local Boundary Correction", "local_correction_solved"),
    ]:
        method_solved = frame[solved_col]
        cad_solved = frame["cadical_solved"]
        union_rows.append(
            {
                "method": method,
                "paper_name": paper_name,
                "method_solved": int(method_solved.sum()),
                "cadical_solved": int(cad_solved.sum()),
                "union_solved": int((method_solved | cad_solved).sum()),
                "method_only": int((method_solved & ~cad_solved).sum()),
                "cadical_only": int((cad_solved & ~method_solved).sum()),
                "both_solved": int((method_solved & cad_solved).sum()),
                "both_unsolved": int((~method_solved & ~cad_solved).sum()),
            }
        )
    union = pd.DataFrame(union_rows)
    union.to_csv(OUT_DIR / "portfolio_union_summary.csv", index=False)

    doc_lines = [
        "# CaDiCaL / Neural Full400 Overlap Audit",
        "",
        "Scope: decision audit only. This does not modify the model, selector,",
        "thresholds, Local Boundary Correction rule, or solver configuration.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv",
        "runs/cadical/solver_stats_full400_cpu60.csv",
        "```",
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
            "## Portfolio Union Counts",
            "",
            "| Method | Method solved | CaDiCaL solved | Union solved | Method only | CaDiCaL only | Both unsolved |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in union.iterrows():
        doc_lines.append(
            f"| {row['paper_name']} | {row['method_solved']} | {row['cadical_solved']} | "
            f"{row['union_solved']} | {row['method_only']} | {row['cadical_only']} | {row['both_unsolved']} |"
        )

    doc_lines.extend(
        [
            "",
            "## Local Solved / CaDiCaL Unsolved",
            "",
            *markdown_table(
                subsets["local_solved_cadical_unsolved"],
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "old_compact_solved",
                    "local_correction_solved",
                    "cadical_solved",
                    "cadical_time",
                    "pattern",
                ],
            ),
            "",
            "## Online Solved / CaDiCaL Unsolved",
            "",
            *markdown_table(
                subsets["online_solved_cadical_unsolved"],
                ["file_key", "one_shot_solved", "online_solved", "cadical_solved", "cadical_time", "pattern"],
            ),
            "",
            "## One-Shot Timeout Recovered By Online",
            "",
            *markdown_table(
                recovered,
                ["file_key", "one_shot_solved", "online_solved", "cadical_solved", "cadical_time", "pattern"],
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
                    "cadical_solved",
                    "cadical_time",
                    "local_minus_online_time_mean",
                    "pattern",
                ],
            ),
            "",
            "## Decision",
            "",
            "- There is stable nonzero neural/CaDiCaL complementarity: + Local Boundary",
            "  Correction solves 5 instances that CaDiCaL does not solve, and Online",
            "  alone solves 4 instances that CaDiCaL does not solve.",
            "- However, Online's 5 one-shot-timeout recoveries are all solved by",
            "  CaDiCaL. The Online complementarity instances are already One-shot solved,",
            "  so they do not support a strong recovery-over-CDCL story.",
            "- Local Correction's open set is mixed: CaDiCaL solves `3sat_46.cnf` and",
            "  `3sat_196.cnf` quickly, does not solve `3sat_188.cnf`, and also does not",
            "  solve neutral timeout `3sat_66.cnf`.",
            "- The best paper direction is complementarity / portfolio framing, not",
            "  standalone performance dominance. Local Boundary Correction remains an",
            "  internal neural-workflow ablation, with `3sat_188.cnf` as the only",
            "  open-set solved complementarity point against CaDiCaL.",
            "",
            "Generated artifacts:",
            "",
            "```text",
            "runs/analysis/cadical_neural_overlap/combined.csv",
            "runs/analysis/cadical_neural_overlap/summary.csv",
            "runs/analysis/cadical_neural_overlap/portfolio_union_summary.csv",
            "runs/analysis/cadical_neural_overlap/cadical_solved_local_unsolved.csv",
            "runs/analysis/cadical_neural_overlap/local_solved_cadical_unsolved.csv",
            "runs/analysis/cadical_neural_overlap/online_solved_cadical_unsolved.csv",
            "runs/analysis/cadical_neural_overlap/oneshot_timeout_recovered_by_online.csv",
            "runs/analysis/cadical_neural_overlap/local_open_set.csv",
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")

    print(summary.to_string(index=False))
    print(union.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
