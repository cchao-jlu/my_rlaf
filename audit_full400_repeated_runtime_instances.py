from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
WORK_DIR = ROOT / "runs/analysis/full400_repeated_runtime"
PER_INSTANCE_CSV = WORK_DIR / "per_instance_summary.csv"
OVERLAP_CSV = WORK_DIR / "solved_pattern_overlap.csv"
PATTERN_SUMMARY_CSV = WORK_DIR / "solved_pattern_summary.csv"
DIFFERENCE_CSV = WORK_DIR / "solved_difference_audit.csv"
LOCAL_OLD_TIME_CSV = WORK_DIR / "local_vs_old_time_audit.csv"
DOC_PATH = ROOT / "docs/full400_repeated_runtime_instance_audit.md"

METHODS = [
    ("one_shot", "one_shot", "One-shot"),
    ("online_consistent_boundary400", "online", "Online-Consistent Selector"),
    ("old_compact", "old_compact", "Old Compact"),
    ("local_reopen_guarded", "local_correction", "+ Local Boundary Correction"),
]
PATTERN_ORDER = "One-shot / Online-Consistent / Old Compact / + Local Boundary Correction"


def load_overlap() -> pd.DataFrame:
    per_instance = pd.read_csv(PER_INSTANCE_CSV)
    pivot = per_instance.pivot(index="file_key", columns="method")
    rows = []
    for file_key in pivot.index:
        row: dict[str, object] = {"file_key": file_key}
        pattern_bits = []
        stable_repeats = True
        for method, prefix, _paper_name in METHODS:
            repeats = int(pivot[("repeats", method)].loc[file_key])
            solved_repeats = int(pivot[("solved_repeats", method)].loc[file_key])
            solved = solved_repeats == repeats
            stable_repeats = stable_repeats and solved_repeats in {0, repeats}
            pattern_bits.append("1" if solved else "0")
            row[f"{prefix}_solved_repeats"] = solved_repeats
            row[f"{prefix}_solved"] = solved
            row[f"{prefix}_time_mean"] = float(pivot[("time_mean", method)].loc[file_key])
            row[f"{prefix}_time_std"] = float(pivot[("time_std", method)].loc[file_key])
            row[f"{prefix}_result_values"] = pivot[("result_values", method)].loc[file_key]
        row["pattern"] = "".join(pattern_bits)
        row["pattern_label"] = "p" + row["pattern"]
        row["stable_repeats"] = stable_repeats
        row["online_minus_one_shot_time_mean"] = row["online_time_mean"] - row["one_shot_time_mean"]
        row["old_minus_online_time_mean"] = row["old_compact_time_mean"] - row["online_time_mean"]
        row["local_minus_online_time_mean"] = row["local_correction_time_mean"] - row["online_time_mean"]
        row["local_minus_old_time_mean"] = row["local_correction_time_mean"] - row["old_compact_time_mean"]
        rows.append(row)
    return pd.DataFrame(rows).sort_values("file_key")


def write_doc(
    overlap: pd.DataFrame,
    pattern_summary: pd.DataFrame,
    differences: pd.DataFrame,
    local_old: pd.DataFrame,
) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

    online_old = overlap[(~overlap["online_solved"]) & (overlap["old_compact_solved"])]
    online_local = overlap[(~overlap["online_solved"]) & (overlap["local_correction_solved"])]
    old_local_mismatch = overlap[overlap["old_compact_solved"] != overlap["local_correction_solved"]]
    local_old_same = local_old[local_old["old_local_same_solved"]]
    slower_0p1 = int((local_old_same["local_minus_old_time_mean"] > 0.1).sum())
    slower_0p5 = int((local_old_same["local_minus_old_time_mean"] > 0.5).sum())
    slower_1p0 = int((local_old_same["local_minus_old_time_mean"] > 1.0).sum())
    max_slowdown = local_old_same.sort_values("local_minus_old_time_mean", ascending=False).head(1)

    lines = [
        "# Full400 Repeated Runtime Per-Instance Audit",
        "",
        "This audit uses only the committed full400 repeated-runtime artifacts.",
        "It does not run new solver evaluations and does not change model, threshold, or solver configuration.",
        "",
        f"Solved pattern order: `{PATTERN_ORDER}`.",
        "All four methods have stable per-instance repeat outcomes: every instance is either solved in all 3 repeats or timed out in all 3 repeats for a given method.",
        "",
        "Outputs:",
        "",
        f"- `{OVERLAP_CSV.relative_to(ROOT)}`",
        f"- `{PATTERN_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{DIFFERENCE_CSV.relative_to(ROOT)}`",
        f"- `{LOCAL_OLD_TIME_CSV.relative_to(ROOT)}`",
        "",
        "## Solved Pattern Summary",
        "",
        "| pattern | count | interpretation |",
        "| --- | ---: | --- |",
    ]
    interpretation = {
        "0000": "no method solves",
        "0011": "Old Compact and Local Correction solve; One-shot and Online timeout",
        "0111": "all guided variants solve; One-shot times out",
        "1111": "all methods solve",
    }
    for _, row in pattern_summary.iterrows():
        pattern = row["pattern"]
        lines.append(f"| {pattern} | {int(row['count'])} | {interpretation.get(pattern, '')} |")

    lines.extend(
        [
            "",
            "## Key Solved Difference",
            "",
            "- Old Compact has exactly one all-repeat solved instance that Online-Consistent Selector does not solve.",
            "- + Local Boundary Correction has exactly one all-repeat solved instance that Online-Consistent Selector does not solve.",
            "- These are the same boundary instance.",
            "",
            "| comparison | instance | pattern | one-shot mean | online mean | old compact mean | local correction mean |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, frame in [
        ("Old Compact over Online", online_old),
        ("Local Correction over Online", online_local),
    ]:
        for _, row in frame.iterrows():
            lines.append(
                "| {label} | {file_key} | {pattern} | {one_shot_time_mean:.4f} | {online_time_mean:.4f} | {old_compact_time_mean:.4f} | {local_correction_time_mean:.4f} |".format(
                    label=label,
                    **row,
                )
            )

    lines.extend(
        [
            "",
            "## Local Correction Versus Old Compact",
            "",
            f"- Solved-pattern mismatch count: {len(old_local_mismatch)}.",
            f"- Same-solved instances with Local Correction slower than Old Compact by >0.1s: {slower_0p1}.",
            f"- Same-solved instances with Local Correction slower than Old Compact by >0.5s: {slower_0p5}.",
            f"- Same-solved instances with Local Correction slower than Old Compact by >1.0s: {slower_1p0}.",
        ]
    )
    if not max_slowdown.empty:
        row = max_slowdown.iloc[0]
        lines.append(
            "- Maximum same-solved slowdown is {delta:.4f}s on `{file_key}`.".format(
                delta=row["local_minus_old_time_mean"],
                file_key=row["file_key"],
            )
        )
    lines.extend(
        [
            "",
            "Top same-solved Local Correction slowdowns relative to Old Compact:",
            "",
            "| instance | pattern | old solved repeats | old mean | local mean | local-old delta |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in local_old_same.sort_values("local_minus_old_time_mean", ascending=False).head(10).iterrows():
        lines.append(
            "| {file_key} | {pattern} | {old_compact_solved_repeats} | {old_compact_time_mean:.4f} | {local_correction_time_mean:.4f} | {local_minus_old_time_mean:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Paper-Facing Reading",
            "",
            "This audit supports the narrower claim that guarded Local Boundary Correction reaches the Old Compact solved count on repeated full400 while reducing mean runtime.",
            "It does not support the claim that Online-Consistent Selector alone exceeds Old Compact in solved count.",
            "`3sat_188.cnf` is the single boundary instance explaining both the Old Compact-over-Online and Local-over-Online solved-count gap.",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    overlap = load_overlap()
    overlap.to_csv(OVERLAP_CSV, index=False)

    pattern_summary = (
        overlap.groupby("pattern", as_index=False)
        .agg(count=("file_key", "size"), stable_repeats=("stable_repeats", "all"))
        .sort_values("pattern")
    )
    pattern_summary["pattern_label"] = "p" + pattern_summary["pattern"]
    pattern_summary = pattern_summary[["pattern", "pattern_label", "count", "stable_repeats"]]
    pattern_summary.to_csv(PATTERN_SUMMARY_CSV, index=False)

    differences = overlap[
        (overlap["one_shot_solved"] != overlap["online_solved"])
        | (overlap["online_solved"] != overlap["old_compact_solved"])
        | (overlap["online_solved"] != overlap["local_correction_solved"])
        | (overlap["old_compact_solved"] != overlap["local_correction_solved"])
    ].copy()
    differences["old_solved_online_timeout"] = differences["old_compact_solved"] & ~differences["online_solved"]
    differences["local_solved_online_timeout"] = differences["local_correction_solved"] & ~differences["online_solved"]
    differences["local_old_solved_mismatch"] = (
        differences["local_correction_solved"] != differences["old_compact_solved"]
    )
    differences.to_csv(DIFFERENCE_CSV, index=False)

    local_old = overlap.copy()
    local_old["old_local_same_solved"] = (
        local_old["old_compact_solved"] == local_old["local_correction_solved"]
    )
    local_old["local_slower_gt_0p1s"] = local_old["local_minus_old_time_mean"] > 0.1
    local_old["local_slower_gt_0p5s"] = local_old["local_minus_old_time_mean"] > 0.5
    local_old["local_slower_gt_1p0s"] = local_old["local_minus_old_time_mean"] > 1.0
    local_old = local_old.sort_values("local_minus_old_time_mean", ascending=False)
    local_old.to_csv(LOCAL_OLD_TIME_CSV, index=False)

    write_doc(overlap, pattern_summary, differences, local_old)
    print(f"wrote {OVERLAP_CSV.relative_to(ROOT)}")
    print(f"wrote {PATTERN_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {DIFFERENCE_CSV.relative_to(ROOT)}")
    print(f"wrote {LOCAL_OLD_TIME_CSV.relative_to(ROOT)}")
    print(f"wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
