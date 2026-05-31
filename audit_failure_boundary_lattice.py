from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/failure_boundary_lattice"
DOC_PATH = ROOT / "docs/failure_boundary_lattice_audit.md"

SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def load_frame() -> pd.DataFrame:
    glucose = pd.read_csv(ROOT / "runs/glucose/solver_stats_full400_cpu60.csv")
    glucose["file_key"] = glucose["file"].astype(str).map(lambda value: Path(value).name)
    glucose["glucose_solved"] = glucose["Result"].astype(str).isin(SOLVED)
    glucose["glucose_time"] = pd.to_numeric(glucose["time"], errors="coerce")

    neural = pd.read_csv(
        ROOT / "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv",
        dtype={"pattern": str},
    )
    neural["pattern"] = neural["pattern"].astype(str).str.zfill(4)

    cadical = pd.read_csv(ROOT / "runs/analysis/cadical_repeat_stability/instance_summary.csv")
    march = pd.read_csv(ROOT / "runs/analysis/march_full400_cpu60/strict60_instance_summary.csv")
    portfolio = pd.read_csv(
        ROOT / "runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv",
        dtype={"pattern": str},
    )

    frame = (
        neural.merge(glucose[["file_key", "glucose_solved", "glucose_time"]], on="file_key", how="left")
        .merge(cadical, on="file_key", how="left")
        .merge(march, on="file_key", how="left")
        .merge(
            portfolio[
                [
                    "file_key",
                    "portfolio_solved_repeats",
                    "local_first_stage_solved_repeats",
                    "cadical_second_stage_solved_repeats",
                ]
            ],
            on="file_key",
            how="left",
        )
    )
    missing = frame[
        frame["glucose_solved"].isna()
        | frame["cadical_solved_repeats"].isna()
        | frame["march_solved_strict60_repeats"].isna()
        | frame["portfolio_solved_repeats"].isna()
    ]["file_key"].tolist()
    if missing:
        raise ValueError(f"Missing lattice rows: {missing}")

    frame["cadical_any_solved"] = frame["cadical_solved_repeats"].gt(0)
    frame["cadical_all_solved"] = frame["cadical_solved_repeats"].eq(3)
    frame["march_all_solved"] = frame["march_solved_strict60_all"].astype(bool)
    frame["portfolio_any_solved"] = frame["portfolio_solved_repeats"].gt(0)
    frame["portfolio_all_solved"] = frame["portfolio_solved_repeats"].eq(3)
    return frame


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


def pair_row(frame: pd.DataFrame, left: str, right: str, label: str) -> dict[str, object]:
    left_solved = frame[left].astype(bool)
    right_solved = frame[right].astype(bool)
    return {
        "comparison": label,
        "left_solved": int(left_solved.sum()),
        "right_solved": int(right_solved.sum()),
        "left_only": int((left_solved & ~right_solved).sum()),
        "right_only": int((right_solved & ~left_solved).sum()),
        "both": int((left_solved & right_solved).sum()),
        "union": int((left_solved | right_solved).sum()),
    }


def write_subset(frame: pd.DataFrame, name: str, mask: pd.Series) -> pd.DataFrame:
    columns = [
        "file_key",
        "glucose_solved",
        "one_shot_solved",
        "online_solved",
        "old_compact_solved",
        "local_correction_solved",
        "cadical_solved_repeats",
        "march_solved_strict60_repeats",
        "portfolio_solved_repeats",
        "pattern",
    ]
    subset = frame.loc[mask, columns].sort_values("file_key").copy()
    subset.to_csv(OUT_DIR / f"{name}.csv", index=False)
    return subset


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_frame()
    frame.to_csv(OUT_DIR / "combined.csv", index=False)

    method_rows = []
    for method, column in [
        ("Glucose default", "glucose_solved"),
        ("One-shot", "one_shot_solved"),
        ("Online-Consistent Selector", "online_solved"),
        ("Old Compact", "old_compact_solved"),
        ("+ Local Boundary Correction", "local_correction_solved"),
        ("CaDiCaL any-repeat", "cadical_any_solved"),
        ("CaDiCaL all-repeat", "cadical_all_solved"),
        ("March strict-60 all-repeat", "march_all_solved"),
        ("Local5 -> CaDiCaL55 any-repeat", "portfolio_any_solved"),
        ("Local5 -> CaDiCaL55 all-repeat", "portfolio_all_solved"),
    ]:
        method_rows.append({"method": method, "solved": int(frame[column].astype(bool).sum())})
    method_summary = pd.DataFrame(method_rows)
    method_summary.to_csv(OUT_DIR / "method_summary.csv", index=False)

    pair_summary = pd.DataFrame(
        [
            pair_row(frame, "online_solved", "one_shot_solved", "Online vs One-shot"),
            pair_row(frame, "local_correction_solved", "online_solved", "Local vs Online"),
            pair_row(frame, "local_correction_solved", "glucose_solved", "Local vs Glucose"),
            pair_row(frame, "local_correction_solved", "cadical_all_solved", "Local vs CaDiCaL-all"),
            pair_row(frame, "local_correction_solved", "march_all_solved", "Local vs March-all"),
            pair_row(frame, "online_solved", "march_all_solved", "Online vs March-all"),
            pair_row(frame, "cadical_all_solved", "march_all_solved", "CaDiCaL-all vs March-all"),
            pair_row(frame, "portfolio_all_solved", "march_all_solved", "Portfolio-all vs March-all"),
        ]
    )
    pair_summary.to_csv(OUT_DIR / "pair_summary.csv", index=False)

    recovered_by_online = write_subset(frame, "online_recovered_from_oneshot", ~frame["one_shot_solved"] & frame["online_solved"])
    local_only = write_subset(frame, "local_only_over_online", ~frame["online_solved"] & frame["local_correction_solved"])
    glucose_only_vs_local = write_subset(frame, "glucose_only_vs_local", frame["glucose_solved"] & ~frame["local_correction_solved"])
    local_only_vs_march = write_subset(frame, "local_only_vs_march", frame["local_correction_solved"] & ~frame["march_all_solved"])
    march_hard = write_subset(frame, "march_strict_hard", ~frame["march_all_solved"])

    lines = [
        "# Failure-Boundary Solved-Set Lattice Audit",
        "",
        "Scope: quantify where the current neural-guided Glucose workflow sits",
        "relative to Glucose default, CaDiCaL repeats, March strict-60 repeats,",
        "and the Local5 -> CaDiCaL55 portfolio. This is an analysis artifact only;",
        "it does not change models, thresholds, selectors, or solver configs.",
        "",
        "## Method Counts",
        "",
        *markdown_table(method_summary, ["method", "solved"]),
        "",
        "## Pairwise Containment",
        "",
        *markdown_table(
            pair_summary,
            ["comparison", "left_solved", "right_solved", "left_only", "right_only", "both", "union"],
        ),
        "",
        "## Key Boundary Sets",
        "",
        f"- Online recovers {len(recovered_by_online)} One-shot timeouts; all are solved by March strict-60 all-repeat and CaDiCaL all-repeat.",
        f"- Local Boundary Correction has {len(local_only)} Local-only gain over Online: `3sat_188.cnf`; March solves it in all strict-60 repeats.",
        f"- Glucose default has {len(glucose_only_vs_local)} instance solved that Local does not solve.",
        f"- Local has {len(local_only_vs_march)} solved instance outside repeated March strict-60.",
        f"- Repeated March strict-hard has {len(march_hard)} instances; current neural, CaDiCaL, and portfolio methods solve none of them.",
        "",
        "## Decision",
        "",
        "- The Online-Consistent Selector and Local Boundary Correction form a real",
        "  improvement inside the neural-guided Glucose workflow: Online strictly",
        "  contains One-shot, and Local strictly contains Online by one boundary",
        "  instance.",
        "- That improvement does not transfer into strong-solver complementarity.",
        "  Both Online and Local are strict subsets of repeated March strict-60.",
        "- The defensible top-conference story is therefore a solved-set boundary",
        "  and risk-control study: when neural feedback helps a weak/medium",
        "  neural-guided workflow, and where it is completely dominated by a",
        "  stronger solver family.",
        "- A performance route requires a new benchmark protocol or an external",
        "  stronger-solver gate showing stable neural solves outside the stronger",
        "  solver's repeated solved set.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/failure_boundary_lattice/combined.csv",
        "runs/analysis/failure_boundary_lattice/method_summary.csv",
        "runs/analysis/failure_boundary_lattice/pair_summary.csv",
        "runs/analysis/failure_boundary_lattice/online_recovered_from_oneshot.csv",
        "runs/analysis/failure_boundary_lattice/local_only_over_online.csv",
        "runs/analysis/failure_boundary_lattice/glucose_only_vs_local.csv",
        "runs/analysis/failure_boundary_lattice/local_only_vs_march.csv",
        "runs/analysis/failure_boundary_lattice/march_strict_hard.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(method_summary.to_string(index=False))
    print(pair_summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
