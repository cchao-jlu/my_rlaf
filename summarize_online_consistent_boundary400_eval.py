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
OLD_COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
    "eval_compact_risk_full400.csv"
)
PAIRWISE_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv")
NEW_ROOT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative")
NEW_BATCH_PREFIX = "eval_online_consistent_boundary400_full400_batch"
NEW_MERGED_CSV = Path("runs/analysis/online_consistent_boundary400_full400_actual_batched.csv")
SUMMARY_CSV = Path("runs/analysis/online_consistent_boundary400_full400_summary.csv")
PER_INSTANCE_CSV = Path("runs/analysis/online_consistent_boundary400_full400_per_instance.csv")
BUCKET_CSV = Path("runs/analysis/online_consistent_boundary400_full400_bucket_summary.csv")
CHANGES_CSV = Path("runs/analysis/online_consistent_boundary400_full400_largest_changes.csv")
DOC_PATH = Path("docs/online_consistent_boundary400_full400_eval.md")
FIG_PATH = Path("figures/fig_online_consistent_boundary400_full400_cactus.pdf")
FIG_SVG_PATH = Path("figures/fig_online_consistent_boundary400_full400_cactus.svg")
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
WIN_EPS = 0.1


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def load_eval(path: Path, method: str) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"].map(is_solved)
    frame["method"] = method
    return frame


def collect_new_batches() -> pd.DataFrame:
    frames = []
    for idx in range(4):
        path = NEW_ROOT / f"{NEW_BATCH_PREFIX}{idx}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = load_eval(path, "online_consistent_boundary400")
        frame["batch"] = idx
        frames.append(frame)
    merged = pd.concat(frames, ignore_index=True).sort_values("file_key").reset_index(drop=True)
    NEW_MERGED_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(NEW_MERGED_CSV, index=False)
    return merged


def method_summary(frame: pd.DataFrame, method: str) -> dict[str, object]:
    return {
        "method": method,
        "n": int(len(frame)),
        "solved": int(frame["solved"].sum()),
        "mean_time": float(frame["time"].mean()),
        "median_time": float(frame["time"].median()),
        "mean_cpu_time": float(frame["CPU time"].mean()),
        "mean_gpu_time": float(frame["GPU time"].mean()),
        "mean_conflicts": float(frame["conflicts"].mean()),
        "mean_decisions": float(frame["decisions"].mean()),
    }


def difficulty_bucket(row: pd.Series) -> str:
    if not bool(row["base_solved"]):
        return "timeout"
    time = float(row["base_time"])
    if time < 10.0:
        return "easy(<10s)"
    if time < 30.0:
        return "medium(10-30s)"
    return "hard(>=30s)"


def outcome_vs(row: pd.Series, prefix: str) -> str:
    ref_solved = bool(row[f"{prefix}_solved"])
    new_solved = bool(row["new_solved"])
    delta = float(row[f"delta_time_vs_{prefix}"])
    if ref_solved and new_solved:
        if delta < -WIN_EPS:
            return "faster_both_solved"
        if delta > WIN_EPS:
            return "slower_both_solved"
        return "tie_both_solved"
    if not ref_solved and new_solved:
        return "recovered_timeout"
    if ref_solved and not new_solved:
        return "lost_solution"
    return "both_timeout"


def build_per_instance(new: pd.DataFrame) -> pd.DataFrame:
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
    base = load_eval(BASELINE_CSV, "oneshot")
    old = load_eval(OLD_COMPACT_CSV, "old_compact")
    pairwise = pd.read_csv(PAIRWISE_CSV).copy()
    if "solved" not in pairwise.columns:
        pairwise["solved"] = pairwise["Result"].map(is_solved)
    pairwise["file_key"] = pairwise["file_key"].astype(str)
    pairwise["method"] = "pairwise_veto_actual"

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
            old[columns].rename(
                columns={
                    "Result": "old_result",
                    "solved": "old_solved",
                    "time": "old_time",
                    "CPU time": "old_cpu_time",
                    "GPU time": "old_gpu_time",
                    "conflicts": "old_conflicts",
                    "decisions": "old_decisions",
                    "propagations": "old_propagations",
                }
            ),
            on="file_key",
        )
        .merge(
            pairwise[columns].rename(
                columns={
                    "Result": "pairwise_result",
                    "solved": "pairwise_solved",
                    "time": "pairwise_time",
                    "CPU time": "pairwise_cpu_time",
                    "GPU time": "pairwise_gpu_time",
                    "conflicts": "pairwise_conflicts",
                    "decisions": "pairwise_decisions",
                    "propagations": "pairwise_propagations",
                }
            ),
            on="file_key",
        )
        .merge(
            new[columns].rename(
                columns={
                    "Result": "new_result",
                    "solved": "new_solved",
                    "time": "new_time",
                    "CPU time": "new_cpu_time",
                    "GPU time": "new_gpu_time",
                    "conflicts": "new_conflicts",
                    "decisions": "new_decisions",
                    "propagations": "new_propagations",
                }
            ),
            on="file_key",
        )
    )
    merged.insert(0, "size", 400)
    merged.insert(1, "split", "data/test/3sat/400")
    for prefix in ["base", "old", "pairwise"]:
        merged[f"delta_time_vs_{prefix}"] = merged["new_time"] - merged[f"{prefix}_time"]
        merged[f"delta_conflicts_vs_{prefix}"] = merged["new_conflicts"] - merged[f"{prefix}_conflicts"]
        merged[f"outcome_vs_{prefix}"] = merged.apply(outcome_vs, axis=1, prefix=prefix)
    merged["difficulty_bucket"] = merged.apply(difficulty_bucket, axis=1)
    return merged


def summary_from_methods(new: pd.DataFrame) -> pd.DataFrame:
    methods = [
        load_eval(BASELINE_CSV, "oneshot"),
        load_eval(OLD_COMPACT_CSV, "old_compact"),
        load_eval(PAIRWISE_CSV, "pairwise_veto_actual"),
        new,
    ]
    return pd.DataFrame([method_summary(frame, str(frame["method"].iloc[0])) for frame in methods])


def bucket_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bucket, group in per_instance.groupby("difficulty_bucket", sort=False):
        counts = group["outcome_vs_old"].value_counts()
        rows.append(
            {
                "bucket": bucket,
                "n": int(len(group)),
                "base_solved": int(group["base_solved"].sum()),
                "old_solved": int(group["old_solved"].sum()),
                "new_solved": int(group["new_solved"].sum()),
                "delta_solved_vs_old": int(group["new_solved"].sum() - group["old_solved"].sum()),
                "delta_mean_time_vs_old": float(group["delta_time_vs_old"].mean()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    order = {"easy(<10s)": 0, "medium(10-30s)": 1, "hard(>=30s)": 2, "timeout": 3}
    result = pd.DataFrame(rows)
    result["_order"] = result["bucket"].map(order)
    return result.sort_values("_order").drop(columns=["_order"])


def largest_changes(per_instance: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    columns = [
        "file_key",
        "difficulty_bucket",
        "old_result",
        "new_result",
        "old_time",
        "new_time",
        "delta_time_vs_old",
        "outcome_vs_old",
        "base_time",
        "pairwise_time",
    ]
    wins = per_instance.nsmallest(n, "delta_time_vs_old")[columns].copy()
    losses = per_instance.nlargest(n, "delta_time_vs_old")[columns].copy()
    wins.insert(0, "change_type", "largest_win")
    losses.insert(0, "change_type", "largest_loss")
    return pd.concat([wins, losses], ignore_index=True)


def solved_times(frame: pd.DataFrame) -> list[float]:
    return sorted(float(value) for value in frame.loc[frame["solved"], "time"].tolist())


def plot_cactus(new: pd.DataFrame) -> None:
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for label, frame, color in [
        ("one-shot", load_eval(BASELINE_CSV, "oneshot"), "#4c78a8"),
        ("old compact", load_eval(OLD_COMPACT_CSV, "old_compact"), "#f58518"),
        ("pairwise veto", load_eval(PAIRWISE_CSV, "pairwise_veto_actual"), "#54a24b"),
        ("boundary400", new, "#b279a2"),
    ]:
        times = solved_times(frame)
        ax.plot(range(1, len(times) + 1), times, label=label, color=color, linewidth=1.8)
    ax.set_title("3SAT-400 full test")
    ax.set_xlabel("Solved instances")
    ax.set_ylabel("Total time (s)")
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.set_xlim(left=1)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_PATH, bbox_inches="tight")
    fig.savefig(FIG_SVG_PATH, bbox_inches="tight")
    plt.close(fig)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame[columns].iterrows():
        rows.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(rows)


def write_doc(summary: pd.DataFrame, buckets: pd.DataFrame, changes: pd.DataFrame, per_instance: pd.DataFrame) -> None:
    outcome_counts = per_instance["outcome_vs_old"].value_counts().rename_axis("outcome_vs_old").reset_index(name="count")
    key_cases = per_instance[
        per_instance["file_key"].isin(["3sat_89.cnf", "3sat_122.cnf", "3sat_163.cnf", "3sat_188.cnf", "3sat_189.cnf", "3sat_82.cnf"])
    ].copy()
    doc = [
        "# Online-Consistent Boundary400 Full400 评估",
        "",
        "本报告合并 4 个 50 实例 batch 的真实 wall-clock 结果。",
        "该 checkpoint 使用 full400 boundary 子集生成的 online-consistent trace 重训 two-stage selector。",
        "",
        "## 方法汇总",
        "",
        markdown_table(summary, ["method", "n", "solved", "mean_time", "median_time", "mean_cpu_time", "mean_gpu_time"]),
        "",
        "## 相对旧 compact 主线的 outcome",
        "",
        markdown_table(outcome_counts, ["outcome_vs_old", "count"]),
        "",
        "## 难度桶",
        "",
        markdown_table(buckets, list(buckets.columns)),
        "",
        "## 重点样本",
        "",
        markdown_table(
            key_cases,
            [
                "file_key",
                "difficulty_bucket",
                "old_result",
                "new_result",
                "old_time",
                "new_time",
                "delta_time_vs_old",
                "outcome_vs_old",
            ],
        ),
        "",
        "## 最大变化",
        "",
        markdown_table(changes, list(changes.columns)),
        "",
        "## 输出文件",
        "",
        f"- `{NEW_MERGED_CSV}`",
        f"- `{SUMMARY_CSV}`",
        f"- `{PER_INSTANCE_CSV}`",
        f"- `{BUCKET_CSV}`",
        f"- `{CHANGES_CSV}`",
        f"- `{FIG_PATH}`",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    new = collect_new_batches()
    summary = summary_from_methods(new)
    per_instance = build_per_instance(new)
    buckets = bucket_summary(per_instance)
    changes = largest_changes(per_instance)

    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_CSV, index=False)
    per_instance.to_csv(PER_INSTANCE_CSV, index=False)
    buckets.to_csv(BUCKET_CSV, index=False)
    changes.to_csv(CHANGES_CSV, index=False)
    plot_cactus(new)
    write_doc(summary, buckets, changes, per_instance)
    print(f"wrote {NEW_MERGED_CSV}")
    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {PER_INSTANCE_CSV}")
    print(f"wrote {DOC_PATH}")
    print(f"wrote {FIG_PATH}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
