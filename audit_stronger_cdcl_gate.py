from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/stronger_cdcl_gate"
DOC_PATH = ROOT / "docs/stronger_cdcl_gate_audit.md"

MARCH_INSTANCE = ROOT / "runs/analysis/march_full400_cpu60/strict60_instance_summary.csv"
NEURAL_OVERLAP = ROOT / "runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv"
CADICAL_INSTANCE = ROOT / "runs/analysis/cadical_repeat_stability/instance_summary.csv"
PORTFOLIO_OVERLAP = ROOT / "runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv"


SOLVER_CANDIDATES = [
    ("Glucose", "solvers/glucose/simp/glucose_static", "available baseline"),
    ("Weighted Glucose", "solvers/glucose_weighted/simp/glucose_static", "available neural workflow solver"),
    ("Weighted Glucose release", "solvers/glucose_weighted/simp/glucose_release", "available neural workflow solver"),
    ("CaDiCaL", "solvers/cadical/cadical", "available stronger CDCL baseline"),
    ("March", "solvers/march/march_nh", "available lookahead solver baseline"),
    ("Weighted March", "solvers/march_weighted/march_nh", "available weighted lookahead solver"),
    ("Kissat", "solvers/kissat/kissat", "missing external stronger CDCL gate"),
    ("MapleSAT", "solvers/maplesat/maplesat", "missing external stronger CDCL gate"),
    ("CryptoMiniSat", "solvers/cryptominisat/cryptominisat5", "missing external stronger CDCL gate"),
]


def executable(path: Path) -> bool:
    return path.exists() and os.access(path, os.X_OK)


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


def solver_availability() -> pd.DataFrame:
    rows = []
    for name, rel_path, role in SOLVER_CANDIDATES:
        path = ROOT / rel_path
        rows.append(
            {
                "solver": name,
                "path": rel_path,
                "present": path.exists(),
                "executable": executable(path),
                "role": role,
            }
        )
    return pd.DataFrame(rows)


def load_overlap() -> pd.DataFrame:
    march = pd.read_csv(MARCH_INSTANCE)
    neural = pd.read_csv(NEURAL_OVERLAP, dtype={"pattern": str})
    neural["pattern"] = neural["pattern"].astype(str).str.zfill(4)
    cadical = pd.read_csv(CADICAL_INSTANCE)
    portfolio = pd.read_csv(PORTFOLIO_OVERLAP, dtype={"pattern": str})

    frame = (
        march.merge(neural, on="file_key", how="left")
        .merge(cadical, on="file_key", how="left", suffixes=("", "_cadical"))
        .merge(portfolio, on="file_key", how="left", suffixes=("", "_portfolio"))
    )
    missing = frame[
        frame["one_shot_solved"].isna()
        | frame["cadical_solved_repeats"].isna()
        | frame["portfolio_solved_repeats"].isna()
    ]["file_key"].tolist()
    if missing:
        raise ValueError(f"Missing overlap rows: {missing}")
    return frame


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    availability = solver_availability()
    availability.to_csv(OUT_DIR / "solver_availability.csv", index=False)

    frame = load_overlap()
    march_hard = frame.loc[~frame["march_solved_strict60_any"].astype(bool)].copy()
    march_hard_columns = [
        "file_key",
        "march_solved_external65_repeats",
        "cadical_solved_repeats",
        "one_shot_solved",
        "online_solved",
        "old_compact_solved",
        "local_correction_solved",
        "portfolio_solved_repeats",
        "pattern",
    ]
    march_hard[march_hard_columns].to_csv(OUT_DIR / "march_strict_hard_overlap.csv", index=False)

    summary_rows = [
        {
            "item": "available_executable_strong_solvers",
            "value": int(
                availability.loc[
                    availability["solver"].isin(["CaDiCaL", "March"]),
                    "executable",
                ].sum()
            ),
            "interpretation": "CaDiCaL and March are the available stronger-solver baselines in this checkout.",
        },
        {
            "item": "missing_external_solver_families",
            "value": int(
                availability.loc[
                    availability["solver"].isin(["Kissat", "MapleSAT", "CryptoMiniSat"]),
                    "executable",
                ].eq(False).sum()
            ),
            "interpretation": "Kissat, MapleSAT, and CryptoMiniSat binaries are absent from this checkout.",
        },
        {
            "item": "march_strict60_hard_instances",
            "value": int(len(march_hard)),
            "interpretation": "Instances unsolved by March under strict 60s in all three repeats.",
        },
        {
            "item": "neural_solved_on_march_hard",
            "value": int(march_hard["local_correction_solved"].astype(bool).sum()),
            "interpretation": "Local Boundary Correction solves none of the repeated-March strict-hard subset.",
        },
        {
            "item": "online_solved_on_march_hard",
            "value": int(march_hard["online_solved"].astype(bool).sum()),
            "interpretation": "Online-Consistent Selector solves none of the repeated-March strict-hard subset.",
        },
        {
            "item": "portfolio_solved_repeats_on_march_hard",
            "value": int(march_hard["portfolio_solved_repeats"].sum()),
            "interpretation": "The Local5 -> CaDiCaL55 portfolio has no solved repeat on the repeated-March strict-hard subset.",
        },
        {
            "item": "cadical_solved_repeats_on_march_hard",
            "value": int(march_hard["cadical_solved_repeats"].sum()),
            "interpretation": "CaDiCaL has no solved repeat on the repeated-March strict-hard subset.",
        },
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "summary.csv", index=False)

    hard_keys = ", ".join(f"`{key}`" for key in march_hard["file_key"].tolist())
    lines = [
        "# Stronger-CDCL Gate Audit",
        "",
        "Scope: evidence gate only. This audit does not change the neural model,",
        "selector thresholds, Local Boundary Correction guard, portfolio schedule,",
        "or solver configurations.",
        "",
        "## Solver Availability",
        "",
        *markdown_table(availability, ["solver", "path", "present", "executable", "role"]),
        "",
        "Current checkout conclusion: CaDiCaL and March are available; Kissat,",
        "MapleSAT, and CryptoMiniSat are not present as executable artifacts.",
        "",
        "## March Strict-Hard Subset",
        "",
        "A decisive top-conference performance claim would require complementarity",
        "on instances that a strong baseline cannot solve. Under repeated March",
        "strict-60, the hard subset contains 16 instances. Current neural and",
        "portfolio methods solve none of them.",
        "",
        *markdown_table(summary, ["item", "value", "interpretation"]),
        "",
        "March strict-hard instance keys:",
        "",
        hard_keys,
        "",
        "Detailed overlap is written to:",
        "",
        "```text",
        "runs/analysis/stronger_cdcl_gate/march_strict_hard_overlap.csv",
        "```",
        "",
        "## Decision",
        "",
        "- The current result cannot support a strong-SAT-baseline performance or",
        "  complementarity claim: the repeated-March strict-hard subset has zero",
        "  neural, CaDiCaL, or Local5 -> CaDiCaL55 portfolio solves.",
        "- The paper can still be made rigorous as a failure-boundary / risk-control",
        "  study: Online-Consistent selection improves a neural-guided Glucose",
        "  workflow, but stronger solver families expose the boundary of that",
        "  improvement.",
        "- To reopen a top-conference performance route, the next hard gate is not",
        "  another neural selector. It is an external stronger-solver artifact",
        "  audit: provide Kissat/MapleSAT/CryptoMiniSat binaries, run the same",
        "  full400 60s protocol with three repeats, and check whether any neural or",
        "  portfolio method solves instances missed by that solver in all repeats.",
        "- If those external solvers also cover all neural-solved instances, the",
        "  only defensible top-conference path is a negative/failure-boundary",
        "  framing or a different benchmark protocol with an explicit rationale.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/stronger_cdcl_gate/solver_availability.csv",
        "runs/analysis/stronger_cdcl_gate/summary.csv",
        "runs/analysis/stronger_cdcl_gate/march_strict_hard_overlap.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
