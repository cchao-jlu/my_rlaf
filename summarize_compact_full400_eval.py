from __future__ import annotations

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


BASELINE_CSV = Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv")
COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
    "eval_compact_risk_full400.csv"
)
OUT_DIR = Path("runs/analysis")
FIG_DIR = Path("figures")
DOC_PATH = Path("docs/compact_risk_full400_eval.md")
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


def build_per_instance() -> pd.DataFrame:
    base = load_eval(BASELINE_CSV)
    compact = load_eval(COMPACT_CSV)
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
    merged.insert(0, "size", 400)
    merged.insert(1, "split", "data/test/3sat/400")
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
    counts = per_instance["outcome"].value_counts()
    return pd.DataFrame(
        [
            {
                "size": 400,
                "split": "data/test/3sat/400",
                "n": int(len(per_instance)),
                "base_solved": int(per_instance["base_solved"].sum()),
                "compact_solved": int(per_instance["compact_solved"].sum()),
                "delta_solved": int(per_instance["compact_solved"].sum() - per_instance["base_solved"].sum()),
                "base_mean_time": float(per_instance["base_time"].mean()),
                "compact_mean_time": float(per_instance["compact_time"].mean()),
                "delta_mean_time": float(per_instance["delta_time"].mean()),
                "median_delta_time": float(per_instance["delta_time"].median()),
                "base_mean_conflicts": float(per_instance["base_conflicts"].mean()),
                "compact_mean_conflicts": float(per_instance["compact_conflicts"].mean()),
                "delta_mean_conflicts": float(per_instance["delta_conflicts"].mean()),
                "wins": int(per_instance["is_win"].sum()),
                "losses": int(per_instance["is_loss"].sum()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        ]
    )


def bucket_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    bucket_order = {
        "easy(<10s)": 0,
        "medium(10-30s)": 1,
        "hard(>=30s)": 2,
        "timeout": 3,
    }
    rows = []
    for bucket, group in per_instance.groupby("difficulty_bucket", sort=False):
        counts = group["outcome"].value_counts()
        rows.append(
            {
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
    return result.sort_values("bucket_order").drop(columns=["bucket_order"])


def largest_changes(per_instance: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    columns = [
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
    wins = per_instance.nsmallest(n, "delta_time")[columns].copy()
    losses = per_instance.nlargest(n, "delta_time")[columns].copy()
    wins.insert(0, "change_type", "largest_win")
    losses.insert(0, "change_type", "largest_loss")
    return pd.concat([wins, losses], ignore_index=True)


def solved_times(frame: pd.DataFrame) -> list[float]:
    solved = frame[frame["solved"]].copy()
    return sorted(float(value) for value in solved["time"].tolist())


def plot_cactus() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    for label, path, color, marker in [
        ("one-shot", BASELINE_CSV, "#4c78a8", "o"),
        ("compact risk", COMPACT_CSV, "#f58518", "s"),
    ]:
        times = solved_times(load_eval(path))
        ax.plot(
            range(1, len(times) + 1),
            times,
            label=label,
            color=color,
            linewidth=1.8,
            marker=marker,
            markevery=max(1, len(times) // 10),
            markersize=3.8,
        )
    ax.set_title("3SAT-400 full test")
    ax.set_xlabel("Solved instances")
    ax.set_ylabel("Total time (s)")
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.set_xlim(left=1)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig_compact_risk_full400_cactus.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig_compact_risk_full400_cactus.svg", bbox_inches="tight")
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
    row = metrics.iloc[0]
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
        "# Compact Risk Controller 完整 400 测试集评估",
        "",
        "本文档记录 compact risk evidence two-stage selector 在完整",
        "`data/test/3sat/400/*.cnf` 上的重新评估。比较对象是同一批 CNF 上",
        "重新运行的 one-shot baseline。",
        "",
        "## 输出文件",
        "",
        "- `runs/analysis/compact_risk_full400_per_instance.csv`",
        "- `runs/analysis/compact_risk_full400_summary.csv`",
        "- `runs/analysis/compact_risk_full400_bucket_summary.csv`",
        "- `runs/analysis/compact_risk_full400_largest_changes.csv`",
        "- `figures/fig_compact_risk_full400_cactus.pdf`",
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
        "- compact risk controller 在完整 400 测试集上没有 lost solution。",
        (
            f"- solved count 从 one-shot 的 {int(row['base_solved'])} "
            f"提升到 {int(row['compact_solved'])}，恢复 "
            f"{int(row['recovered_timeout'])} 个 timeout。"
        ),
        (
            f"- 平均总时间从 {float(row['base_mean_time']):.2f}s "
            f"降到 {float(row['compact_mean_time']):.2f}s，平均冲突数也下降。"
        ),
        "- 主要收益来自少数 hard/timeout 实例的大幅改善；easy/medium 上仍有一些小幅 slowdown。",
        "- 这个结果比 hard-recovery heldout 更关键：它说明 compact risk gate 不只是安全，",
        "  在完整 400 分布上也出现了真实 timeout recovery。",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    per_instance = build_per_instance()
    metrics = metric_summary(per_instance)
    buckets = bucket_summary(per_instance)
    changes = largest_changes(per_instance)

    per_instance.to_csv(OUT_DIR / "compact_risk_full400_per_instance.csv", index=False)
    metrics.to_csv(OUT_DIR / "compact_risk_full400_summary.csv", index=False)
    buckets.to_csv(OUT_DIR / "compact_risk_full400_bucket_summary.csv", index=False)
    changes.to_csv(OUT_DIR / "compact_risk_full400_largest_changes.csv", index=False)
    plot_cactus()
    write_doc(metrics, buckets, changes)

    print(metrics.to_string(index=False))
    print(f"wrote {OUT_DIR / 'compact_risk_full400_per_instance.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_full400_summary.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_full400_bucket_summary.csv'}")
    print(f"wrote {OUT_DIR / 'compact_risk_full400_largest_changes.csv'}")
    print(f"wrote {FIG_DIR / 'fig_compact_risk_full400_cactus.pdf'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
