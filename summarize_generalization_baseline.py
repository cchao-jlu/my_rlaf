from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/generalization_baseline"
SUMMARY_CSV = OUT_DIR / "summary.csv"
PAPER_TABLE_CSV = OUT_DIR / "paper_table.csv"
AUDIT_CSV = OUT_DIR / "audit.csv"
DOC_PATH = ROOT / "docs/paper_generalization_baseline_table.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


SINGLE_RUN_SPECS = [
    (
        300,
        "Glucose default",
        "glucose_default",
        "runs/glucose/solver_stats_300_cpu60.csv",
        "single-run nominal 60s / external 65s guard",
    ),
    (
        300,
        "One-shot",
        "one_shot",
        "runs/analysis/appendix_300350/raw/one_shot_300.csv",
        "appendix same-protocol rerun",
    ),
    (
        300,
        "Online-Consistent Selector",
        "online_consistent_boundary400",
        "runs/analysis/appendix_300350/raw/online_consistent_300.csv",
        "appendix same-protocol rerun; local manifest disabled",
    ),
    (
        300,
        "Old Compact",
        "old_compact",
        "runs/analysis/generalization_baseline/raw/old_compact_300.csv",
        "matched final config rerun; local manifest disabled",
    ),
    (
        350,
        "Glucose default",
        "glucose_default",
        "runs/glucose/solver_stats_350_cpu60.csv",
        "single-run nominal 60s / external 65s guard",
    ),
    (
        350,
        "One-shot",
        "one_shot",
        "runs/analysis/appendix_300350/raw/one_shot_350.csv",
        "appendix same-protocol rerun",
    ),
    (
        350,
        "Online-Consistent Selector",
        "online_consistent_boundary400",
        "runs/analysis/appendix_300350/raw/online_consistent_350.csv",
        "appendix same-protocol rerun; local manifest disabled",
    ),
    (
        350,
        "Old Compact",
        "old_compact",
        "runs/analysis/generalization_baseline/raw/old_compact_350.csv",
        "matched final config rerun; local manifest disabled",
    ),
    (
        400,
        "Glucose default",
        "glucose_default",
        "runs/glucose/solver_stats_full400_cpu60.csv",
        "single-run nominal 60s / external 65s guard",
    ),
    (
        400,
        "CaDiCaL default",
        "cadical_default",
        "runs/cadical/solver_stats_full400_cpu60.csv",
        "single-run CaDiCaL 1.5.2 wall-clock 60s / external 65s guard",
    ),
]


METHOD_ORDER = {
    "glucose_default": 0,
    "cadical_default": 1,
    "one_shot": 2,
    "online_consistent_boundary400": 3,
    "old_compact": 4,
    "local_reopen_guarded": 5,
}


def is_solved(value: object) -> bool:
    return str(value) in SOLVED_RESULTS


def summarize_raw_csv(
    size: int,
    paper_name: str,
    method: str,
    csv_path: str,
    note: str,
) -> dict[str, object]:
    path = ROOT / csv_path
    if not path.exists():
        return {
            "size": size,
            "method": method,
            "paper_name": paper_name,
            "available": False,
            "source_csv": csv_path,
            "protocol": "single_run",
            "note": note,
        }

    frame = pd.read_csv(path)
    solved = frame["Result"].map(is_solved)
    times = pd.to_numeric(frame["time"], errors="coerce")
    return {
        "size": size,
        "method": method,
        "paper_name": paper_name,
        "available": True,
        "total": int(len(frame)),
        "unique_files": int(frame["file"].astype(str).nunique()),
        "solved": int(solved.sum()),
        "timeouts": int((~solved).sum()),
        "mean_time": float(times.mean()),
        "median_time": float(times.median()),
        "max_time": float(times.max()),
        "source_csv": csv_path,
        "protocol": "single_run",
        "note": note,
    }


def add_full400_seed_rows(rows: list[dict[str, object]]) -> None:
    source = ROOT / "runs/analysis/full400_seed_robustness/method_summary.csv"
    if not source.exists():
        return
    frame = pd.read_csv(source)
    for _, row in frame.iterrows():
        rows.append(
            {
                "size": 400,
                "method": row["method"],
                "paper_name": row["paper_name"],
                "available": True,
                "total": 200,
                "unique_files": 200,
                "solved": float(row["solved_mean"]),
                "timeouts": float(200 - row["solved_mean"]),
                "mean_time": float(row["mean_time_mean"]),
                "median_time": float(row["median_time_mean"]),
                "solved_std": float(row["solved_std"]),
                "mean_time_std": float(row["mean_time_std"]),
                "source_csv": "runs/analysis/full400_seed_robustness/method_summary.csv",
                "protocol": "3_seed_robustness",
                "note": "seeds 1/2/3; Local Boundary Correction only appears at 400",
            }
        )


def write_audit() -> pd.DataFrame:
    audit = pd.DataFrame(
        [
            {
                "item": "One-shot 300/350",
                "status": "reused",
                "reason": "current appendix rerun exists for 200 instances; old drift-prone CSVs not used",
                "source": "runs/analysis/appendix_300350/raw/one_shot_{300,350}.csv",
            },
            {
                "item": "Online-Consistent 300/350",
                "status": "reused",
                "reason": "current appendix rerun exists for 200 instances with local_reopen_candidate_manifest=null",
                "source": "runs/analysis/appendix_300350/raw/online_consistent_{300,350}.csv",
            },
            {
                "item": "Glucose default 300/350",
                "status": "new run",
                "reason": "only full400 had the same nominal 60s / external 65s baseline; old runs/glucose/solver_stats.csv uses a long CPU limit",
                "source": "runs/glucose/solver_stats_{300,350}_cpu60.csv",
            },
            {
                "item": "CaDiCaL default full400",
                "status": "new run",
                "reason": "top-conference baseline audit needed a stronger unguided CDCL reference than Glucose default",
                "source": "runs/cadical/solver_stats_full400_cpu60.csv",
            },
            {
                "item": "Old Compact 300/350",
                "status": "new run",
                "reason": "historical eval_compact_risk_disjoint_{300,350}.csv covers only 100 disjoint instances",
                "source": "runs/analysis/generalization_baseline/raw/old_compact_{300,350}.csv",
            },
            {
                "item": "Local Boundary Correction 300/350",
                "status": "not run",
                "reason": "400-boundary guarded correction; do not migrate to 300/350",
                "source": "",
            },
            {
                "item": "Full400 neural methods",
                "status": "reused",
                "reason": "use existing 3-seed robustness table as the main full400 result",
                "source": "runs/analysis/full400_seed_robustness/method_summary.csv",
            },
        ]
    )
    audit.to_csv(AUDIT_CSV, index=False)
    return audit


def format_solved(value: object, protocol: str) -> str:
    solved = float(value)
    if protocol == "3_seed_robustness":
        return f"{solved:.1f}"
    return f"{int(round(solved))}"


def write_doc(paper: pd.DataFrame, audit: pd.DataFrame) -> None:
    lines = [
        "# Generalization / Baseline Robustness Table",
        "",
        "Scope: broaden the evidence around the final selector without tuning any",
        "thresholds, adding selector branches, or moving Local Boundary Correction to",
        "300/350.",
        "",
        "## Audit Result",
        "",
        "| Item | Status | Reason | Source |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in audit.iterrows():
        lines.append(
            f"| {row['item']} | {row['status']} | {row['reason']} | `{row['source']}` |"
        )

    lines.extend(
        [
            "",
            "## Paper-Ready Table",
            "",
            "Caption:",
            "",
            "> Generalization and baseline robustness across held-out 3SAT sizes. The",
            "> 300/350 rows are single-run appendix checks under the frozen protocol.",
            "> The 400 neural rows are the main 3-seed solver robustness results.",
            "> Local Boundary Correction is only evaluated on the 400-boundary setting.",
            "",
            "| Size | Method | Protocol | Solved / 200 | Mean time (s) | Median time (s) | Source |",
            "| ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in paper.iterrows():
        lines.append(
            "| "
            f"{int(row['size'])} | {row['paper_name']} | {row['protocol']} | "
            f"{format_solved(row['solved'], row['protocol'])} | "
            f"{float(row['mean_time']):.3f} | {float(row['median_time']):.3f} | "
            f"`{row['source_csv']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The result is not a full400-only story: on 300, Online-Consistent",
            "  preserves solved count and is faster than both One-shot and Old Compact;",
            "  on 350, it improves solved count over One-shot and Old Compact in this",
            "  frozen single-run appendix protocol.",
            "- Glucose default and CaDiCaL default are unguided CDCL references, not",
            "  neural baselines. Glucose is strong on 300 but falls behind the",
            "  neural-guided methods on 350 and 400 under the nominal 60s budget.",
            "  CaDiCaL is stronger than the neural-guided Glucose workflow on full400,",
            "  so the paper should not claim dominance over modern CDCL defaults.",
            "- Old Compact remains a strong baseline. It matches Online-Consistent",
            "  solved count on 300 but is slower in mean time, is weaker in solved",
            "  count on 350, and reaches one more solved instance on full400 before",
            "  Local Boundary Correction matches its solved count and lowers mean time.",
            "- Local Boundary Correction stays 400-only because the formal rule is a",
            "  guarded boundary correction tied to the 400 candidate manifest.",
            "",
            "## Generated Artifacts",
            "",
            f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
            f"- `{PAPER_TABLE_CSV.relative_to(ROOT)}`",
            f"- `{AUDIT_CSV.relative_to(ROOT)}`",
            "",
            "Regenerate with:",
            "",
            "```bash",
            "/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_generalization_baseline.py",
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        summarize_raw_csv(size, paper_name, method, csv_path, note)
        for size, paper_name, method, csv_path, note in SINGLE_RUN_SPECS
    ]
    add_full400_seed_rows(rows)

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY_CSV, index=False)

    paper = summary[summary["available"] == True].copy()
    paper["method_order"] = paper["method"].map(METHOD_ORDER).fillna(99)
    paper = paper.sort_values(["size", "method_order"])
    paper.to_csv(PAPER_TABLE_CSV, index=False)

    audit = write_audit()
    write_doc(paper, audit)

    print(SUMMARY_CSV.relative_to(ROOT))
    print(PAPER_TABLE_CSV.relative_to(ROOT))
    print(AUDIT_CSV.relative_to(ROOT))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
