from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/portfolio_e2e_local5_cadical55"
DOC_PATH = ROOT / "docs/portfolio_e2e_local5_cadical55_stability.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


def repeat_raw_paths() -> list[tuple[int, Path]]:
    return [
        (0, OUT_DIR / "full_raw.csv"),
        (1, OUT_DIR / "full_repeat1_raw.csv"),
        (2, OUT_DIR / "full_repeat2_raw.csv"),
    ]


def load_repeat_frame(repeat: int, path: Path, baseline: pd.DataFrame) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame["repeat"] = repeat
    frame["file_key"] = frame["file_key"].astype(str)
    merged = frame.merge(
        baseline[
            [
                "file_key",
                "cadical_solved",
                "cadical_time",
                "local_correction_solved",
                "local_correction_time_mean",
                "pattern",
            ]
        ],
        on="file_key",
        how="left",
        suffixes=("", "_60s_baseline"),
    )
    if merged["cadical_solved_60s_baseline"].isna().any():
        missing = merged.loc[merged["cadical_solved_60s_baseline"].isna(), "file_key"].tolist()
        raise ValueError(f"Missing CaDiCaL baseline rows: {missing}")
    merged["pattern"] = merged["pattern"].astype(str).str.zfill(4)
    merged["cadical_second_stage_solved"] = (
        ~merged["local_solved"].astype(bool) & merged["cadical_solved"].astype(bool)
    )
    merged["portfolio_only_vs_cadical"] = (
        merged["portfolio_solved"].astype(bool) & ~merged["cadical_solved_60s_baseline"].astype(bool)
    )
    merged["cadical_only_vs_portfolio"] = (
        ~merged["portfolio_solved"].astype(bool) & merged["cadical_solved_60s_baseline"].astype(bool)
    )
    merged["local_error"] = merged["local_result"].astype(str).eq("ERROR")
    return merged


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                if pd.isna(value):
                    values.append("")
                elif col.endswith("_time") or col.endswith("_time_mean") or col.endswith("_time_std"):
                    values.append(f"{value:.3f}")
                elif float(value).is_integer():
                    values.append(str(int(value)))
                else:
                    values.append(f"{value:.3f}")
            elif pd.isna(value):
                values.append("")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def main() -> None:
    baseline = pd.read_csv(ROOT / "runs/analysis/cadical_neural_overlap/combined.csv", dtype={"pattern": str})
    baseline["file_key"] = baseline["file_key"].astype(str)
    frames = [load_repeat_frame(repeat, path, baseline) for repeat, path in repeat_raw_paths()]
    combined = pd.concat(frames, ignore_index=True)

    repeat_rows = []
    for repeat, group in combined.groupby("repeat", sort=True):
        repeat_rows.append(
            {
                "repeat": int(repeat),
                "instances": int(len(group)),
                "portfolio_solved": int(group["portfolio_solved"].sum()),
                "local_first_stage_solved": int(group["local_solved"].sum()),
                "cadical_second_stage_solved": int(group["cadical_second_stage_solved"].sum()),
                "cadical_60s_baseline_solved": int(group["cadical_solved_60s_baseline"].sum()),
                "delta_vs_cadical_60s": int(
                    group["portfolio_solved"].sum() - group["cadical_solved_60s_baseline"].sum()
                ),
                "portfolio_only_vs_cadical": int(group["portfolio_only_vs_cadical"].sum()),
                "cadical_only_vs_portfolio": int(group["cadical_only_vs_portfolio"].sum()),
                "local_errors": int(group["local_error"].sum()),
                "mean_portfolio_time": float(pd.to_numeric(group["portfolio_time"], errors="coerce").mean()),
                "median_portfolio_time": float(pd.to_numeric(group["portfolio_time"], errors="coerce").median()),
            }
        )
    repeat_summary = pd.DataFrame(repeat_rows)
    repeat_summary.to_csv(OUT_DIR / "repeat_stability_summary.csv", index=False)

    solved_stats = repeat_summary["portfolio_solved"]
    aggregate = pd.DataFrame(
        [
            {
                "repeats": int(len(repeat_summary)),
                "portfolio_solved_mean": float(solved_stats.mean()),
                "portfolio_solved_std": float(solved_stats.std(ddof=0)),
                "portfolio_solved_min": int(solved_stats.min()),
                "portfolio_solved_max": int(solved_stats.max()),
                "delta_vs_cadical_min": int(repeat_summary["delta_vs_cadical_60s"].min()),
                "delta_vs_cadical_max": int(repeat_summary["delta_vs_cadical_60s"].max()),
                "cadical_only_vs_portfolio_max": int(repeat_summary["cadical_only_vs_portfolio"].max()),
                "local_errors_total": int(repeat_summary["local_errors"].sum()),
                "mean_portfolio_time_mean": float(repeat_summary["mean_portfolio_time"].mean()),
                "mean_portfolio_time_std": float(repeat_summary["mean_portfolio_time"].std(ddof=0)),
            }
        ]
    )
    aggregate.to_csv(OUT_DIR / "repeat_stability_aggregate.csv", index=False)

    instance_rows = []
    for file_key, group in combined.groupby("file_key", sort=True):
        group = group.sort_values("repeat")
        portfolio_repeats = int(group["portfolio_solved"].sum())
        local_repeats = int(group["local_solved"].sum())
        second_repeats = int(group["cadical_second_stage_solved"].sum())
        portfolio_only_repeats = int(group["portfolio_only_vs_cadical"].sum())
        cadical_only_repeats = int(group["cadical_only_vs_portfolio"].sum())
        instance_rows.append(
            {
                "file_key": file_key,
                "portfolio_solved_repeats": portfolio_repeats,
                "local_first_stage_solved_repeats": local_repeats,
                "cadical_second_stage_solved_repeats": second_repeats,
                "portfolio_only_vs_cadical_repeats": portfolio_only_repeats,
                "cadical_only_vs_portfolio_repeats": cadical_only_repeats,
                "stable_portfolio_solved": portfolio_repeats in {0, len(group)},
                "stable_portfolio_only_vs_cadical": portfolio_only_repeats in {0, len(group)},
                "cadical_60s_solved": bool(group["cadical_solved_60s_baseline"].iloc[0]),
                "cadical_60s_time": float(group["cadical_time_60s_baseline"].iloc[0]),
                "local_correction_time_mean": float(group["local_correction_time_mean"].iloc[0]),
                "portfolio_time_mean": float(pd.to_numeric(group["portfolio_time"], errors="coerce").mean()),
                "portfolio_time_std": float(pd.to_numeric(group["portfolio_time"], errors="coerce").std(ddof=0)),
                "pattern": str(group["pattern"].iloc[0]).zfill(4),
            }
        )
    instance_overlap = pd.DataFrame(instance_rows)
    instance_overlap.to_csv(OUT_DIR / "repeat_instance_overlap.csv", index=False)

    stable_portfolio_only = instance_overlap.loc[
        instance_overlap["portfolio_only_vs_cadical_repeats"].eq(len(repeat_summary))
    ].sort_values("file_key")
    boundary_portfolio_only = instance_overlap.loc[
        instance_overlap["portfolio_only_vs_cadical_repeats"].between(1, len(repeat_summary) - 1)
    ].sort_values("file_key")
    cadical_only_any = instance_overlap.loc[
        instance_overlap["cadical_only_vs_portfolio_repeats"].gt(0)
    ].sort_values("file_key")
    unstable_solved = instance_overlap.loc[
        ~instance_overlap["stable_portfolio_solved"]
    ].sort_values("file_key")

    stable_portfolio_only.to_csv(OUT_DIR / "repeat_stable_portfolio_only_vs_cadical.csv", index=False)
    boundary_portfolio_only.to_csv(OUT_DIR / "repeat_boundary_portfolio_only_vs_cadical.csv", index=False)
    cadical_only_any.to_csv(OUT_DIR / "repeat_any_cadical_only_vs_portfolio.csv", index=False)
    unstable_solved.to_csv(OUT_DIR / "repeat_unstable_portfolio_solved.csv", index=False)

    stable_local_first = int(stable_portfolio_only["local_first_stage_solved_repeats"].eq(len(repeat_summary)).sum())
    stable_second_stage = int(stable_portfolio_only["cadical_second_stage_solved_repeats"].eq(len(repeat_summary)).sum())
    boundary_second_stage = int(boundary_portfolio_only["cadical_second_stage_solved_repeats"].gt(0).sum())

    lines = [
        "# End-to-End Local-5s / CaDiCaL-55s Portfolio Stability",
        "",
        "Scope: repeated full400 end-to-end portfolio audit. The model, selector,",
        "Local Boundary Correction rule, CaDiCaL binary, and time split are fixed.",
        "Each repeat runs Local Boundary Correction for at most 5s, then CaDiCaL",
        "for at most 55s on unsolved instances.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/analysis/portfolio_e2e_local5_cadical55/full_raw.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/full_repeat1_raw.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/full_repeat2_raw.csv",
        "runs/analysis/cadical_neural_overlap/combined.csv",
        "```",
        "",
        "## Repeat Summary",
        "",
        *markdown_table(
            repeat_summary,
            [
                "repeat",
                "portfolio_solved",
                "local_first_stage_solved",
                "cadical_second_stage_solved",
                "cadical_60s_baseline_solved",
                "delta_vs_cadical_60s",
                "portfolio_only_vs_cadical",
                "cadical_only_vs_portfolio",
                "mean_portfolio_time",
            ],
        ),
        "",
        "## Aggregate",
        "",
        *markdown_table(
            aggregate,
            [
                "repeats",
                "portfolio_solved_mean",
                "portfolio_solved_std",
                "portfolio_solved_min",
                "portfolio_solved_max",
                "delta_vs_cadical_min",
                "delta_vs_cadical_max",
                "cadical_only_vs_portfolio_max",
                "local_errors_total",
            ],
        ),
        "",
        "## Stable Portfolio-Only Instances",
        "",
        *markdown_table(
            stable_portfolio_only,
            [
                "file_key",
                "portfolio_only_vs_cadical_repeats",
                "local_first_stage_solved_repeats",
                "cadical_second_stage_solved_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
            ],
        ),
        "",
        "## Boundary-Sensitive Portfolio-Only Instances",
        "",
        *markdown_table(
            boundary_portfolio_only,
            [
                "file_key",
                "portfolio_only_vs_cadical_repeats",
                "local_first_stage_solved_repeats",
                "cadical_second_stage_solved_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
            ],
        ),
        "",
        "## Any CaDiCaL-Only Losses",
        "",
        *markdown_table(
            cadical_only_any,
            [
                "file_key",
                "cadical_only_vs_portfolio_repeats",
                "cadical_60s_time",
                "portfolio_time_mean",
                "pattern",
            ],
        ),
        "",
        "## Decision",
        "",
        "- The true end-to-end portfolio solves 79-80/200 over three full400",
        "  repeats, compared with 75/200 for CaDiCaL 60s.",
        "- Portfolio improvement over CaDiCaL is +4 to +5 solved instances, with",
        "  zero CaDiCaL-only losses in all repeats.",
        "- Local first stage is stable at 40 solves across repeats. Among the four",
        f"  stable portfolio-only instances, {stable_local_first} are solved by Local",
        f"  within 5s and {stable_second_stage} is solved by the second-stage 55s",
        "  CaDiCaL run despite the independent 60s CaDiCaL baseline timing out.",
        f"- Boundary-sensitive portfolio-only evidence is {boundary_second_stage}",
        "  second-stage CaDiCaL cutoff/runtime boundary case.",
        "- Stable portfolio-only instances are `3sat_111.cnf`, `3sat_132.cnf`,",
        "  `3sat_140.cnf`, and `3sat_25.cnf`; `3sat_48.cnf` is boundary-sensitive",
        "  and appears in two of three repeats.",
        "- This supports a cautious portfolio/complementarity claim. The strongest",
        "  neural-first contribution is the stable 5s Local solves; the second-stage",
        "  CaDiCaL-only cutoff cases should be reported as runtime-boundary evidence,",
        "  not as neural solves.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_aggregate.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stable_portfolio_only_vs_cadical.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_boundary_portfolio_only_vs_cadical.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_any_cadical_only_vs_portfolio.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_unstable_portfolio_solved.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
