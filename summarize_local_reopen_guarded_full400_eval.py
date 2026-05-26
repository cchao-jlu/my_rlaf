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
ONLINE_CONSERVATIVE_CSV = Path("runs/analysis/online_consistent_boundary400_full400_actual_batched.csv")
PAIRWISE_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv")
LOCAL_REOPEN_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/"
    "eval_local_reopen_guarded_full400.csv"
)
GUIDANCE_AUDIT_CSV = Path("runs/analysis/local_reopen_guarded_full400_guidance_audit.csv")

OUT_DIR = Path("runs/analysis")
FIG_DIR = Path("figures")
SUMMARY_CSV = OUT_DIR / "local_reopen_guarded_full400_summary.csv"
PER_INSTANCE_CSV = OUT_DIR / "local_reopen_guarded_full400_per_instance.csv"
BUCKET_CSV = OUT_DIR / "local_reopen_guarded_full400_bucket_summary.csv"
CHANGES_CSV = OUT_DIR / "local_reopen_guarded_full400_largest_changes.csv"
OPEN_SET_CSV = OUT_DIR / "local_reopen_guarded_full400_open_set.csv"
DOC_PATH = Path("docs/local_reopen_guarded_full400_eval.md")
FIG_PATH = FIG_DIR / "fig_local_reopen_guarded_full400_cactus.pdf"
FIG_SVG_PATH = FIG_DIR / "fig_local_reopen_guarded_full400_cactus.svg"

UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
WIN_EPS = 0.1


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def file_key(path: object) -> str:
    return Path(str(path)).name


def load_eval(path: Path, method: str) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    if "file_key" not in frame.columns:
        frame["file_key"] = frame["file"].map(file_key)
    else:
        frame["file_key"] = frame["file_key"].astype(str)
    frame["solved"] = frame["Result"].map(is_solved)
    frame["method"] = method
    return frame


def method_summary(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "method": str(frame["method"].iloc[0]),
        "n": int(len(frame)),
        "solved": int(frame["solved"].sum()),
        "mean_time": float(frame["time"].mean()),
        "median_time": float(frame["time"].median()),
        "total_time": float(frame["time"].sum()),
        "mean_cpu_time": float(frame["CPU time"].mean()),
        "mean_gpu_time": float(frame["GPU time"].mean()),
        "mean_conflicts": float(frame["conflicts"].mean()),
        "mean_decisions": float(frame["decisions"].mean()),
    }


def method_frames() -> dict[str, pd.DataFrame]:
    frames = {
        "one_shot": load_eval(BASELINE_CSV, "one_shot"),
        "old_compact": load_eval(OLD_COMPACT_CSV, "old_compact"),
        "online_consistent": load_eval(ONLINE_CONSERVATIVE_CSV, "online_consistent"),
        "local_reopen_guarded": load_eval(LOCAL_REOPEN_CSV, "local_reopen_guarded"),
    }
    if PAIRWISE_CSV.exists():
        frames["pairwise_veto"] = load_eval(PAIRWISE_CSV, "pairwise_veto")
    return frames


def eval_columns(prefix: str) -> dict[str, str]:
    return {
        "Result": f"{prefix}_result",
        "solved": f"{prefix}_solved",
        "time": f"{prefix}_time",
        "CPU time": f"{prefix}_cpu_time",
        "GPU time": f"{prefix}_gpu_time",
        "conflicts": f"{prefix}_conflicts",
        "decisions": f"{prefix}_decisions",
        "propagations": f"{prefix}_propagations",
    }


def selected_eval_columns() -> list[str]:
    return [
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


def difficulty_bucket(row: pd.Series) -> str:
    if not bool(row["one_shot_solved"]):
        return "timeout"
    time = float(row["one_shot_time"])
    if time < 10.0:
        return "easy(<10s)"
    if time < 30.0:
        return "medium(10-30s)"
    return "hard(>=30s)"


def outcome_vs(row: pd.Series, prefix: str) -> str:
    ref_solved = bool(row[f"{prefix}_solved"])
    local_solved = bool(row["local_solved"])
    delta = float(row[f"delta_time_vs_{prefix}"])
    if ref_solved and local_solved:
        if delta < -WIN_EPS:
            return "faster_both_solved"
        if delta > WIN_EPS:
            return "slower_both_solved"
        return "tie_both_solved"
    if not ref_solved and local_solved:
        return "recovered_timeout"
    if ref_solved and not local_solved:
        return "lost_solution"
    return "both_timeout"


def build_per_instance(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    merged = frames["one_shot"][selected_eval_columns()].rename(columns=eval_columns("one_shot"))
    for method, prefix in [
        ("old_compact", "old"),
        ("online_consistent", "online"),
        ("local_reopen_guarded", "local"),
    ]:
        merged = merged.merge(
            frames[method][selected_eval_columns()].rename(columns=eval_columns(prefix)),
            on="file_key",
            how="inner",
        )
    if "pairwise_veto" in frames:
        merged = merged.merge(
            frames["pairwise_veto"][selected_eval_columns()].rename(columns=eval_columns("pairwise")),
            on="file_key",
            how="left",
        )
    merged.insert(0, "size", 400)
    merged.insert(1, "split", "data/test/3sat/400")
    for prefix in ["one_shot", "old", "online"]:
        merged[f"delta_time_vs_{prefix}"] = merged["local_time"] - merged[f"{prefix}_time"]
        merged[f"delta_conflicts_vs_{prefix}"] = merged["local_conflicts"] - merged[f"{prefix}_conflicts"]
        merged[f"delta_decisions_vs_{prefix}"] = merged["local_decisions"] - merged[f"{prefix}_decisions"]
        merged[f"outcome_vs_{prefix}"] = merged.apply(outcome_vs, axis=1, prefix=prefix)
    merged["difficulty_bucket"] = merged.apply(difficulty_bucket, axis=1)
    return merged


def summary_from_methods(frames: dict[str, pd.DataFrame], per_instance: pd.DataFrame) -> pd.DataFrame:
    summary = pd.DataFrame([method_summary(frame) for frame in frames.values()])
    local_row = summary["method"].eq("local_reopen_guarded")
    for ref in ["one_shot", "old_compact", "online_consistent"]:
        ref_summary = summary[summary["method"].eq(ref)].iloc[0]
        summary.loc[local_row, f"delta_solved_vs_{ref}"] = (
            int(summary.loc[local_row, "solved"].iloc[0]) - int(ref_summary["solved"])
        )
        summary.loc[local_row, f"delta_mean_time_vs_{ref}"] = (
            float(summary.loc[local_row, "mean_time"].iloc[0]) - float(ref_summary["mean_time"])
        )
    return summary


def bucket_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bucket, group in per_instance.groupby("difficulty_bucket", sort=False):
        counts = group["outcome_vs_online"].value_counts()
        rows.append(
            {
                "bucket": bucket,
                "n": int(len(group)),
                "one_shot_solved": int(group["one_shot_solved"].sum()),
                "online_solved": int(group["online_solved"].sum()),
                "local_solved": int(group["local_solved"].sum()),
                "delta_solved_vs_online": int(group["local_solved"].sum() - group["online_solved"].sum()),
                "delta_mean_time_vs_online": float(group["delta_time_vs_online"].mean()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    order = {"easy(<10s)": 0, "medium(10-30s)": 1, "hard(>=30s)": 2, "timeout": 3}
    frame = pd.DataFrame(rows)
    frame["_order"] = frame["bucket"].map(order)
    return frame.sort_values("_order").drop(columns=["_order"])


def largest_changes(per_instance: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    columns = [
        "file_key",
        "difficulty_bucket",
        "online_result",
        "local_result",
        "online_time",
        "local_time",
        "delta_time_vs_online",
        "outcome_vs_online",
        "old_time",
        "one_shot_time",
    ]
    wins = per_instance.nsmallest(n, "delta_time_vs_online")[columns].copy()
    losses = per_instance.nlargest(n, "delta_time_vs_online")[columns].copy()
    wins.insert(0, "change_type", "largest_win")
    losses.insert(0, "change_type", "largest_loss")
    return pd.concat([wins, losses], ignore_index=True)


def open_set(per_instance: pd.DataFrame) -> pd.DataFrame:
    audit = pd.read_csv(GUIDANCE_AUDIT_CSV).copy()
    audit["local_reopen_rule_open"] = audit["local_reopen_rule_open"].astype(bool)
    columns = [
        "file_key",
        "local_reopen_candidate",
        "use_adapter",
        "local_reopen_rule_open",
        "use_adapter_with_local_reopen",
        "risk_prob",
        "recovery_prob",
        "slowdown_prob",
        "warmup_c1000_minus_warmup_c750_decisions",
        "warmup_c2000_rho_event_corr",
    ]
    opened = audit.loc[audit["local_reopen_rule_open"], columns].copy()
    merged = opened.merge(
        per_instance[
            [
                "file_key",
                "online_result",
                "local_result",
                "online_time",
                "local_time",
                "delta_time_vs_online",
                "outcome_vs_online",
                "old_time",
                "one_shot_time",
                "delta_time_vs_old",
                "outcome_vs_old",
            ]
        ],
        on="file_key",
        how="left",
    )
    return merged.sort_values("file_key")


def solved_times(frame: pd.DataFrame) -> list[float]:
    return sorted(float(value) for value in frame.loc[frame["solved"], "time"].tolist())


def plot_cactus(frames: dict[str, pd.DataFrame]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    for label, key, color in [
        ("one-shot", "one_shot", "#4c78a8"),
        ("old compact", "old_compact", "#f58518"),
        ("online consistent", "online_consistent", "#54a24b"),
        ("local reopen guarded", "local_reopen_guarded", "#b279a2"),
    ]:
        times = solved_times(frames[key])
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
    if frame.empty:
        return "_空_"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame[columns].iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_doc(
    summary: pd.DataFrame,
    buckets: pd.DataFrame,
    changes: pd.DataFrame,
    opened: pd.DataFrame,
    per_instance: pd.DataFrame,
) -> None:
    local = summary[summary["method"].eq("local_reopen_guarded")].iloc[0]
    online = summary[summary["method"].eq("online_consistent")].iloc[0]
    old = summary[summary["method"].eq("old_compact")].iloc[0]
    key_cases = per_instance[
        per_instance["file_key"].isin(["3sat_46.cnf", "3sat_66.cnf", "3sat_188.cnf", "3sat_196.cnf", "3sat_82.cnf", "3sat_93.cnf"])
    ].copy()
    outcome_counts = (
        per_instance["outcome_vs_online"].value_counts().rename_axis("outcome_vs_online").reset_index(name="count")
    )
    doc = [
        "# Guarded Local Reopen Full400 评估",
        "",
        "## 实验定位",
        "",
        "这不是新的全局主模型，而是 `local boundary correction ablation` 的 full400 接入验证。",
        "candidate guard 只允许 `data/new_closed_old_on_boundary/manifest.csv` 中的局部边界样本触发 reopen；非候选样本不会因为局部规则被额外打开。",
        "",
        "局部规则为：",
        "",
        "- `local_reopen_candidate >= 1`",
        "- `warmup_c1000_minus_warmup_c750_decisions >= 294`",
        "- `warmup_c2000_rho_event_corr >= 0.0365`",
        "",
        "## 方法汇总",
        "",
        markdown_table(
            summary,
            [
                "method",
                "n",
                "solved",
                "mean_time",
                "median_time",
                "total_time",
                "mean_cpu_time",
                "mean_gpu_time",
            ],
        ),
        "",
        "关键数字：",
        "",
        f"- guarded local reopen：`{int(local['solved'])}/200`，mean time `{float(local['mean_time']):.4f}s`。",
        f"- online-consistent conservative：`{int(online['solved'])}/200`，mean time `{float(online['mean_time']):.4f}s`。",
        f"- 旧 compact 主线：`{int(old['solved'])}/200`，mean time `{float(old['mean_time']):.4f}s`。",
        f"- 相比 online-consistent conservative：解出数 `{int(local['solved']) - int(online['solved']):+d}`，平均时间 `{float(local['mean_time']) - float(online['mean_time']):+.4f}s`。",
        f"- 相比旧 compact：解出数 `{int(local['solved']) - int(old['solved']):+d}`，平均时间 `{float(local['mean_time']) - float(old['mean_time']):+.4f}s`。",
        "",
        "## Local Reopen 实际触发集合",
        "",
        markdown_table(
            opened,
            [
                "file_key",
                "use_adapter",
                "local_reopen_rule_open",
                "use_adapter_with_local_reopen",
                "online_result",
                "local_result",
                "online_time",
                "local_time",
                "delta_time_vs_online",
                "outcome_vs_online",
                "warmup_c1000_minus_warmup_c750_decisions",
                "warmup_c2000_rho_event_corr",
            ],
        ),
        "",
        "## 相对 Conservative 的 Outcome",
        "",
        markdown_table(outcome_counts, ["outcome_vs_online", "count"]),
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
                "online_result",
                "local_result",
                "online_time",
                "local_time",
                "delta_time_vs_online",
                "outcome_vs_online",
                "old_time",
                "one_shot_time",
            ],
        ),
        "",
        "## 最大单实例变化",
        "",
        markdown_table(changes, list(changes.columns)),
        "",
        "## 当前结论",
        "",
        "- candidate guard 生效：full400 中只有 4 个 `new_closed_old_on` 候选触发 local reopen。",
        "- full400 wall-clock 没有增加 solved count，但平均时间优于旧 compact 与 online-consistent conservative。",
        "- 这条线适合作为 `local boundary correction ablation` 写入论文：证明过保守 risk controller 的少量边界错误可以被局部 reopen rule 修正，但不应提升为主模型故事。",
        "",
        "## 输出文件",
        "",
        f"- `{SUMMARY_CSV}`",
        f"- `{PER_INSTANCE_CSV}`",
        f"- `{BUCKET_CSV}`",
        f"- `{CHANGES_CSV}`",
        f"- `{OPEN_SET_CSV}`",
        f"- `{FIG_PATH}`",
        f"- `{GUIDANCE_AUDIT_CSV}`",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    frames = method_frames()
    per_instance = build_per_instance(frames)
    summary = summary_from_methods(frames, per_instance)
    buckets = bucket_summary(per_instance)
    changes = largest_changes(per_instance)
    opened = open_set(per_instance)

    summary.to_csv(SUMMARY_CSV, index=False)
    per_instance.to_csv(PER_INSTANCE_CSV, index=False)
    buckets.to_csv(BUCKET_CSV, index=False)
    changes.to_csv(CHANGES_CSV, index=False)
    opened.to_csv(OPEN_SET_CSV, index=False)
    plot_cactus(frames)
    write_doc(summary, buckets, changes, opened, per_instance)

    print(f"wrote {SUMMARY_CSV}")
    print(f"wrote {PER_INSTANCE_CSV}")
    print(f"wrote {BUCKET_CSV}")
    print(f"wrote {CHANGES_CSV}")
    print(f"wrote {OPEN_SET_CSV}")
    print(f"wrote {FIG_PATH}")
    print(f"wrote {DOC_PATH}")
    print(summary.to_string(index=False))
    print(opened.to_string(index=False))


if __name__ == "__main__":
    main()
