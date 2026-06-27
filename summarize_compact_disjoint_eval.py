from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


@dataclass(frozen=True)
class EvalSpec:
    size: int
    split_name: str
    baseline_path: Path
    compact_path: Path


SPECS = [
    EvalSpec(
        size=300,
        split_name="heldout_test/300",
        baseline_path=Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_disjoint_compact_300.csv"),
        compact_path=Path(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
            "eval_compact_risk_disjoint_300.csv"
        ),
    ),
    EvalSpec(
        size=350,
        split_name="heldout_test/350",
        baseline_path=Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_disjoint_compact_350.csv"),
        compact_path=Path(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
            "eval_compact_risk_disjoint_350.csv"
        ),
    ),
    EvalSpec(
        size=400,
        split_name="hard_recovery_heldout/400",
        baseline_path=Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_disjoint_compact_400.csv"),
        compact_path=Path(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
            "eval_compact_risk_disjoint_400.csv"
        ),
    ),
]

OUT_DIR = Path("runs/analysis")
FIG_DIR = Path("figures")
DOC_PATH = Path("docs/compact_risk_disjoint_eval.md")
WIN_EPS = 0.1
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def load_eval(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"].map(is_solved)
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
    compact_solved = bool(row["compact_solved"])
    delta = float(row["delta_time"])
    if base_solved and compact_solved:
        if delta < -WIN_EPS:
            return "faster_both_solved"
        if delta > WIN_EPS:
            return "slower_both_solved"
        return "tie_both_solved"
    if not base_solved and compact_solved:
        return "recovered_timeout"
    if base_solved and not compact_solved:
        return "lost_solution"
    return "both_timeout"


def compare_spec(spec: EvalSpec) -> pd.DataFrame:
    base = load_eval(spec.baseline_path)
    compact = load_eval(spec.compact_path)
    columns = [
        "file_key",
        "Result",
        "solved",
        "time",
        "CPU time",
        "GPU time",
        "conflicts",
        "decisions",
        "propagations",
    ]
    merged = (
        base[columns]
        .rename(
            columns={
                "Result": "base_result",
                "solved": "base_solved",
                "time": "base_time",
                "CPU time": "base_cpu_time",
                "GPU time": "base_gpu_time",
                "conflicts": "base_conflicts",
                "decisions": "base_decisions",
                "propagations": "base_propagations",
            }
        )
        .merge(
            compact[columns].rename(
                columns={
                    "Result": "compact_result",
                    "solved": "compact_solved",
                    "time": "compact_time",
                    "CPU time": "compact_cpu_time",
                    "GPU time": "compact_gpu_time",
                    "conflicts": "compact_conflicts",
                    "decisions": "compact_decisions",
                    "propagations": "compact_propagations",
                }
            ),
            on="file_key",
            how="inner",
        )
    )
    merged.insert(0, "size", spec.size)
    merged.insert(1, "split", spec.split_name)
    merged["delta_time"] = merged["compact_time"] - merged["base_time"]
    merged["delta_cpu_time"] = merged["compact_cpu_time"] - merged["base_cpu_time"]
    merged["delta_conflicts"] = merged["compact_conflicts"] - merged["base_conflicts"]
    merged["delta_decisions"] = merged["compact_decisions"] - merged["base_decisions"]
    merged["delta_propagations"] = merged["compact_propagations"] - merged["base_propagations"]
    merged["difficulty_bucket"] = merged.apply(difficulty_bucket, axis=1)
    merged["outcome"] = merged.apply(outcome, axis=1)
    merged["is_win"] = merged["outcome"].isin(["faster_both_solved", "recovered_timeout"])
    merged["is_loss"] = merged["outcome"].isin(["slower_both_solved", "lost_solution"])
    return merged


def metric_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (size, split), group in per_instance.groupby(["size", "split"], sort=False):
        counts = group["outcome"].value_counts()
        rows.append(
            {
                "size": int(size),
                "split": split,
                "n": int(len(group)),
                "base_solved": int(group["base_solved"].sum()),
                "compact_solved": int(group["compact_solved"].sum()),
                "delta_solved": int(group["compact_solved"].sum() - group["base_solved"].sum()),
                "base_mean_time": float(group["base_time"].mean()),
                "compact_mean_time": float(group["compact_time"].mean()),
                "delta_mean_time": float(group["delta_time"].mean()),
                "median_delta_time": float(group["delta_time"].median()),
                "base_mean_conflicts": float(group["base_conflicts"].mean()),
                "compact_mean_conflicts": float(group["compact_conflicts"].mean()),
                "delta_mean_conflicts": float(group["delta_conflicts"].mean()),
                "wins": int(group["is_win"].sum()),
                "losses": int(group["is_loss"].sum()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    return pd.DataFrame(rows)


def bucket_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    bucket_order = {
        "easy(<10s)": 0,
        "medium(10-30s)": 1,
        "hard(>=30s)": 2,
        "timeout": 3,
    }
    rows = []
    for (size, bucket), group in per_instance.groupby(["size", "difficulty_bucket"], sort=False):
        counts = group["outcome"].value_counts()
        rows.append(
            {
                "size": int(size),
                "bucket": bucket,
                "bucket_order": bucket_order[bucket],
                "n": int(len(group)),
                "base_solved": int(group["base_solved"].sum()),
                "compact_solved": int(group["compact_solved"].sum()),
                "delta_solved": int(group["compact_solved"].sum() - group["base_solved"].sum()),
                "delta_mean_time": float(group["delta_time"].mean()),
                "median_delta_time": float(group["delta_time"].median()),
                "wins": int(group["is_win"].sum()),
                "losses": int(group["is_loss"].sum()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    result = pd.DataFrame(rows)
    return result.sort_values(["size", "bucket_order"]).drop(columns=["bucket_order"])


def largest_changes(per_instance: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    parts = []
    columns = [
        "size",
        "file_key",
        "difficulty_bucket",
        "base_result",
        "compact_result",
        "base_time",
        "compact_time",
        "delta_time",
        "outcome",
        "delta_conflicts",
        "delta_decisions",
    ]
    for size, group in per_instance.groupby("size", sort=True):
        wins = group.nsmallest(n, "delta_time")[columns].copy()
        losses = group.nlargest(n, "delta_time")[columns].copy()
        wins.insert(1, "change_type", "largest_win")
        losses.insert(1, "change_type", "largest_loss")
        parts.extend([wins, losses])
    return pd.concat(parts, ignore_index=True)


def solved_times(frame: pd.DataFrame) -> list[float]:
    solved = frame[frame["solved"]].copy()
    return sorted(float(value) for value in solved["time"].tolist())


def plot_cactus() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    colors = {"one-shot": "#4c78a8", "compact risk": "#f58518"}
    markers = {"one-shot": "o", "compact risk": "s"}

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.2), sharey=True)
    for ax, spec in zip(axes, SPECS):
        for label, path in [
            ("one-shot", spec.baseline_path),
            ("compact risk", spec.compact_path),
        ]:
            frame = load_eval(path)
            times = solved_times(frame)
            ax.plot(
                range(1, len(times) + 1),
                times,
                label=label,
                color=colors[label],
                linewidth=1.8,
                marker=markers[label],
                markevery=max(1, len(times) // 8),
                markersize=3.8,
            )
        ax.set_title(f"3SAT-{spec.size}")
        ax.set_xlabel("Solved instances")
        ax.set_ylabel("Total time (s)")
        ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
        ax.set_xlim(left=1)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, fontsize=9)
    fig.subplots_adjust(top=0.80)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_compact_risk_disjoint_cactus_300_350_400.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig_compact_risk_disjoint_cactus_300_350_400.svg", bbox_inches="tight")
    plt.close(fig)

    for spec in SPECS:
        fig, ax = plt.subplots(figsize=(4.4, 3.2))
        for label, path in [
            ("one-shot", spec.baseline_path),
            ("compact risk", spec.compact_path),
        ]:
            frame = load_eval(path)
            times = solved_times(frame)
            ax.plot(
                range(1, len(times) + 1),
                times,
                label=label,
                color=colors[label],
                linewidth=1.8,
                marker=markers[label],
                markevery=max(1, len(times) // 8),
                markersize=3.8,
            )
        ax.set_title(f"3SAT-{spec.size}")
        ax.set_xlabel("Solved instances")
        ax.set_ylabel("Total time (s)")
        ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
        ax.set_xlim(left=1)
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"fig_compact_risk_disjoint_cactus_{spec.size}.pdf", bbox_inches="tight")
        fig.savefig(FIG_DIR / f"fig_compact_risk_disjoint_cactus_{spec.size}.svg", bbox_inches="tight")
        plt.close(fig)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_doc(metrics: pd.DataFrame, buckets: pd.DataFrame, changes: pd.DataFrame) -> None:
    metric_cols = [
        "size",
        "split",
        "n",
        "base_solved",
        "compact_solved",
        "delta_solved",
        "base_mean_time",
        "compact_mean_time",
        "delta_mean_time",
        "median_delta_time",
        "wins",
        "losses",
        "recovered_timeout",
        "lost_solution",
        "both_timeout",
    ]
    bucket_cols = [
        "size",
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
    change_cols = [
        "size",
        "change_type",
        "file_key",
        "difficulty_bucket",
        "base_result",
        "compact_result",
        "base_time",
        "compact_time",
        "delta_time",
        "outcome",
    ]
    doc = [
        "# Compact Risk Controller Disjoint 评估",
        "",
        "本文档记录 compact risk evidence two-stage selector 的正式 disjoint 评估。",
        "比较对象是同一批 CNF 上重新运行的 one-shot baseline。",
        "",
        "## Split",
        "",
        "- 300：`data/selector_splits/3sat/heldout_test/300/*.cnf`，100 个实例",
        "- 350：`data/selector_splits/3sat/heldout_test/350/*.cnf`，100 个实例",
        "- 400：`data/selector_splits/3sat/hard_recovery_heldout/400/*.cnf`，80 个实例",
        "",
        "注意：400 不是完整随机测试集，而是 hard-recovery split 的 heldout 部分。",
        "",
        "## 输出文件",
        "",
        "- `runs/analysis/compact_risk_disjoint_per_instance.csv`",
        "- `runs/analysis/compact_risk_disjoint_summary.csv`",
        "- `runs/analysis/compact_risk_disjoint_bucket_summary.csv`",
        "- `runs/analysis/compact_risk_disjoint_largest_changes.csv`",
        "- `figures/fig_compact_risk_disjoint_cactus_300_350_400.pdf`",
        "",
        "## 总体结果",
        "",
        markdown_table(metrics[metric_cols], metric_cols),
        "",
        "## Difficulty Bucket",
        "",
        "bucket 按 one-shot baseline 划分：10s 内为 easy，10-30s 为 medium，",
        "30s 以上为 hard，未解为 timeout。",
        "",
        markdown_table(buckets[bucket_cols], bucket_cols),
        "",
        "## 最大单实例变化",
        "",
        markdown_table(changes[change_cols], change_cols),
        "",
        "## 结论",
        "",
        "- compact risk controller 在 300/350/400 三个 disjoint split 上没有 lost solution。",
        "- 300 和 350 都保持 100/100 solved，并带来小幅平均时间下降。",
        "- 400 hard-recovery heldout 上 solved count 与 one-shot 持平；平均时间略降，",
        "  但 timeout bucket 没有 recovered_timeout，说明这个 heldout split 对 recovery 能力",
        "  仍然不够敏感。",
        "- 当前结果支持“risk gate 能防止翻车并带来稳定小收益”，但还不能证明",
        "  它在真正 400 timeout recovery 上有强恢复能力。",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    per_instance = pd.concat([compare_spec(spec) for spec in SPECS], ignore_index=True)
    metrics = metric_summary(per_instance)
    buckets = bucket_summary(per_instance)
    changes = largest_changes(per_instance)

    per_instance.to_csv(OUT_DIR / "compact_risk_disjoint_per_instance.csv", index=False)
    metrics.to_csv(OUT_DIR / "compact_risk_disjoint_summary.csv", index=False)
    buckets.to_csv(OUT_DIR / "compact_risk_disjoint_bucket_summary.csv", index=False)
    changes.to_csv(OUT_DIR / "compact_risk_disjoint_largest_changes.csv", index=False)
    plot_cactus()
    write_doc(metrics, buckets, changes)

    print(metrics.to_string(index=False))
    print(f"wrote {OUT_DIR / 'compact_risk_disjoint_per_instance.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_disjoint_summary.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_disjoint_bucket_summary.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_disjoint_largest_changes.csv'}")
    print(f"wrote {FIG_DIR / 'fig_compact_risk_disjoint_cactus_300_350_400.pdf'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
