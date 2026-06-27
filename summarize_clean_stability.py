from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    path_template: str


METHODS = [
    MethodSpec(
        key="oneshot",
        label="one-shot",
        path_template="runs/GNN_Glucose_3SAT_V1/eval_oneshot_{size}_optimized_events_gated.csv",
    ),
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
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/clean_stability_and_cactus_results.md")


def load_eval(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"] != "INDETERMINATE"
    return frame


def metric_row(size: int, method: MethodSpec, frame: pd.DataFrame) -> dict[str, object]:
    return {
        "size": size,
        "method": method.label,
        "n": int(len(frame)),
        "solved": int(frame["solved"].sum()),
        "mean_time": float(frame["time"].mean()),
        "median_time": float(frame["time"].median()),
        "p75_time": float(frame["time"].quantile(0.75)),
        "p95_time": float(frame["time"].quantile(0.95)),
        "mean_conflicts": float(frame["conflicts"].mean()),
        "mean_decisions": float(frame["decisions"].mean()),
    }


def paired_frame(base: pd.DataFrame, method: pd.DataFrame) -> pd.DataFrame:
    columns = ["file_key", "time", "solved", "conflicts", "decisions"]
    return (
        base[columns]
        .rename(
            columns={
                "time": "base_time",
                "solved": "base_solved",
                "conflicts": "base_conflicts",
                "decisions": "base_decisions",
            }
        )
        .merge(
            method[columns].rename(
                columns={
                    "time": "method_time",
                    "solved": "method_solved",
                    "conflicts": "method_conflicts",
                    "decisions": "method_decisions",
                }
            ),
            on="file_key",
            how="inner",
        )
    )


def bootstrap_summary(
    paired: pd.DataFrame,
    rng: np.random.Generator,
    iterations: int = 2000,
) -> dict[str, float]:
    n = len(paired)
    base_time = paired["base_time"].to_numpy(dtype=np.float64)
    method_time = paired["method_time"].to_numpy(dtype=np.float64)
    base_solved = paired["base_solved"].to_numpy(dtype=np.float64)
    method_solved = paired["method_solved"].to_numpy(dtype=np.float64)
    indices = rng.integers(0, n, size=(iterations, n))
    delta_time = method_time[indices].mean(axis=1) - base_time[indices].mean(axis=1)
    delta_solved = method_solved[indices].sum(axis=1) - base_solved[indices].sum(axis=1)
    return {
        "bootstrap_delta_time_mean": float(delta_time.mean()),
        "bootstrap_delta_time_ci_low": float(np.quantile(delta_time, 0.025)),
        "bootstrap_delta_time_ci_high": float(np.quantile(delta_time, 0.975)),
        "bootstrap_time_improve_prob": float((delta_time < 0.0).mean()),
        "bootstrap_delta_solved_mean": float(delta_solved.mean()),
        "bootstrap_delta_solved_ci_low": float(np.quantile(delta_solved, 0.025)),
        "bootstrap_delta_solved_ci_high": float(np.quantile(delta_solved, 0.975)),
        "bootstrap_solved_improve_prob": float((delta_solved > 0.0).mean()),
    }


def split_summary(
    paired: pd.DataFrame,
    rng: np.random.Generator,
    iterations: int = 2000,
    split_size: int = 100,
) -> dict[str, float]:
    n = len(paired)
    size = min(split_size, n)
    base_time = paired["base_time"].to_numpy(dtype=np.float64)
    method_time = paired["method_time"].to_numpy(dtype=np.float64)
    base_solved = paired["base_solved"].to_numpy(dtype=np.float64)
    method_solved = paired["method_solved"].to_numpy(dtype=np.float64)

    delta_times = []
    delta_solved = []
    for _ in range(iterations):
        indices = rng.choice(n, size=size, replace=False)
        delta_times.append(float(method_time[indices].mean() - base_time[indices].mean()))
        delta_solved.append(float(method_solved[indices].sum() - base_solved[indices].sum()))
    delta_times = np.asarray(delta_times, dtype=np.float64)
    delta_solved = np.asarray(delta_solved, dtype=np.float64)
    return {
        "split_size": int(size),
        "split_delta_time_mean": float(delta_times.mean()),
        "split_delta_time_ci_low": float(np.quantile(delta_times, 0.025)),
        "split_delta_time_ci_high": float(np.quantile(delta_times, 0.975)),
        "split_time_improve_rate": float((delta_times < 0.0).mean()),
        "split_delta_solved_mean": float(delta_solved.mean()),
        "split_delta_solved_ci_low": float(np.quantile(delta_solved, 0.025)),
        "split_delta_solved_ci_high": float(np.quantile(delta_solved, 0.975)),
        "split_solved_improve_rate": float((delta_solved > 0.0).mean()),
    }


def format_float(value: object, digits: int = 4) -> str:
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(format_float(row[column], digits) for column in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    rng = np.random.default_rng(1729)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded: dict[tuple[int, str], pd.DataFrame] = {}
    metric_rows = []
    for size in SIZES:
        for method in METHODS:
            path = Path(method.path_template.format(size=size))
            if not path.exists():
                continue
            frame = load_eval(path)
            loaded[(size, method.key)] = frame
            metric_rows.append(metric_row(size, method, frame))

    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(OUT_DIR / "clean_metrics_summary.csv", index=False)

    stability_rows = []
    baseline = METHODS[0]
    for size in SIZES:
        base_frame = loaded.get((size, baseline.key))
        if base_frame is None:
            continue
        for method in METHODS[1:]:
            method_frame = loaded.get((size, method.key))
            if method_frame is None:
                continue
            paired = paired_frame(base_frame, method_frame)
            row = {
                "size": size,
                "method": method.label,
                "n": int(len(paired)),
                "delta_mean_time": float(paired["method_time"].mean() - paired["base_time"].mean()),
                "delta_solved": int(paired["method_solved"].sum() - paired["base_solved"].sum()),
                "delta_mean_conflicts": float(
                    paired["method_conflicts"].mean() - paired["base_conflicts"].mean()
                ),
                "delta_mean_decisions": float(
                    paired["method_decisions"].mean() - paired["base_decisions"].mean()
                ),
            }
            row.update(bootstrap_summary(paired, rng=rng))
            row.update(split_summary(paired, rng=rng))
            stability_rows.append(row)

    stability = pd.DataFrame(stability_rows)
    stability.to_csv(OUT_DIR / "clean_stability_vs_oneshot.csv", index=False)

    doc = [
        "# Clean Stability and Cactus Results",
        "",
        "This note summarizes the clean optimized-binary 3SAT-300/350/400 runs.",
        "It uses existing CSV files only; no solver run is performed by this script.",
        "",
        "Generated artifacts:",
        "",
        "- `figures/fig_clean_cactus_3sat_300_350_400.pdf`",
        "- `figures/fig_clean_cactus_3sat_300.pdf`",
        "- `figures/fig_clean_cactus_3sat_350.pdf`",
        "- `figures/fig_clean_cactus_3sat_400.pdf`",
        "- `runs/analysis/clean_metrics_summary.csv`",
        "- `runs/analysis/clean_stability_vs_oneshot.csv`",
        "",
        "## Mean Metrics",
        "",
        markdown_table(
            metrics[
                [
                    "size",
                    "method",
                    "n",
                    "solved",
                    "mean_time",
                    "median_time",
                    "mean_conflicts",
                    "mean_decisions",
                ]
            ],
            [
                "size",
                "method",
                "n",
                "solved",
                "mean_time",
                "median_time",
                "mean_conflicts",
                "mean_decisions",
            ],
        ),
        "",
        "## Stability Against One-Shot",
        "",
        "`delta_mean_time < 0` means faster than one-shot. The bootstrap is paired",
        "over instances; the split columns repeatedly sample 100-instance held-out",
        "subsets without replacement to mimic split-level robustness.",
        "",
        markdown_table(
            stability[
                [
                    "size",
                    "method",
                    "delta_mean_time",
                    "bootstrap_delta_time_ci_low",
                    "bootstrap_delta_time_ci_high",
                    "bootstrap_time_improve_prob",
                    "delta_solved",
                    "split_time_improve_rate",
                    "split_solved_improve_rate",
                ]
            ],
            [
                "size",
                "method",
                "delta_mean_time",
                "bootstrap_delta_time_ci_low",
                "bootstrap_delta_time_ci_high",
                "bootstrap_time_improve_prob",
                "delta_solved",
                "split_time_improve_rate",
                "split_solved_improve_rate",
            ],
        ),
        "",
        "## Reading",
        "",
        "- Fixed-rho is a stable 300 improvement but weak on 350/400.",
        "- Polarity-gate-min095 is safe but mostly tracks fixed-rho.",
        "- Conservative SBE polarity has a useful 350 signal, but the 400 result",
        "  is negative; it should be treated as a hypothesis, not a main claim.",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")
    print(f"wrote {OUT_DIR / 'clean_metrics_summary.csv'}")
    print(f"wrote {OUT_DIR / 'clean_stability_vs_oneshot.csv'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
