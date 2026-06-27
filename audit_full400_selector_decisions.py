from __future__ import annotations

from pathlib import Path

import pandas as pd
import torch

from extract_compact_selector_features import stage_probability
from src.model.model import load_checkpoint


OLD_CHECKPOINT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt")
STABLE_CHECKPOINT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactStableRecovery300350400/best.pt")
FEATURES_CSV = Path("runs/analysis/compact_risk_full400_with_selector_features.csv")
PER_INSTANCE_CSV = Path("runs/analysis/compact_stable_full400_per_instance.csv")
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/full400_selector_decision_audit.md")
FOCUS = {
    "3sat_163.cnf",
    "3sat_122.cnf",
    "3sat_88.cnf",
    "3sat_25.cnf",
    "3sat_140.cnf",
    "3sat_82.cnf",
}


def selector_probs(frame: pd.DataFrame, checkpoint: Path, prefix: str) -> pd.DataFrame:
    model, _, _ = load_checkpoint(str(checkpoint), var_output=True)
    risk_probs = stage_probability(
        frame,
        feature_names=list(model.event_adapter_risk_selector_feature_names),
        weights=list(model.event_adapter_risk_selector_weights),
        bias=float(model.event_adapter_risk_selector_bias),
        mean=list(model.event_adapter_risk_selector_feature_mean),
        std=list(model.event_adapter_risk_selector_feature_std),
    )
    recovery_probs = stage_probability(
        frame,
        feature_names=list(model.event_adapter_recovery_selector_feature_names),
        weights=list(model.event_adapter_recovery_selector_weights),
        bias=float(model.event_adapter_recovery_selector_bias),
        mean=list(model.event_adapter_recovery_selector_feature_mean),
        std=list(model.event_adapter_recovery_selector_feature_std),
    )
    risk_threshold = float(model.event_adapter_risk_selector_threshold)
    recovery_threshold = float(model.event_adapter_recovery_selector_threshold)
    result = pd.DataFrame(
        {
            "file_key": frame["file_key"],
            f"{prefix}_risk_prob": risk_probs.numpy(),
            f"{prefix}_recovery_prob": recovery_probs.numpy(),
        }
    )
    result[f"{prefix}_risk_threshold"] = risk_threshold
    result[f"{prefix}_recovery_threshold"] = recovery_threshold
    result[f"{prefix}_risk_margin"] = result[f"{prefix}_risk_prob"] - risk_threshold
    result[f"{prefix}_recovery_margin"] = result[f"{prefix}_recovery_prob"] - recovery_threshold
    result[f"{prefix}_use_adapter"] = (
        (result[f"{prefix}_risk_prob"] < risk_threshold)
        & (result[f"{prefix}_recovery_prob"] >= recovery_threshold)
    ).astype("int64")
    return result


def decision_change(row: pd.Series) -> str:
    old_use = bool(row["old_use_adapter"])
    stable_use = bool(row["stable_use_adapter"])
    if old_use and stable_use:
        return "both_on"
    if (not old_use) and (not stable_use):
        return "both_off"
    if old_use and (not stable_use):
        return "stable_closed"
    return "stable_opened"


def diagnose(row: pd.Series) -> str:
    outcome = str(row["outcome_vs_old_compact"])
    change = str(row["decision_change"])
    if outcome == "stable_lost" and change == "stable_opened":
        return "stable 新开 adapter 后丢解"
    if outcome == "stable_lost" and change == "stable_closed":
        return "stable 关掉 adapter 后丢解"
    if outcome == "stable_slower" and change == "stable_opened":
        return "stable 新开 adapter 后慢化"
    if outcome == "stable_slower" and change == "stable_closed":
        return "stable 关掉 adapter 后慢化"
    if outcome == "stable_faster" and change == "stable_opened":
        return "stable 新开 adapter 后加速"
    if outcome == "stable_faster" and change == "stable_closed":
        return "stable 关掉 adapter 后加速"
    if change == "both_on":
        return "两者都开启，差异主要来自求解随机/阈值外因素"
    if change == "both_off":
        return "两者都关闭，差异主要来自 one-shot/运行噪声"
    return "边界变化但 outcome 不显著"


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame[columns].iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    features = pd.read_csv(FEATURES_CSV)
    per_instance = pd.read_csv(PER_INSTANCE_CSV)
    old = selector_probs(features, OLD_CHECKPOINT, "old")
    stable = selector_probs(features, STABLE_CHECKPOINT, "stable")
    audit = (
        per_instance.merge(old, on="file_key", how="left")
        .merge(stable, on="file_key", how="left")
    )
    audit["decision_change"] = audit.apply(decision_change, axis=1)
    audit["diagnosis"] = audit.apply(diagnose, axis=1)
    audit["stable_minus_old_risk_prob"] = audit["stable_risk_prob"] - audit["old_risk_prob"]
    audit["stable_minus_old_recovery_prob"] = audit["stable_recovery_prob"] - audit["old_recovery_prob"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = OUT_DIR / "full400_selector_decision_audit.csv"
    focus_path = OUT_DIR / "full400_selector_decision_audit_focus.csv"
    summary_path = OUT_DIR / "full400_selector_decision_audit_summary.csv"
    audit.to_csv(audit_path, index=False)

    focus = audit[audit["file_key"].isin(FOCUS)].copy().sort_values("file_key")
    focus.to_csv(focus_path, index=False)

    rows = []
    for change, group in audit.groupby("decision_change", sort=True):
        counts = group["outcome_vs_old_compact"].value_counts()
        rows.append(
            {
                "decision_change": change,
                "n": int(len(group)),
                "stable_solved": int(group["compact_stable_solved"].sum()),
                "old_solved": int(group["old_compact_solved"].sum()),
                "delta_solved": int(group["compact_stable_solved"].sum() - group["old_compact_solved"].sum()),
                "delta_mean_time_vs_old": float(group["compact_stable_delta_time_vs_old_compact"].mean()),
                "stable_faster": int(counts.get("stable_faster", 0)),
                "stable_slower": int(counts.get("stable_slower", 0)),
                "stable_lost": int(counts.get("stable_lost", 0)),
                "stable_recovered": int(counts.get("stable_recovered", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(summary_path, index=False)

    changed = audit[audit["decision_change"].isin(["stable_opened", "stable_closed"])].copy()
    changed = changed.sort_values("compact_stable_delta_time_vs_old_compact", ascending=False)
    loss_cols = [
        "file_key",
        "decision_change",
        "outcome_vs_old_compact",
        "old_compact_time",
        "compact_stable_time",
        "compact_stable_delta_time_vs_old_compact",
        "old_risk_prob",
        "old_recovery_prob",
        "old_use_adapter",
        "stable_risk_prob",
        "stable_recovery_prob",
        "stable_use_adapter",
        "diagnosis",
    ]
    key_losses = audit[
        audit["outcome_vs_old_compact"].isin(["stable_lost", "stable_slower"])
    ].nlargest(12, "compact_stable_delta_time_vs_old_compact")

    focus_cols = [
        "file_key",
        "old_compact_result",
        "compact_stable_result",
        "old_compact_time",
        "compact_stable_time",
        "compact_stable_delta_time_vs_old_compact",
        "old_risk_prob",
        "old_recovery_prob",
        "old_use_adapter",
        "stable_risk_prob",
        "stable_recovery_prob",
        "stable_use_adapter",
        "decision_change",
        "outcome_vs_old_compact",
        "diagnosis",
    ]
    doc = [
        "# Full400 Selector 决策审计",
        "",
        "本审计固定 full400 的同一份 warmup/event feature cache，分别套用旧 compact 和 compact stable 的线性 risk/recovery selector。",
        "因此这里看的是 selector 边界差异本身，不重新引入 solver rollout 噪声。",
        "",
        "## 结论",
        "",
        "- 旧 compact 仍作为当前主线结果保留：`56/200, 46.3484s`。",
        "- compact stable：`54/200, 46.6911s`，不能替换主线。",
        "- stable 的主要问题不是整体模型表达力，而是 full400 上 decision boundary 发生了不稳定位移：risk threshold 更严格会关掉部分旧 compact 的有效 adapter，同时 recovery threshold 更宽松又会打开部分 easy/medium 风险样本。",
        "- `3sat_163.cnf` 是典型漏开样本：old 开启 adapter，stable 关闭 adapter，结果从 SAT 变成 timeout。",
        "- `3sat_88.cnf` 和 `3sat_25.cnf` 是典型误开样本：old 关闭 adapter，stable 打开 adapter，导致明显慢化。",
        "",
        "## 决策变化汇总",
        "",
        markdown_table(
            summary,
            [
                "decision_change",
                "n",
                "old_solved",
                "stable_solved",
                "delta_solved",
                "delta_mean_time_vs_old",
                "stable_faster",
                "stable_slower",
                "stable_lost",
                "stable_recovered",
                "both_timeout",
            ],
        ),
        "",
        "## 重点实例",
        "",
        markdown_table(focus, focus_cols),
        "",
        "## 最大负面样本",
        "",
        markdown_table(key_losses, loss_cols),
        "",
        "## 输出文件",
        "",
        f"- `{audit_path}`",
        f"- `{focus_path}`",
        f"- `{summary_path}`",
        "",
    ]
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(summary.to_string(index=False))
    print(focus[focus_cols].to_string(index=False))
    print(f"wrote {audit_path}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
