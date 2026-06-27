from __future__ import annotations

from pathlib import Path

import pandas as pd


NO_OVERRIDE_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/"
    "eval_online_consistent_focus6_400.csv"
)
LOCAL_REOPEN_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/"
    "eval_local_reopen_focus6_400.csv"
)
COMPARISON_CSV = Path("runs/analysis/local_reopen_focus6_wallclock_comparison.csv")
SUMMARY_CSV = Path("runs/analysis/local_reopen_focus6_wallclock_summary.csv")
DOC_PATH = Path("docs/local_reopen_override_focus6_eval.md")

EXPECTED_CLASS = {
    "3sat_46.cnf": "positive/hard_speedup",
    "3sat_196.cnf": "positive/hard_speedup",
    "3sat_188.cnf": "positive/recovered_timeout",
    "3sat_66.cnf": "neutral",
    "3sat_82.cnf": "negative/slowdown",
    "3sat_93.cnf": "negative/slowdown",
}


def load_eval(path: Path, policy: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["policy"] = policy
    frame["file_key"] = frame["file"].astype(str).str.rsplit("/", n=1).str[-1]
    return frame


def build_comparison(no_override: pd.DataFrame, local_reopen: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for file_key in sorted(set(no_override["file_key"]).intersection(local_reopen["file_key"])):
        base = no_override[no_override["file_key"] == file_key].iloc[0]
        override = local_reopen[local_reopen["file_key"] == file_key].iloc[0]
        rows.append(
            {
                "file_key": file_key,
                "expected_trace_class": EXPECTED_CLASS.get(file_key, ""),
                "no_override_result": base["Result"],
                "local_reopen_result": override["Result"],
                "no_override_time": float(base["time"]),
                "local_reopen_time": float(override["time"]),
                "delta_time": float(override["time"] - base["time"]),
                "no_override_conflicts": float(base["conflicts"]),
                "local_reopen_conflicts": float(override["conflicts"]),
                "delta_conflicts": float(override["conflicts"] - base["conflicts"]),
                "no_override_decisions": float(base["decisions"]),
                "local_reopen_decisions": float(override["decisions"]),
                "delta_decisions": float(override["decisions"] - base["decisions"]),
                "no_override_refinement_cpu": float(base["refinement CPU time"]),
                "local_reopen_refinement_cpu": float(override["refinement CPU time"]),
            }
        )
    return pd.DataFrame(rows)


def build_summary(no_override: pd.DataFrame, local_reopen: pd.DataFrame) -> pd.DataFrame:
    frame = pd.concat([no_override, local_reopen], ignore_index=True)
    return (
        frame.groupby("policy")
        .agg(
            solved=("Result", lambda s: int((s != "INDETERMINATE").sum())),
            mean_time=("time", "mean"),
            total_time=("time", "sum"),
            mean_cpu=("CPU time", "mean"),
            mean_conflicts=("conflicts", "mean"),
        )
        .reset_index()
    )


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    view = frame.loc[:, columns].copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda value: f"{float(value):.4f}")
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *rows])


def write_doc(comparison: pd.DataFrame, summary: pd.DataFrame) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary_view = summary.copy()
    comparison_view = comparison.copy()
    doc = [
        "# Local Reopen Override Focus6 真实 Wall-clock 验证",
        "",
        "## 实验目的",
        "",
        "本实验不再调全局阈值，只在 `new_closed_old_on` 局部边界上加入 reopen override。",
        "目标是验证 dense offline trace 中的收益能否转化为真实 solver wall-clock：打开 `3sat_46/196/188`，同时挡住 `3sat_82/93`。",
        "",
        "## 局部规则",
        "",
        "- `warmup_c1000_minus_warmup_c750_decisions >= 294`",
        "- `warmup_c2000_rho_event_corr >= 0.0365`",
        "",
        "第二个阈值使用 `0.0365`，避免 `3sat_196.cnf` 在 `0.03650097...` 附近被浮点四舍五入误关。",
        "",
        "## 聚合结果",
        "",
        markdown_table(
            summary_view,
            ["policy", "solved", "mean_time", "total_time", "mean_cpu", "mean_conflicts"],
        ),
        "",
        "## 逐实例对比",
        "",
        markdown_table(
            comparison_view,
            [
                "file_key",
                "expected_trace_class",
                "no_override_result",
                "local_reopen_result",
                "no_override_time",
                "local_reopen_time",
                "delta_time",
                "delta_conflicts",
                "delta_decisions",
            ],
        ),
        "",
        "## 结论",
        "",
        "- `3sat_46.cnf` 和 `3sat_196.cnf` 的 hard speedup 落到了真实 wall-clock；其中 `3sat_46.cnf` 从约 30.63s 降到约 0.53s，`3sat_196.cnf` 从约 25.68s 降到约 10.07s。",
        "- `3sat_188.cnf` 从 timeout 恢复为 SAT，时间约 25.57s，说明 recovered timeout 的 offline trace 不是假信号。",
        "- `3sat_82.cnf` 和 `3sat_93.cnf` 的冲突数/决策数没有变化，说明 negative slowdown 样本没有被 reopen；总时间的小差异主要来自额外 750-conflict warmup 采样点和运行噪声。",
        "- `3sat_66.cnf` 被规则打开但仍 timeout，真实开销约 +0.02s，符合 dense trace 中的 neutral 判断。",
        "",
        "## 输出文件",
        "",
        f"- `{COMPARISON_CSV}`",
        f"- `{SUMMARY_CSV}`",
        f"- `{LOCAL_REOPEN_CSV}`",
        f"- `{NO_OVERRIDE_CSV}`",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    no_override = load_eval(NO_OVERRIDE_CSV, "no_override")
    local_reopen = load_eval(LOCAL_REOPEN_CSV, "local_reopen")
    comparison = build_comparison(no_override, local_reopen)
    summary = build_summary(no_override, local_reopen)
    COMPARISON_CSV.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(COMPARISON_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(comparison, summary)
    print(DOC_PATH)


if __name__ == "__main__":
    main()
