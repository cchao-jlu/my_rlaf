from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


DOC_PATH = Path("docs/boundary_pairwise_recovery_positive_floor_slowdown_veto_summary.md")
FOCUS_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto/"
    "eval_positive_floor_pairwise_slowdown_veto_focus400_rerun.csv"
)
OFFLINE_SUMMARY = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_offline_summary.csv")
OFFLINE_POLICY = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_offline_policy.csv")
OLD_FULL400 = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto/"
    "eval_positive_floor_pairwise_slowdown_veto_full400.csv"
)
RERUN_FULL400 = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto/"
    "eval_positive_floor_pairwise_slowdown_veto_full400_rerun.csv"
)
BATCH_PREFIX = "eval_positive_floor_pairwise_slowdown_veto_full400_batch"
BATCH_ROOT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto")
BATCH_MERGED = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv")
BATCH_SUMMARY = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_summary.csv")
BATCH_VS_OLD = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_vs_old_compact.csv")
OFFLINE_VS_ACTUAL = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_offline_vs_actual.csv")
ONLINE_FEATURE_SUMMARY = Path(
    "runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_feature_proxy_summary.csv"
)
ONLINE_FEATURE_POLICY = Path(
    "runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_feature_proxy_policy.csv"
)
BASELINE_CSV = Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv")
OLD_COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
    "eval_compact_risk_full400.csv"
)
CALIBRATED_COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated/"
    "eval_easy_slowdown_filter_full400_calibrated.csv"
)
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
WIN_EPS = 0.1


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_空_"
    text = frame.copy()
    for column in text.columns:
        if pd.api.types.is_float_dtype(text[column]):
            text[column] = text[column].map(lambda value: f"{value:.6f}")
        else:
            text[column] = text[column].astype(str)
    columns = list(text.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in text.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(rows)


def load_focus() -> pd.DataFrame:
    focus = pd.read_csv(FOCUS_CSV)
    focus["file_key"] = focus["file"].map(lambda value: os.path.basename(str(value)))
    return focus[
        [
            "file_key",
            "Result",
            "time",
            "CPU time",
            "conflicts",
            "decisions",
            "refinement CPU time",
            "refinement GPU time",
        ]
    ].sort_values("file_key")


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def load_eval(path: Path, method: str) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["solved"] = frame["Result"].map(is_solved)
    frame["method"] = method
    return frame


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


def collect_batched_full400() -> pd.DataFrame:
    frames = []
    for batch_idx in range(4):
        path = BATCH_ROOT / f"{BATCH_PREFIX}{batch_idx}.csv"
        if not path.exists():
            continue
        frame = load_eval(path, method="pairwise_veto_actual")
        frame["batch"] = batch_idx
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("file_key").reset_index(drop=True)
    BATCH_MERGED.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(BATCH_MERGED, index=False)
    return merged


def compare_pairwise_to_old(pairwise: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if pairwise.empty or not OLD_COMPACT_CSV.exists() or not BASELINE_CSV.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    base = load_eval(BASELINE_CSV, method="oneshot")
    old = load_eval(OLD_COMPACT_CSV, method="old_compact")
    methods = [base, old, pairwise]
    if CALIBRATED_COMPACT_CSV.exists():
        methods.insert(2, load_eval(CALIBRATED_COMPACT_CSV, method="old_compact_calibrated"))
    summary = pd.DataFrame([method_summary(frame, str(frame["method"].iloc[0])) for frame in methods])
    summary.to_csv(BATCH_SUMMARY, index=False)

    columns = ["file_key", "Result", "solved", "time", "CPU time", "conflicts", "decisions"]
    comparison = (
        old[columns]
        .rename(
            columns={
                "Result": "old_result",
                "solved": "old_solved",
                "time": "old_time",
                "CPU time": "old_cpu_time",
                "conflicts": "old_conflicts",
                "decisions": "old_decisions",
            }
        )
        .merge(
            pairwise[columns].rename(
                columns={
                    "Result": "pairwise_result",
                    "solved": "pairwise_solved",
                    "time": "pairwise_time",
                    "CPU time": "pairwise_cpu_time",
                    "conflicts": "pairwise_conflicts",
                    "decisions": "pairwise_decisions",
                }
            ),
            on="file_key",
            how="inner",
        )
    )
    comparison["delta_time_vs_old"] = comparison["pairwise_time"] - comparison["old_time"]
    comparison["delta_conflicts_vs_old"] = comparison["pairwise_conflicts"] - comparison["old_conflicts"]
    comparison["delta_decisions_vs_old"] = comparison["pairwise_decisions"] - comparison["old_decisions"]

    def outcome(row: pd.Series) -> str:
        old_solved = bool(row["old_solved"])
        pair_solved = bool(row["pairwise_solved"])
        delta = float(row["delta_time_vs_old"])
        if old_solved and pair_solved:
            if delta < -WIN_EPS:
                return "faster_both_solved"
            if delta > WIN_EPS:
                return "slower_both_solved"
            return "tie_both_solved"
        if old_solved and not pair_solved:
            return "lost_vs_old"
        if not old_solved and pair_solved:
            return "recovered_vs_old"
        return "both_timeout"

    comparison["outcome_vs_old"] = comparison.apply(outcome, axis=1)
    comparison.to_csv(BATCH_VS_OLD, index=False)

    mismatch = pd.DataFrame()
    if OFFLINE_POLICY.exists():
        offline = pd.read_csv(OFFLINE_POLICY)
        if "selector_solved_est" in offline.columns:
            offline_solved = offline["selector_solved_est"].astype(bool)
        elif "use_adapter" in offline.columns and "adapter_solved" in offline.columns and "base_solved" in offline.columns:
            offline_solved = (
                offline["use_adapter"].astype(bool) & offline["adapter_solved"].astype(bool)
            ) | (
                ~offline["use_adapter"].astype(bool) & offline["base_solved"].astype(bool)
            )
        elif "outcome" in offline.columns:
            offline_solved = offline["outcome"].isin(
                ["faster_both_solved", "slower_both_solved", "tie_both_solved", "recovered_timeout"]
            )
        else:
            offline_solved = pd.Series([False] * len(offline), index=offline.index)
        offline = offline.copy()
        offline["offline_selector_solved_est"] = offline_solved.astype(bool)
        mismatch = offline[["file_key", "outcome", "use_adapter", "offline_selector_solved_est"]].merge(
            pairwise[["file_key", "Result", "solved", "time"]].rename(
                columns={"Result": "actual_result", "solved": "actual_solved", "time": "actual_time"}
            ),
            on="file_key",
            how="inner",
        )
        mismatch["solved_est_mismatch"] = mismatch["offline_selector_solved_est"] != mismatch["actual_solved"]
        mismatch = mismatch.sort_values(["solved_est_mismatch", "file_key"], ascending=[False, True])
        mismatch.to_csv(OFFLINE_VS_ACTUAL, index=False)
    return summary, comparison, mismatch


def outcome_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()
    counts = comparison["outcome_vs_old"].value_counts()
    return pd.DataFrame(
        [
            {
                "n": int(len(comparison)),
                "old_solved": int(comparison["old_solved"].sum()),
                "pairwise_solved": int(comparison["pairwise_solved"].sum()),
                "delta_solved_vs_old": int(comparison["pairwise_solved"].sum() - comparison["old_solved"].sum()),
                "old_mean_time": float(comparison["old_time"].mean()),
                "pairwise_mean_time": float(comparison["pairwise_time"].mean()),
                "delta_mean_time_vs_old": float(comparison["delta_time_vs_old"].mean()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_vs_old": int(counts.get("recovered_vs_old", 0)),
                "lost_vs_old": int(counts.get("lost_vs_old", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        ]
    )


def key_actual_cases(comparison: pd.DataFrame) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()
    keys = [
        "3sat_89.cnf",
        "3sat_46.cnf",
        "3sat_163.cnf",
        "3sat_88.cnf",
        "3sat_25.cnf",
        "3sat_82.cnf",
        "3sat_140.cnf",
    ]
    columns = [
        "file_key",
        "old_result",
        "pairwise_result",
        "old_time",
        "pairwise_time",
        "delta_time_vs_old",
        "outcome_vs_old",
    ]
    return comparison[comparison["file_key"].isin(keys)][columns].sort_values("file_key")


def main() -> None:
    offline_summary = pd.read_csv(OFFLINE_SUMMARY) if OFFLINE_SUMMARY.exists() else pd.DataFrame()
    offline_policy = pd.read_csv(OFFLINE_POLICY) if OFFLINE_POLICY.exists() else pd.DataFrame()
    online_feature_summary = (
        pd.read_csv(ONLINE_FEATURE_SUMMARY) if ONLINE_FEATURE_SUMMARY.exists() else pd.DataFrame()
    )
    online_feature_policy = (
        pd.read_csv(ONLINE_FEATURE_POLICY) if ONLINE_FEATURE_POLICY.exists() else pd.DataFrame()
    )
    batched_full400 = collect_batched_full400()
    actual_summary, actual_comparison, offline_vs_actual = compare_pairwise_to_old(batched_full400)
    actual_outcome = outcome_summary(actual_comparison)
    actual_key_cases = key_actual_cases(actual_comparison)
    offline_mismatch_summary = pd.DataFrame()
    if not offline_vs_actual.empty:
        offline_mismatch_summary = pd.DataFrame(
            [
                {
                    "n": int(len(offline_vs_actual)),
                    "offline_solved_est": int(offline_vs_actual["offline_selector_solved_est"].sum()),
                    "actual_solved": int(offline_vs_actual["actual_solved"].sum()),
                    "solved_est_mismatch": int(offline_vs_actual["solved_est_mismatch"].sum()),
                    "offline_est_actual_timeout": int(
                        (
                            offline_vs_actual["offline_selector_solved_est"].astype(bool)
                            & ~offline_vs_actual["actual_solved"].astype(bool)
                        ).sum()
                    ),
                    "offline_timeout_actual_solved": int(
                        (
                            ~offline_vs_actual["offline_selector_solved_est"].astype(bool)
                            & offline_vs_actual["actual_solved"].astype(bool)
                        ).sum()
                    ),
                }
            ]
        )
    online_feature_mismatches = pd.DataFrame()
    if not online_feature_policy.empty and "actual_mismatch" in online_feature_policy.columns:
        online_feature_mismatches = online_feature_policy[
            online_feature_policy["actual_mismatch"].astype(bool)
        ][
            [
                "file_key",
                "selector_use_adapter",
                "risk_prob",
                "recovery_prob",
                "slowdown_prob",
                "base_solved",
                "base_time",
                "old_solved",
                "old_time",
                "online_feature_proxy_solved",
                "actual_solved",
                "actual_time",
            ]
        ].sort_values("file_key")
    focus = load_focus() if FOCUS_CSV.exists() else pd.DataFrame()
    focus_summary = pd.DataFrame()
    if not focus.empty:
        focus_summary = pd.DataFrame(
            [
                {
                    "n": len(focus),
                    "solved": int(focus["Result"].ne("INDETERMINATE").sum()),
                    "mean_time": float(focus["time"].mean()),
                    "mean_cpu_time": float(focus["CPU time"].mean()),
                }
            ]
        )
    key_policy = pd.DataFrame()
    if not offline_policy.empty:
        key_policy = offline_policy[
            offline_policy["file_key"].isin(
                [
                    "3sat_89.cnf",
                    "3sat_46.cnf",
                    "3sat_163.cnf",
                    "3sat_88.cnf",
                    "3sat_25.cnf",
                    "3sat_82.cnf",
                    "3sat_140.cnf",
                ]
            )
        ][
            [
                "file_key",
                "outcome",
                "risk_prob",
                "recovery_prob",
                "slowdown_prob",
                "use_before_veto",
                "slowdown_veto",
                "use_adapter",
            ]
        ].sort_values("file_key")

    full400_note = [
        "- `eval_positive_floor_pairwise_slowdown_veto_full400.csv` 存在，但其时间戳早于最终 `config.yaml` 刷新，属于旧错误校准下的结果，不作为有效结论。",
        "- 本轮已按 4 个 50 实例批次完成正式 full400 重跑，并合并为 `runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv`。",
        "- 分批真实结果为 `52/200`、均值 `46.8755s`，低于旧 compact 的 `56/200`、`46.3484s`；因此 pairwise+veto 暂时不能替换主线。",
        "- 旧 offline 估算使用 stale selector feature cache，高估到 `56 solved`；用最终 checkpoint 重新提取 online feature 后，proxy 估算降为 `54 solved`，只剩 2 个真实偏差。",
    ]
    if RERUN_FULL400.exists():
        full400_note.append(f"- 注意：检测到 `{RERUN_FULL400}` 已存在，需要确认时间戳晚于最终 config 后才能使用。")

    doc = [
        "# Boundary Pairwise + Slowdown Veto 结果汇总",
        "",
        "本轮目标是修复 compact stable recovery detector 的边界排序问题：保住 `3sat_163/89/46` 这类 recovery / hard speedup，同时挡掉 `3sat_25/88` 这类 easy slowdown。",
        "",
        "## 关键结论",
        "",
        "- Pairwise recovery ranking 能修复 `3sat_163` 与 `3sat_25/88` 的排序错误。",
        "- Positive-floor 阈值进一步保住 `3sat_89` 和 `3sat_46`，但会打开更多 slowdown 候选。",
        "- 叠加 slowdown veto 后，offline full400 估算回到旧 compact 的 `56 solved`，且均值估算略优。",
        "- 7 个重点实例真实 wall-clock 验证通过：`3sat_89` 从 timeout 恢复到 `0.531s`，`3sat_163` 仍恢复，`3sat_25/88` 没有被错误放大。",
        "- 但完整 full400 分批真实评估只有 `52/200`，没有追上旧 compact；focus 结果不能当作最终证据，因为在线审计显示 `3sat_89` 在最终 selector 下并未稳定开启 adapter。",
        "- 这条分支应作为边界修复诊断/负结果保留，论文主线仍保持 old compact 或 full400-calibrated compact。",
        "",
        "## Offline Full400 估算",
        "",
        markdown_table(offline_summary),
        "",
        "## 真实 Full400 分批结果",
        "",
        markdown_table(actual_summary),
        "",
        "## 真实 Full400 相对旧 Compact 的结果",
        "",
        markdown_table(actual_outcome),
        "",
        "## Offline 估算与真实结果偏差",
        "",
        markdown_table(offline_mismatch_summary),
        "",
        "## Online Feature Proxy 复核",
        "",
        "旧 offline 估算直接复用了 old compact 的 full400 selector feature cache，再套 pairwise/veto 权重；这和最终 checkpoint 在线评估时的 multi-point feature 不一致。重新用最终 checkpoint 提取 feature 后，proxy 估算从 `56 solved` 降到 `54 solved`，更接近真实 `52 solved`。",
        "",
        markdown_table(online_feature_summary),
        "",
        "## Online Feature Proxy 与真实结果仍不一致的样本",
        "",
        markdown_table(online_feature_mismatches),
        "",
        "## 重点样本 Offline 决策",
        "",
        markdown_table(key_policy),
        "",
        "## 重点样本真实结果",
        "",
        markdown_table(actual_key_cases),
        "",
        "## Focus Wall-Clock 汇总",
        "",
        markdown_table(focus_summary),
        "",
        "## Focus Wall-Clock 明细",
        "",
        markdown_table(focus),
        "",
        "## 完整 Full400 重跑状态",
        "",
        "\n".join(full400_note),
        "",
        "## 下一步",
        "",
        "1. 主结果不要切到 pairwise+veto；保留旧 compact / full400-calibrated compact 作为当前主线。",
        "2. 后续 threshold sweep 必须基于 `positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv` 这类最终 checkpoint 在线特征，不能复用旧 compact cache。",
        "3. 后续若继续改 selector，应优先修正真实 wall-clock 与离线反事实标签之间的分布偏差，而不是继续增加 selector 结构复杂度。",
        "",
    ]
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(f"wrote {DOC_PATH}")
    if not focus_summary.empty:
        print(focus_summary.to_string(index=False))
    if not offline_summary.empty:
        print(offline_summary.to_string(index=False))
    if not actual_summary.empty:
        print(actual_summary.to_string(index=False))
    if not actual_outcome.empty:
        print(actual_outcome.to_string(index=False))


if __name__ == "__main__":
    main()
