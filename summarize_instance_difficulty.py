from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    path_template: str


BASELINE = MethodSpec(
    key="oneshot",
    label="one-shot",
    path_template="runs/GNN_Glucose_3SAT_V1/eval_oneshot_{size}_optimized_events_gated.csv",
)

METHODS = [
    MethodSpec(
        key="fixed_rho",
        label="fixed-rho",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
            "eval_trace_adapter_rho_gate_{size}_optimized_events_gated.csv"
        ),
    ),
    MethodSpec(
        key="polarity_gate_min095",
        label="polarity-gate-min095",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_PolarityGateMin095/"
            "eval_polarity_gate_min095_{size}_optimized_events_gated.csv"
        ),
    ),
    MethodSpec(
        key="sbe_polarity_conservative",
        label="conservative SBE polarity",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarityConservative/"
            "eval_sbe_polarity_conservative_{size}_optimized_events_gated.csv"
        ),
    ),
]

SIZES = [300, 350, 400]
METHOD_ORDER = {method.label: index for index, method in enumerate(METHODS)}
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/per_instance_win_loss_difficulty.md")
WIN_EPS = 0.1


def load_eval(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"] != "INDETERMINATE"
    return frame


def difficulty_bucket(row: pd.Series) -> str:
    if not bool(row["base_solved"]):
        return "timeout"
    time = float(row["base_time"])
    if time < 10.0:
        return "easy(<10s)"
    if time < 30.0:
        return "medium(10-30s)"
    return "hard(>=30s)"


def outcome(row: pd.Series) -> str:
    base_solved = bool(row["base_solved"])
    method_solved = bool(row["method_solved"])
    delta = float(row["delta_time"])
    if base_solved and method_solved:
        if delta < -WIN_EPS:
            return "faster_both_solved"
        if delta > WIN_EPS:
            return "slower_both_solved"
        return "tie_both_solved"
    if not base_solved and method_solved:
        return "recovered_timeout"
    if base_solved and not method_solved:
        return "lost_solution"
    return "both_timeout"


def compare_method(size: int, method: MethodSpec) -> pd.DataFrame:
    base = load_eval(Path(BASELINE.path_template.format(size=size)))
    current = load_eval(Path(method.path_template.format(size=size)))
    columns = ["file_key", "Result", "solved", "time", "conflicts", "decisions", "CPU time"]
    merged = (
        base[columns]
        .rename(
            columns={
                "Result": "base_result",
                "solved": "base_solved",
                "time": "base_time",
                "conflicts": "base_conflicts",
                "decisions": "base_decisions",
                "CPU time": "base_cpu_time",
            }
        )
        .merge(
            current[columns].rename(
                columns={
                    "Result": "method_result",
                    "solved": "method_solved",
                    "time": "method_time",
                    "conflicts": "method_conflicts",
                    "decisions": "method_decisions",
                    "CPU time": "method_cpu_time",
                }
            ),
            on="file_key",
            how="inner",
        )
    )
    merged.insert(0, "size", size)
    merged.insert(1, "method", method.label)
    merged["delta_time"] = merged["method_time"] - merged["base_time"]
    merged["delta_cpu_time"] = merged["method_cpu_time"] - merged["base_cpu_time"]
    merged["delta_conflicts"] = merged["method_conflicts"] - merged["base_conflicts"]
    merged["delta_decisions"] = merged["method_decisions"] - merged["base_decisions"]
    merged["difficulty_bucket"] = merged.apply(difficulty_bucket, axis=1)
    merged["outcome"] = merged.apply(outcome, axis=1)
    merged["is_win"] = merged["outcome"].isin(["faster_both_solved", "recovered_timeout"])
    merged["is_loss"] = merged["outcome"].isin(["slower_both_solved", "lost_solution"])
    return merged


def summarize_overall(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (size, method), group in frame.groupby(["size", "method"], sort=False):
        counts = group["outcome"].value_counts()
        rows.append(
            {
                "size": size,
                "method": method,
                "n": int(len(group)),
                "wins": int(group["is_win"].sum()),
                "losses": int(group["is_loss"].sum()),
                "neutral": int(len(group) - group["is_win"].sum() - group["is_loss"].sum()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
                "delta_solved": int(group["method_solved"].sum() - group["base_solved"].sum()),
                "delta_mean_time": float(group["delta_time"].mean()),
                "median_delta_time": float(group["delta_time"].median()),
                "delta_mean_conflicts": float(group["delta_conflicts"].mean()),
                "delta_mean_decisions": float(group["delta_decisions"].mean()),
            }
        )
    result = pd.DataFrame(rows)
    result["method_order"] = result["method"].map(METHOD_ORDER)
    return result.sort_values(["size", "method_order"]).drop(columns=["method_order"])


def summarize_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    bucket_order = ["easy(<10s)", "medium(10-30s)", "hard(>=30s)", "timeout"]
    rows = []
    for (size, method, bucket), group in frame.groupby(
        ["size", "method", "difficulty_bucket"],
        sort=False,
    ):
        counts = group["outcome"].value_counts()
        rows.append(
            {
                "size": size,
                "method": method,
                "bucket": bucket,
                "bucket_order": bucket_order.index(bucket),
                "n": int(len(group)),
                "base_solved": int(group["base_solved"].sum()),
                "method_solved": int(group["method_solved"].sum()),
                "delta_solved": int(group["method_solved"].sum() - group["base_solved"].sum()),
                "base_mean_time": float(group["base_time"].mean()),
                "method_mean_time": float(group["method_time"].mean()),
                "delta_mean_time": float(group["delta_time"].mean()),
                "median_delta_time": float(group["delta_time"].median()),
                "wins": int(group["is_win"].sum()),
                "losses": int(group["is_loss"].sum()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
                "delta_mean_conflicts": float(group["delta_conflicts"].mean()),
                "delta_mean_decisions": float(group["delta_decisions"].mean()),
            }
        )
    result = pd.DataFrame(rows)
    result["method_order"] = result["method"].map(METHOD_ORDER)
    return result.sort_values(["size", "method_order", "bucket_order"]).drop(
        columns=["method_order", "bucket_order"]
    )


def top_changes(frame: pd.DataFrame, size: int, method: str, n: int = 5) -> pd.DataFrame:
    subset = frame[(frame["size"] == size) & (frame["method"] == method)].copy()
    if subset.empty:
        return pd.DataFrame()
    columns = [
        "file_key",
        "difficulty_bucket",
        "base_result",
        "method_result",
        "base_time",
        "method_time",
        "delta_time",
        "outcome",
        "delta_conflicts",
        "delta_decisions",
    ]
    best = subset.nsmallest(n, "delta_time")[columns].copy()
    worst = subset.nlargest(n, "delta_time")[columns].copy()
    best.insert(0, "change_type", "largest_win")
    worst.insert(0, "change_type", "largest_loss")
    return pd.concat([best, worst], ignore_index=True)


def format_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(format_value(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_doc(
    overall: pd.DataFrame,
    buckets: pd.DataFrame,
    change_examples: pd.DataFrame,
) -> None:
    overall_cols = [
        "size",
        "method",
        "wins",
        "losses",
        "neutral",
        "recovered_timeout",
        "lost_solution",
        "delta_solved",
        "delta_mean_time",
        "median_delta_time",
    ]
    bucket_cols = [
        "size",
        "method",
        "bucket",
        "n",
        "delta_solved",
        "delta_mean_time",
        "wins",
        "losses",
        "recovered_timeout",
        "lost_solution",
        "both_timeout",
    ]
    example_cols = [
        "change_type",
        "file_key",
        "difficulty_bucket",
        "base_result",
        "method_result",
        "base_time",
        "method_time",
        "delta_time",
        "outcome",
    ]
    doc = [
        "# Per-Instance Win/Loss and Difficulty Bucket Report",
        "",
        "This report compares clean optimized-binary runs against the one-shot",
        "baseline on the same CNF instances. A win/loss threshold of `0.1s` is used",
        "for instances solved by both methods. Timeout recovery and lost solutions",
        "are counted as wins and losses respectively.",
        "",
        "Generated CSV files:",
        "",
        "- `runs/analysis/per_instance_method_deltas.csv`",
        "- `runs/analysis/per_instance_win_loss_summary.csv`",
        "- `runs/analysis/difficulty_bucket_summary.csv`",
        "- `runs/analysis/largest_instance_changes.csv`",
        "",
        "## Overall Win/Loss",
        "",
        markdown_table(overall[overall_cols], overall_cols),
        "",
        "## Difficulty Buckets",
        "",
        "Buckets are defined by one-shot baseline behavior: solved under `10s`,",
        "solved in `10-30s`, solved after `30s`, or timeout.",
        "",
        markdown_table(buckets[bucket_cols], bucket_cols),
        "",
        "## Largest Instance-Level Changes",
        "",
        "The examples below focus on the main ambiguous signal: conservative SBE",
        "polarity on 3SAT-350 and 3SAT-400.",
        "",
        markdown_table(change_examples[example_cols], example_cols),
        "",
        "## Reading",
        "",
        "- Fixed-rho mainly helps 3SAT-300 by shaving time on already-solved",
        "  easy/medium/hard instances; it does not recover new hard timeouts.",
        "- On 3SAT-350, conservative SBE polarity wins mostly through the timeout",
        "  bucket: it recovers more one-shot timeouts than it loses solved instances.",
        "- On 3SAT-400, conservative SBE polarity loses solved instances and has no",
        "  compensating timeout recovery, so the 350 signal is not scale-robust.",
        "- A future selector should be trained as a risk controller: predict when",
        "  event guidance is likely to recover timeout/hard instances without losing",
        "  already-solvable instances, rather than only predicting small runtime gain.",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparisons = []
    for size in SIZES:
        for method in METHODS:
            path = Path(method.path_template.format(size=size))
            if path.exists():
                comparisons.append(compare_method(size, method))
    per_instance = pd.concat(comparisons, ignore_index=True)
    overall = summarize_overall(per_instance)
    buckets = summarize_buckets(per_instance)
    change_examples = pd.concat(
        [
            top_changes(per_instance, 350, "conservative SBE polarity"),
            top_changes(per_instance, 400, "conservative SBE polarity"),
        ],
        ignore_index=True,
    )

    per_instance.to_csv(OUT_DIR / "per_instance_method_deltas.csv", index=False)
    overall.to_csv(OUT_DIR / "per_instance_win_loss_summary.csv", index=False)
    buckets.to_csv(OUT_DIR / "difficulty_bucket_summary.csv", index=False)
    change_examples.to_csv(OUT_DIR / "largest_instance_changes.csv", index=False)
    write_doc(overall, buckets, change_examples)

    print(f"wrote {OUT_DIR / 'per_instance_method_deltas.csv'}")
    print(f"wrote {OUT_DIR / 'per_instance_win_loss_summary.csv'}")
    print(f"wrote {OUT_DIR / 'difficulty_bucket_summary.csv'}")
    print(f"wrote {OUT_DIR / 'largest_instance_changes.csv'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
