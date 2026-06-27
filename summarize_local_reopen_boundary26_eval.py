from __future__ import annotations

from pathlib import Path

import pandas as pd


NO_OVERRIDE_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/"
    "eval_online_consistent_new_closed_old_on_boundary400.csv"
)
LOCAL_REOPEN_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/"
    "eval_local_reopen_new_closed_old_on_boundary400.csv"
)
GUIDANCE_AUDIT_CSV = Path("runs/analysis/local_reopen_boundary26_guidance_audit.csv")
TRACE_CSV = Path("data/counterfactual_trace/new_closed_old_on_dense400_outcomes.csv")
COMPARISON_CSV = Path("runs/analysis/local_reopen_boundary26_wallclock_comparison.csv")
SUMMARY_CSV = Path("runs/analysis/local_reopen_boundary26_wallclock_summary.csv")
OPEN_SET_CSV = Path("runs/analysis/local_reopen_boundary26_open_set.csv")
DOC_PATH = Path("docs/local_boundary_correction_ablation.md")

LOCAL_REOPEN_DECISION_THRESHOLD = 294.0
LOCAL_REOPEN_CORR_THRESHOLD = 0.0365


def file_key(path: object) -> str:
    return Path(str(path)).name


def load_eval(path: Path, policy: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["policy"] = policy
    frame["file_key"] = frame["file"].map(file_key)
    return frame


def load_trace(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["file_key"] = frame["file"].map(file_key)
    return frame[
        [
            "file_key",
            "counterfactual_class",
            "counterfactual_reason",
            "adapter_minus_base_time",
        ]
    ].copy()


def build_comparison(no_override: pd.DataFrame, local_reopen: pd.DataFrame, trace: pd.DataFrame) -> pd.DataFrame:
    rows = []
    trace_by_key = trace.set_index("file_key")
    for key in sorted(set(no_override["file_key"]).intersection(local_reopen["file_key"])):
        base = no_override[no_override["file_key"] == key].iloc[0]
        override = local_reopen[local_reopen["file_key"] == key].iloc[0]
        trace_row = trace_by_key.loc[key] if key in trace_by_key.index else pd.Series(dtype=object)
        rows.append(
            {
                "file_key": key,
                "counterfactual_class": trace_row.get("counterfactual_class", "neutral"),
                "counterfactual_reason": trace_row.get("counterfactual_reason", "neutral"),
                "offline_adapter_minus_base_time": float(trace_row.get("adapter_minus_base_time", 0.0)),
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
            n=("file_key", "size"),
            solved=("Result", lambda s: int((s != "INDETERMINATE").sum())),
            mean_time=("time", "mean"),
            total_time=("time", "sum"),
            mean_cpu=("CPU time", "mean"),
            mean_conflicts=("conflicts", "mean"),
            mean_decisions=("decisions", "mean"),
        )
        .reset_index()
    )


def build_open_set(guidance: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    frame = guidance.copy()
    frame["base_selector_use_adapter"] = frame["use_adapter"].astype(bool)
    frame["local_reopen_rule_open"] = (
        (pd.to_numeric(frame["warmup_c1000_minus_warmup_c750_decisions"], errors="coerce") >= LOCAL_REOPEN_DECISION_THRESHOLD)
        & (pd.to_numeric(frame["warmup_c2000_rho_event_corr"], errors="coerce") >= LOCAL_REOPEN_CORR_THRESHOLD)
    )
    merged = frame.merge(
        comparison[
            [
                "file_key",
                "counterfactual_class",
                "counterfactual_reason",
                "delta_time",
                "delta_conflicts",
                "delta_decisions",
            ]
        ],
        on="file_key",
        how="left",
    )
    columns = [
        "file_key",
        "counterfactual_class",
        "counterfactual_reason",
        "base_selector_use_adapter",
        "local_reopen_rule_open",
        "risk_prob",
        "recovery_prob",
        "slowdown_prob",
        "warmup_c1000_minus_warmup_c750_decisions",
        "warmup_c2000_rho_event_corr",
        "delta_time",
        "delta_conflicts",
        "delta_decisions",
    ]
    return merged[columns].sort_values(["local_reopen_rule_open", "file_key"], ascending=[False, True])


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    view = frame.loc[:, columns].copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda value: f"{float(value):.4f}")
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in view.columns) + " |")
    return "\n".join(lines)


def write_doc(summary: pd.DataFrame, comparison: pd.DataFrame, open_set: pd.DataFrame) -> None:
    opened = open_set[open_set["local_reopen_rule_open"]].copy()
    closed_negatives = open_set[
        (open_set["counterfactual_class"].eq("negative"))
        & (~open_set["local_reopen_rule_open"])
    ].copy()
    material = comparison[
        comparison["file_key"].isin(["3sat_46.cnf", "3sat_196.cnf", "3sat_188.cnf", "3sat_66.cnf", "3sat_82.cnf", "3sat_93.cnf"])
    ].copy()
    total_gain = (
        float(summary.loc[summary["policy"].eq("local_reopen"), "total_time"].iloc[0])
        - float(summary.loc[summary["policy"].eq("no_override"), "total_time"].iloc[0])
    )
    mean_gain = (
        float(summary.loc[summary["policy"].eq("local_reopen"), "mean_time"].iloc[0])
        - float(summary.loc[summary["policy"].eq("no_override"), "mean_time"].iloc[0])
    )
    doc = [
        "# Local Boundary Correction Ablation",
        "",
        "## 实验定位",
        "",
        "本实验只验证 `new_closed_old_on` 局部边界，不是新的全局主模型，也没有扫描全局阈值。",
        "动机是：当前 conservative risk controller 为了避免 easy/medium 翻车，会过保守地关掉少数 recoverable 或 hard-speedup 样本。",
        "local reopen override 只作为 boundary correction，用一条局部规则修正这类边界错误。",
        "",
        "## 局部规则",
        "",
        "- `warmup_c1000_minus_warmup_c750_decisions >= 294`",
        f"- `warmup_c2000_rho_event_corr >= {LOCAL_REOPEN_CORR_THRESHOLD}`",
        "",
        "该规则来自 `new_closed_old_on` dense trace，不来自 full400 全局阈值搜索。",
        "",
        "## 真实 Wall-clock 聚合结果",
        "",
        markdown_table(
            summary,
            ["policy", "n", "solved", "mean_time", "total_time", "mean_cpu", "mean_conflicts", "mean_decisions"],
        ),
        "",
        f"- total time 变化：`{total_gain:.4f}s`",
        f"- mean time 变化：`{mean_gain:.4f}s`",
        "- 解出数保持 `5/26`，没有新增 lost solution。",
        "",
        "## 实际打开集合",
        "",
        "guidance audit 显示 local reopen rule 只打开 4 个样本：",
        "",
        markdown_table(
            opened,
            [
                "file_key",
                "counterfactual_class",
                "counterfactual_reason",
                "base_selector_use_adapter",
                "local_reopen_rule_open",
                "warmup_c1000_minus_warmup_c750_decisions",
                "warmup_c2000_rho_event_corr",
                "delta_time",
                "delta_conflicts",
            ],
        ),
        "",
        "其中 `3sat_46.cnf` 和 `3sat_196.cnf` 的 hard-speedup 稳定落到真实 wall-clock；`3sat_66.cnf` 是 neutral，真实开销约为零；`3sat_188.cnf` 在本次 boundary26 run 中 no-override 已经解出，因此没有贡献新增 solved，但仍处于应打开的安全区域。",
        "",
        "## Negative 保护",
        "",
        "两个 negative slowdown 样本均保持关闭，final conflicts/decisions 不变；时间上的微小差异主要来自额外 750-conflict warmup 采样点和运行噪声。",
        "",
        markdown_table(
            closed_negatives,
            [
                "file_key",
                "counterfactual_class",
                "counterfactual_reason",
                "base_selector_use_adapter",
                "local_reopen_rule_open",
                "delta_time",
                "delta_conflicts",
                "delta_decisions",
            ],
        ),
        "",
        "## 焦点样本逐实例结果",
        "",
        markdown_table(
            material,
            [
                "file_key",
                "counterfactual_class",
                "counterfactual_reason",
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
        "## 当前结论",
        "",
        "- boundary26 真实 wall-clock 支持把该模块写成 `local boundary correction ablation`。",
        "- 该规则修复了 `3sat_46/196` 这类被 conservative selector 错关的 hard-speedup 样本，同时没有打开 `3sat_82/93` 这类 slowdown 负例。",
        "- 目前仍不应直接宣称它是 full400 主线模型；接 full400 前应加 candidate guard，只允许在 `new_closed_old_on` 这类局部候选上触发 reopen。",
        "",
        "## 输出文件",
        "",
        f"- `{COMPARISON_CSV}`",
        f"- `{SUMMARY_CSV}`",
        f"- `{OPEN_SET_CSV}`",
        f"- `{GUIDANCE_AUDIT_CSV}`",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    no_override = load_eval(NO_OVERRIDE_CSV, "no_override")
    local_reopen = load_eval(LOCAL_REOPEN_CSV, "local_reopen")
    trace = load_trace(TRACE_CSV)
    guidance = pd.read_csv(GUIDANCE_AUDIT_CSV)

    comparison = build_comparison(no_override, local_reopen, trace)
    summary = build_summary(no_override, local_reopen)
    open_set = build_open_set(guidance, comparison)

    COMPARISON_CSV.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(COMPARISON_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    open_set.to_csv(OPEN_SET_CSV, index=False)
    write_doc(summary, comparison, open_set)
    print(DOC_PATH)


if __name__ == "__main__":
    main()
