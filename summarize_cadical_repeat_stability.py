from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/cadical_repeat_stability"
DOC_PATH = ROOT / "docs/cadical_repeat_stability.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}
CADICAL_RUNS = [
    (0, ROOT / "runs/cadical/solver_stats_full400_cpu60.csv"),
    (1, ROOT / "runs/cadical/solver_stats_full400_cpu60_repeat1.csv"),
    (2, ROOT / "runs/cadical/solver_stats_full400_cpu60_repeat2.csv"),
]
KEYS = ["3sat_111.cnf", "3sat_132.cnf", "3sat_140.cnf", "3sat_25.cnf", "3sat_48.cnf"]


def file_key(path: object) -> str:
    return Path(str(path)).name


def load_cadical() -> pd.DataFrame:
    frames = []
    for repeat, path in CADICAL_RUNS:
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path)
        frame["repeat"] = repeat
        frame["file_key"] = frame["file"].map(file_key)
        frame["cadical_solved"] = frame["Result"].isin(SOLVED)
        frame["cadical_time"] = pd.to_numeric(frame["time"], errors="coerce")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


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
                elif col.endswith("_time") or col.endswith("_mean") or col.endswith("_std"):
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cadical = load_cadical()
    portfolio = pd.read_csv(ROOT / "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv")
    claim = pd.read_csv(ROOT / "runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv", dtype={"pattern": str})

    repeat_rows = []
    for repeat, group in cadical.groupby("repeat", sort=True):
        repeat_rows.append(
            {
                "repeat": int(repeat),
                "total": int(len(group)),
                "cadical_solved": int(group["cadical_solved"].sum()),
                "unknown": int((~group["cadical_solved"]).sum()),
                "mean_time": float(group["cadical_time"].mean()),
                "median_time": float(group["cadical_time"].median()),
                "external_timeouts": int(pd.Series(group["external_timeout"]).astype(bool).sum()),
            }
        )
    repeat_summary = pd.DataFrame(repeat_rows)
    repeat_summary.to_csv(OUT_DIR / "repeat_summary.csv", index=False)

    solved_counts = repeat_summary["cadical_solved"]
    aggregate = pd.DataFrame(
        [
            {
                "repeats": int(len(repeat_summary)),
                "cadical_solved_mean": float(solved_counts.mean()),
                "cadical_solved_std": float(solved_counts.std(ddof=0)),
                "cadical_solved_min": int(solved_counts.min()),
                "cadical_solved_max": int(solved_counts.max()),
                "mean_time_mean": float(repeat_summary["mean_time"].mean()),
                "mean_time_std": float(repeat_summary["mean_time"].std(ddof=0)),
            }
        ]
    )
    aggregate.to_csv(OUT_DIR / "aggregate.csv", index=False)

    instance_rows = []
    for key, group in cadical.groupby("file_key", sort=True):
        group = group.sort_values("repeat")
        solved_repeats = int(group["cadical_solved"].sum())
        times = pd.to_numeric(group["cadical_time"], errors="coerce")
        instance_rows.append(
            {
                "file_key": key,
                "cadical_solved_repeats": solved_repeats,
                "stable_cadical_solved": solved_repeats in {0, len(group)},
                "cadical_time_mean": float(times.mean()),
                "cadical_time_min": float(times.min()),
                "cadical_time_max": float(times.max()),
                "results": ",".join(group["Result"].astype(str).tolist()),
            }
        )
    instance_summary = pd.DataFrame(instance_rows)
    instance_summary.to_csv(OUT_DIR / "instance_summary.csv", index=False)

    unstable = instance_summary.loc[~instance_summary["stable_cadical_solved"]].sort_values("file_key")
    unstable.to_csv(OUT_DIR / "unstable_instances.csv", index=False)

    matched = portfolio.merge(repeat_summary[["repeat", "cadical_solved"]], on="repeat", how="left")
    matched["delta_vs_same_repeat_cadical"] = matched["portfolio_solved"] - matched["cadical_solved"]
    matched = matched[
        [
            "repeat",
            "portfolio_solved",
            "cadical_solved",
            "delta_vs_same_repeat_cadical",
            "local_first_stage_solved",
            "cadical_second_stage_solved",
            "cadical_only_vs_portfolio",
        ]
    ]
    matched.to_csv(OUT_DIR / "portfolio_vs_cadical_repeats.csv", index=False)

    key_rows = []
    claim_keys = set(claim["file_key"])
    for key in KEYS:
        cgroup = cadical.loc[cadical["file_key"].eq(key)].sort_values("repeat")
        crow = instance_summary.loc[instance_summary["file_key"].eq(key)].iloc[0].to_dict()
        claim_row = claim.loc[claim["file_key"].eq(key)]
        key_rows.append(
            {
                "file_key": key,
                "cadical_solved_repeats": int(crow["cadical_solved_repeats"]),
                "cadical_results": crow["results"],
                "cadical_time_min": float(crow["cadical_time_min"]),
                "cadical_time_max": float(crow["cadical_time_max"]),
                "previous_claim_class": "" if claim_row.empty else str(claim_row.iloc[0]["claim_class"]),
                "in_previous_portfolio_only_set": key in claim_keys,
            }
        )
    key_audit = pd.DataFrame(key_rows)
    key_audit.to_csv(OUT_DIR / "key_boundary_audit.csv", index=False)

    strict_repeated_neural = key_audit.loc[
        key_audit["previous_claim_class"].eq("stable_neural_first_complement")
        & key_audit["cadical_solved_repeats"].eq(0)
    ]
    solved_counts_text = ", ".join(str(int(value)) for value in repeat_summary["cadical_solved"])
    deltas_text = ", ".join(
        f"{int(value):+d}" for value in matched["delta_vs_same_repeat_cadical"].tolist()
    )

    lines = [
        "# CaDiCaL Full400 Repeat Stability",
        "",
        "Scope: repeat standalone CaDiCaL 60s on full400 to audit whether the",
        "portfolio advantage and portfolio-only claim split are stable against",
        "CaDiCaL runtime variance. This does not modify any neural model, selector,",
        "threshold, or portfolio schedule.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/cadical/solver_stats_full400_cpu60.csv",
        "runs/cadical/solver_stats_full400_cpu60_repeat1.csv",
        "runs/cadical/solver_stats_full400_cpu60_repeat2.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv",
        "runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv",
        "```",
        "",
        "## CaDiCaL Repeat Summary",
        "",
        *markdown_table(
            repeat_summary,
            ["repeat", "cadical_solved", "unknown", "mean_time", "median_time", "external_timeouts"],
        ),
        "",
        "## Matched Portfolio Delta",
        "",
        *markdown_table(
            matched,
            [
                "repeat",
                "portfolio_solved",
                "cadical_solved",
                "delta_vs_same_repeat_cadical",
                "local_first_stage_solved",
                "cadical_second_stage_solved",
                "cadical_only_vs_portfolio",
            ],
        ),
        "",
        "## Key Boundary Audit",
        "",
        *markdown_table(
            key_audit,
            [
                "file_key",
                "cadical_solved_repeats",
                "cadical_results",
                "cadical_time_min",
                "cadical_time_max",
                "previous_claim_class",
            ],
        ),
        "",
        "## Decision",
        "",
        "- Standalone CaDiCaL 60s is not a fixed 75/200 baseline under repeated",
        f"  wall-clock runs; repeats solve {solved_counts_text} instances.",
        "- Against matched same-repeat CaDiCaL counts, the portfolio deltas are",
        f"  {deltas_text}. The +4/+5 claim versus the original single CaDiCaL run",
        "  is not repeated-baseline robust and should be demoted.",
        "- Previously strict neural-first complement is weakened by CaDiCaL repeat",
        "  variance: `3sat_132.cnf` and `3sat_25.cnf` are solved by CaDiCaL in",
        "  repeat1 and repeat2. The repeated-baseline strict neural-first",
        f"  complement count is {len(strict_repeated_neural)}.",
        "- `3sat_111.cnf` and `3sat_48.cnf` are confirmed CaDiCaL runtime-boundary",
        "  cases: both are solved by repeated standalone CaDiCaL 60s runs.",
        "- Paper wording must distinguish the original CaDiCaL-run comparison",
        "  from matched repeated-CaDiCaL robustness.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/cadical_repeat_stability/repeat_summary.csv",
        "runs/analysis/cadical_repeat_stability/aggregate.csv",
        "runs/analysis/cadical_repeat_stability/instance_summary.csv",
        "runs/analysis/cadical_repeat_stability/unstable_instances.csv",
        "runs/analysis/cadical_repeat_stability/portfolio_vs_cadical_repeats.csv",
        "runs/analysis/cadical_repeat_stability/key_boundary_audit.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
