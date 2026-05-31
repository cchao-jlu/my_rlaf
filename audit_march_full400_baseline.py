from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
MARCH_CSV = ROOT / "runs/march/solver_stats_full400_cpu60.csv"
NEURAL_CSV = ROOT / "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv"
CADICAL_CSV = ROOT / "runs/analysis/cadical_repeat_stability/instance_summary.csv"
OUT_DIR = ROOT / "runs/analysis/march_full400_cpu60"
DOC_PATH = ROOT / "docs/march_full400_baseline_audit.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


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
                values.append("yes" if value else "no")
            elif isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    march = pd.read_csv(MARCH_CSV)
    march["file_key"] = march["file"].astype(str).map(lambda value: Path(value).name)
    march["march_solved_external65"] = march["Result"].astype(str).isin(SOLVED)
    march["march_time"] = pd.to_numeric(march["time"], errors="coerce")
    march["march_wall_time"] = pd.to_numeric(march["wall_time"], errors="coerce")
    march["march_solved_strict60"] = march["march_solved_external65"] & (march["march_wall_time"] <= 60.0)
    march["march_time_strict60"] = march["march_wall_time"].where(march["march_solved_strict60"], 60.0)

    neural = pd.read_csv(NEURAL_CSV, dtype={"pattern": str})
    neural["pattern"] = neural["pattern"].astype(str).str.zfill(4)
    cadical = pd.read_csv(CADICAL_CSV)
    cadical["cadical_solved_repeats"] = cadical["cadical_solved_repeats"].astype(int)
    cadical["cadical_unsolved_all"] = cadical["cadical_solved_repeats"].eq(0)

    frame = neural.merge(
        march[
            [
                "file_key",
                "Result",
                "march_solved_external65",
                "march_solved_strict60",
                "march_time",
                "march_wall_time",
                "march_time_strict60",
                "external_timeout",
            ]
        ],
        on="file_key",
        how="left",
    ).merge(
        cadical[["file_key", "cadical_solved_repeats", "cadical_unsolved_all", "results"]],
        on="file_key",
        how="left",
    )
    if frame["march_solved_external65"].isna().any():
        missing = frame.loc[frame["march_solved_external65"].isna(), "file_key"].tolist()
        raise ValueError(f"Missing March rows: {missing}")

    summary = pd.DataFrame(
        [
            {
                "solver": "March",
                "total": int(len(frame)),
                "solved_external65": int(frame["march_solved_external65"].sum()),
                "solved_strict60": int(frame["march_solved_strict60"].sum()),
                "solved_after_60_before_65": int(
                    (frame["march_solved_external65"] & ~frame["march_solved_strict60"]).sum()
                ),
                "mean_time_strict60": float(frame["march_time_strict60"].mean()),
                "median_time_strict60": float(frame["march_time_strict60"].median()),
                "external_timeouts": int(frame["external_timeout"].astype(str).str.lower().isin({"true", "1"}).sum()),
            }
        ]
    )
    summary.to_csv(OUT_DIR / "strict60_summary.csv", index=False)

    comparison_rows = []
    methods = [
        ("One-shot", "one_shot_solved"),
        ("Online-Consistent Selector", "online_solved"),
        ("Old Compact", "old_compact_solved"),
        ("+ Local Boundary Correction", "local_correction_solved"),
    ]
    for name, solved_col in methods:
        method_solved = frame[solved_col].astype(bool)
        march_solved = frame["march_solved_strict60"].astype(bool)
        comparison_rows.append(
            {
                "method": name,
                "method_solved": int(method_solved.sum()),
                "march_strict60_solved": int(march_solved.sum()),
                "union_solved": int((method_solved | march_solved).sum()),
                "method_only_vs_march": int((method_solved & ~march_solved).sum()),
                "march_only_vs_method": int((march_solved & ~method_solved).sum()),
                "both_unsolved": int((~method_solved & ~march_solved).sum()),
            }
        )
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(OUT_DIR / "neural_vs_march_overlap.csv", index=False)

    key_mask = frame["file_key"].isin(["3sat_140.cnf", "3sat_147.cnf", "3sat_188.cnf"])
    key = frame.loc[
        key_mask,
        [
            "file_key",
            "one_shot_solved",
            "online_solved",
            "local_correction_solved",
            "cadical_solved_repeats",
            "march_solved_strict60",
            "march_wall_time",
            "pattern",
        ],
    ].sort_values("file_key")
    key.to_csv(OUT_DIR / "strict_complement_keys.csv", index=False)

    local_only_vs_march = frame.loc[
        frame["local_correction_solved"].astype(bool) & ~frame["march_solved_strict60"].astype(bool),
        [
            "file_key",
            "one_shot_solved",
            "online_solved",
            "local_correction_solved",
            "cadical_solved_repeats",
            "march_solved_strict60",
            "march_wall_time",
            "pattern",
        ],
    ].sort_values("file_key")
    local_only_vs_march.to_csv(OUT_DIR / "local_solved_march_unsolved.csv", index=False)

    march_only_vs_local = frame.loc[
        frame["march_solved_strict60"].astype(bool) & ~frame["local_correction_solved"].astype(bool),
        [
            "file_key",
            "one_shot_solved",
            "online_solved",
            "local_correction_solved",
            "cadical_solved_repeats",
            "march_solved_strict60",
            "march_wall_time",
            "pattern",
        ],
    ].sort_values("file_key")
    march_only_vs_local.to_csv(OUT_DIR / "march_solved_local_unsolved.csv", index=False)

    lines = [
        "# March Full400 Baseline Audit",
        "",
        "Scope: evaluate the existing unweighted March binary as an additional",
        "solver-family baseline on full400. This does not change the neural model,",
        "selector, Local Boundary Correction rule, or portfolio schedule.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/march/solver_stats_full400_cpu60.csv",
        "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv",
        "runs/analysis/cadical_repeat_stability/instance_summary.csv",
        "```",
        "",
        "Important timing note: March has no internal 60s flag in the current",
        "runner. The raw run used a 65s external guard. The paper-relevant count",
        "below therefore reports a strict 60s solved count, treating solutions with",
        "wall time greater than 60s as timeouts.",
        "",
        "## Summary",
        "",
        *markdown_table(
            summary,
            [
                "solver",
                "total",
                "solved_external65",
                "solved_strict60",
                "solved_after_60_before_65",
                "mean_time_strict60",
                "median_time_strict60",
                "external_timeouts",
            ],
        ),
        "",
        "## Neural / March Overlap",
        "",
        *markdown_table(
            comparison,
            [
                "method",
                "method_solved",
                "march_strict60_solved",
                "union_solved",
                "method_only_vs_march",
                "march_only_vs_method",
                "both_unsolved",
            ],
        ),
        "",
        "## Former CaDiCaL-Strict Complement Keys",
        "",
        *markdown_table(
            key,
            [
                "file_key",
                "online_solved",
                "local_correction_solved",
                "cadical_solved_repeats",
                "march_solved_strict60",
                "march_wall_time",
                "pattern",
            ],
        ),
        "",
        "## Decision",
        "",
        "- March strict-60 solves 184/200, far above CaDiCaL repeats (75, 80, 80),",
        "  the Local5 -> CaDiCaL55 portfolio (79-80/200), and all neural-stage",
        "  Glucose-guided methods (48-54/200).",
        "- March solves all three instances that were Local-solved and CaDiCaL",
        "  unsolved in all repeated CaDiCaL runs: `3sat_140.cnf`, `3sat_147.cnf`,",
        "  and `3sat_188.cnf`.",
        "- Local Boundary Correction has no strict solved-count complement against",
        "  March under this single strict-60 run: Local solved / March unsolved is",
        f"  {len(local_only_vs_march)} instances.",
        "- Therefore, the current evidence cannot support a top-conference claim of",
        "  complementarity against strong SAT baselines. Unless March is excluded by",
        "  a clearly justified benchmark protocol, the paper should pivot further",
        "  toward neural-guidance failure boundary analysis, risk control, or a",
        "  workshop/negative-results framing.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/march_full400_cpu60/strict60_summary.csv",
        "runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv",
        "runs/analysis/march_full400_cpu60/strict_complement_keys.csv",
        "runs/analysis/march_full400_cpu60/local_solved_march_unsolved.csv",
        "runs/analysis/march_full400_cpu60/march_solved_local_unsolved.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(summary.to_string(index=False))
    print(comparison.to_string(index=False))
    print(key.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
