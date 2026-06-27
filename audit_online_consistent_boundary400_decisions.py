from __future__ import annotations

from pathlib import Path

import pandas as pd

from extract_compact_selector_features import stage_probability
from src.model.model import load_checkpoint


NEW_CHECKPOINT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/best.pt")
OLD_CHECKPOINT = Path("runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt")
FEATURES_CSV = Path("runs/analysis/online_consistent_boundary400_full400_selector_features.csv")
PER_INSTANCE_CSV = Path("runs/analysis/online_consistent_boundary400_full400_per_instance.csv")
OLD_COMPACT_FEATURES_CSV = Path("runs/analysis/compact_risk_full400_with_selector_features.csv")
DATASET_DIR = Path("data/test/3sat/400")
OUT_DIR = Path("runs/analysis")
AUDIT_CSV = OUT_DIR / "online_consistent_boundary400_decision_audit.csv"
FOCUS_CSV = OUT_DIR / "online_consistent_boundary400_decision_audit_focus.csv"
SUMMARY_CSV = OUT_DIR / "online_consistent_boundary400_decision_audit_summary.csv"
DOC_PATH = Path("docs/online_consistent_boundary400_decision_audit.md")

FOCUS_KEYS = {
    "3sat_46.cnf",
    "3sat_196.cnf",
    "3sat_140.cnf",
    "3sat_82.cnf",
    "3sat_188.cnf",
    "3sat_97.cnf",
    "3sat_163.cnf",
    "3sat_89.cnf",
    "3sat_25.cnf",
    "3sat_88.cnf",
    "3sat_122.cnf",
}


def map_cnf_ids_to_file_keys(frame: pd.DataFrame, files: list[str | Path] | None = None) -> pd.DataFrame:
    result = frame.copy()
    if files is None:
        files = sorted(DATASET_DIR.glob("*.cnf"))
    names = [Path(path).name for path in files]
    result["file_key"] = result["cnf_id"].map(lambda value: names[int(value)])
    return result


def selector_probabilities(features: pd.DataFrame, checkpoint: Path, prefix: str) -> pd.DataFrame:
    model, _, _ = load_checkpoint(str(checkpoint), var_output=True)
    frame = features.copy()
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
    frame["recovery_prob"] = recovery_probs.numpy()
    use_adapter = (
        (risk_probs.numpy() < float(model.event_adapter_risk_selector_threshold))
        & (recovery_probs.numpy() >= float(model.event_adapter_recovery_selector_threshold))
    )
    slowdown_feature_names = list(getattr(model, "event_adapter_slowdown_selector_feature_names", []))
    if slowdown_feature_names:
        slowdown_probs = stage_probability(
            frame,
            feature_names=slowdown_feature_names,
            weights=list(model.event_adapter_slowdown_selector_weights),
            bias=float(model.event_adapter_slowdown_selector_bias),
            mean=list(model.event_adapter_slowdown_selector_feature_mean),
            std=list(model.event_adapter_slowdown_selector_feature_std),
        )
        slowdown_values = slowdown_probs.numpy()
        use_adapter = use_adapter & (
            slowdown_values < float(model.event_adapter_slowdown_selector_threshold)
        )
        slowdown_threshold = float(model.event_adapter_slowdown_selector_threshold)
    else:
        slowdown_values = [float("nan")] * len(frame)
        slowdown_threshold = float("nan")

    result = pd.DataFrame(
        {
            "file_key": features["file_key"],
            f"{prefix}_risk_prob": risk_probs.numpy(),
            f"{prefix}_recovery_prob": recovery_probs.numpy(),
            f"{prefix}_slowdown_prob": slowdown_values,
            f"{prefix}_use_adapter": use_adapter.astype("int64"),
            f"{prefix}_risk_threshold": float(model.event_adapter_risk_selector_threshold),
            f"{prefix}_recovery_threshold": float(model.event_adapter_recovery_selector_threshold),
            f"{prefix}_slowdown_threshold": slowdown_threshold,
        }
    )
    result[f"{prefix}_risk_margin"] = (
        result[f"{prefix}_risk_prob"] - result[f"{prefix}_risk_threshold"]
    )
    result[f"{prefix}_recovery_margin"] = (
        result[f"{prefix}_recovery_prob"] - result[f"{prefix}_recovery_threshold"]
    )
    if slowdown_feature_names:
        result[f"{prefix}_slowdown_margin"] = (
            result[f"{prefix}_slowdown_prob"] - result[f"{prefix}_slowdown_threshold"]
        )
    return result


def decision_change(old_use: bool, new_use: bool) -> str:
    if old_use and new_use:
        return "both_on"
    if (not old_use) and (not new_use):
        return "both_off"
    if old_use and (not new_use):
        return "new_closed_old_on"
    return "new_opened_old_off"


def diagnose_decision(row: pd.Series) -> str:
    change = str(row["decision_change"])
    outcome = str(row["outcome_vs_old"])
    if change == "new_closed_old_on" and outcome == "slower_both_solved":
        return "新 selector 关闭旧 compact 曾开启的 adapter，退回路径慢化"
    if change == "new_closed_old_on" and outcome == "faster_both_solved":
        return "新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速"
    if change == "new_closed_old_on" and outcome == "lost_solution":
        return "关闭旧 compact adapter 后丢解"
    if change == "new_closed_old_on" and outcome == "recovered_timeout":
        return "关闭旧 compact adapter 后新方法仍恢复 timeout"
    if change == "new_opened_old_off" and outcome == "slower_both_solved":
        return "新 selector 打开 adapter 后慢化"
    if change == "new_opened_old_off" and outcome == "faster_both_solved":
        return "新 selector 打开 adapter 后加速"
    if change == "new_opened_old_off" and outcome == "recovered_timeout":
        return "新 selector 打开 adapter 后恢复 timeout"
    if change == "new_opened_old_off" and outcome == "lost_solution":
        return "新 selector 打开 adapter 后丢解"
    if change == "both_on":
        return "两者都开启 adapter，差异来自新 checkpoint/运行路径"
    if change == "both_off":
        return "两者都关闭 adapter，差异主要来自回退求解路径或运行噪声"
    return "边界变化但 outcome 不显著"


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if frame.empty:
        return "_空_"
    table = frame[columns].copy()
    if max_rows is not None:
        table = table.head(max_rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def build_audit() -> pd.DataFrame:
    features = map_cnf_ids_to_file_keys(pd.read_csv(FEATURES_CSV))
    per_instance = pd.read_csv(PER_INSTANCE_CSV)
    old_original = pd.read_csv(OLD_COMPACT_FEATURES_CSV)[
        ["file_key", "selector_use_adapter"]
    ].rename(columns={"selector_use_adapter": "old_original_use_adapter"})

    old_on_new = selector_probabilities(features, OLD_CHECKPOINT, "old_on_new_cache")
    new_probs = selector_probabilities(features, NEW_CHECKPOINT, "new")
    feature_cols = [
        "file_key",
        "cnf_id",
        "risk_prob",
        "recovery_prob",
        "slowdown_prob",
        "selector_use_adapter",
        "warmup_c2000_event_entropy_norm",
        "warmup_c2000_event_top10_mass",
        "warmup_c2000_rho_event_corr",
        "warmup_c2000_delta_abs_mean",
        "warmup_c2000_event_conf_learnt_log_max",
    ]
    feature_cols = [column for column in feature_cols if column in features.columns]
    audit = (
        per_instance.merge(features[feature_cols], on="file_key", how="left")
        .merge(old_original, on="file_key", how="left")
        .merge(old_on_new, on="file_key", how="left")
        .merge(new_probs, on="file_key", how="left")
    )
    audit["old_original_use_adapter"] = audit["old_original_use_adapter"].fillna(0).astype("int64")
    audit["new_use_adapter_actual"] = audit["selector_use_adapter"].astype("int64")
    audit["decision_change"] = audit.apply(
        lambda row: decision_change(
            bool(row["old_original_use_adapter"]),
            bool(row["new_use_adapter_actual"]),
        ),
        axis=1,
    )
    audit["old_weight_cache_shift"] = audit.apply(
        lambda row: decision_change(
            bool(row["old_original_use_adapter"]),
            bool(row["old_on_new_cache_use_adapter"]),
        ),
        axis=1,
    )
    audit["diagnosis"] = audit.apply(diagnose_decision, axis=1)
    audit["new_minus_old_time"] = audit["delta_time_vs_old"]
    audit["new_minus_base_time"] = audit["delta_time_vs_base"]
    audit["adapter_observed_for_threshold_sweep"] = (
        audit["new_use_adapter_actual"].astype(bool) | audit["old_original_use_adapter"].astype(bool)
    ).astype("int64")
    audit["adapter_observation_source"] = "unobserved"
    audit.loc[audit["old_original_use_adapter"].astype(bool), "adapter_observation_source"] = "old_compact_proxy"
    audit.loc[audit["new_use_adapter_actual"].astype(bool), "adapter_observation_source"] = "new_actual"
    return audit


def summarize(audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for change, group in audit.groupby("decision_change", sort=True):
        counts = group["outcome_vs_old"].value_counts()
        rows.append(
            {
                "decision_change": change,
                "n": int(len(group)),
                "old_solved": int(group["old_solved"].sum()),
                "new_solved": int(group["new_solved"].sum()),
                "delta_solved": int(group["new_solved"].sum() - group["old_solved"].sum()),
                "delta_mean_time_vs_old": float(group["delta_time_vs_old"].mean()),
                "faster_both_solved": int(counts.get("faster_both_solved", 0)),
                "slower_both_solved": int(counts.get("slower_both_solved", 0)),
                "tie_both_solved": int(counts.get("tie_both_solved", 0)),
                "recovered_timeout": int(counts.get("recovered_timeout", 0)),
                "lost_solution": int(counts.get("lost_solution", 0)),
                "both_timeout": int(counts.get("both_timeout", 0)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    audit = build_audit()
    summary = summarize(audit)
    focus = audit[audit["file_key"].isin(FOCUS_KEYS)].copy().sort_values("file_key")
    largest_losses = audit.nlargest(15, "delta_time_vs_old")
    largest_wins = audit.nsmallest(15, "delta_time_vs_old")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_CSV.write_text(audit.to_csv(index=False), encoding="utf-8")
    FOCUS_CSV.write_text(focus.to_csv(index=False), encoding="utf-8")
    SUMMARY_CSV.write_text(summary.to_csv(index=False), encoding="utf-8")

    columns_summary = [
        "decision_change",
        "n",
        "old_solved",
        "new_solved",
        "delta_solved",
        "delta_mean_time_vs_old",
        "faster_both_solved",
        "slower_both_solved",
        "tie_both_solved",
        "recovered_timeout",
        "lost_solution",
        "both_timeout",
    ]
    columns_focus = [
        "file_key",
        "difficulty_bucket",
        "base_time",
        "old_time",
        "new_time",
        "delta_time_vs_old",
        "outcome_vs_old",
        "old_original_use_adapter",
        "old_on_new_cache_use_adapter",
        "new_use_adapter_actual",
        "new_risk_prob",
        "new_recovery_prob",
        "new_slowdown_prob",
        "decision_change",
        "old_weight_cache_shift",
        "diagnosis",
    ]
    columns_focus = [column for column in columns_focus if column in audit.columns]
    doc = [
        "# Online-consistent Boundary400 Selector 决策审计",
        "",
        "本审计只使用 `online_consistent_boundary400_full400_selector_features.csv` 作为当前 selector 的在线一致特征证据。",
        "旧 compact 的原始开关只作为“该实例是否已有真实 adapter 分支观测”的参照，不用于新 checkpoint 的决策。",
        "",
        "## 主要结论",
        "",
        "- 新 online-consistent boundary400 checkpoint 与旧 compact 同为 `56/200`，均时从 `46.3484s` 小幅降到 `46.2217s`。",
        "- 大退化 `3sat_46.cnf`、`3sat_196.cnf` 不是新 selector 误开 adapter，而是新 selector 关闭了旧 compact 曾开启且在该次运行中很有效的 adapter 分支。",
        "- 大改善 `3sat_140.cnf` 是新 selector 新开 adapter 后获得的 hard speedup；`3sat_82.cnf` 是关闭旧 compact adapter 后回到更快回退路径。",
        "- 因此下一步应做“基于当前 online cache 的阈值/边界审计”，优先验证是否能重新打开少数有旧 adapter 真实观测的正例，同时不打开没有观测支撑的风险样本。",
        "",
        "## 决策变化汇总",
        "",
        markdown_table(summary, columns_summary),
        "",
        "## 重点样本",
        "",
        markdown_table(focus, columns_focus),
        "",
        "## 最大退化",
        "",
        markdown_table(largest_losses, columns_focus, max_rows=15),
        "",
        "## 最大改善",
        "",
        markdown_table(largest_wins, columns_focus, max_rows=15),
        "",
        "## 输出文件",
        "",
        f"- `{AUDIT_CSV}`",
        f"- `{FOCUS_CSV}`",
        f"- `{SUMMARY_CSV}`",
        "",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(summary.to_string(index=False))
    print(f"wrote {AUDIT_CSV}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
