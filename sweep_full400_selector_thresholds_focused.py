from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sweep_full400_selector_thresholds import (
    AUDIT_CSV,
    DOC_PATH,
    FOCUS,
    OUT_DIR,
    markdown_table,
    prepare_branches,
)


def candidate_grid(frame: pd.DataFrame, column: str) -> np.ndarray:
    values = set(np.arange(0.0, 1.0001, 0.01).round(6).tolist())
    focus = frame[frame["file_key"].isin(FOCUS)][column].astype(float)
    for value in focus.tolist():
        values.add(float(value))
        values.add(float(min(1.000001, value + 1.0e-6)))
        values.add(float(max(0.0, value - 1.0e-6)))
    values.update([0.0, 0.5, 1.0, 1.000001])
    return np.array(sorted(value for value in values if 0.0 <= value <= 1.000001), dtype=np.float32)


def eval_policy(frame: pd.DataFrame, risk_threshold: float, recovery_threshold: float) -> dict:
    use = (
        (frame["stable_risk_prob"].astype(float) < float(risk_threshold))
        & (frame["stable_recovery_prob"].astype(float) >= float(recovery_threshold))
    )
    known_use = use & frame["adapter_observed"].astype(bool)
    unknown = use & ~frame["adapter_observed"].astype(bool)
    solved = frame["base_solved_est"].astype(bool).copy()
    time = frame["base_time_est"].astype(float).copy()
    solved.loc[known_use] = frame.loc[known_use, "adapter_solved_obs"].astype(bool)
    time.loc[known_use] = frame.loc[known_use, "adapter_time_obs"].astype(float)
    lost = frame["base_solved_est"].astype(bool) & known_use & ~frame["adapter_solved_obs"].astype(bool)
    recovered = ~frame["base_solved_est"].astype(bool) & known_use & frame["adapter_solved_obs"].astype(bool)
    row = {
        "risk_threshold": float(risk_threshold),
        "recovery_threshold": float(recovery_threshold),
        "selected": int(use.sum()),
        "unknown_adapter_opened": int(unknown.sum()),
        "supported": int(unknown.sum()) == 0,
        "selector_solved_est": int(solved.sum()),
        "base_solved_est": int(frame["base_solved_est"].sum()),
        "delta_solved_est": int(solved.sum() - frame["base_solved_est"].sum()),
        "lost_solution_est": int(lost.sum()),
        "recovered_timeout_est": int(recovered.sum()),
        "mean_time_est": float(time.mean()),
        "delta_mean_time_vs_base_est": float(time.mean() - frame["base_time_est"].astype(float).mean()),
    }
    for file_key in FOCUS:
        mask = frame["file_key"].eq(file_key)
        if mask.any():
            row[f"use_{file_key}"] = int(use.loc[mask].iloc[0])
    return row


def main() -> None:
    audit = pd.read_csv(AUDIT_CSV)
    frame = prepare_branches(audit)
    risk_values = candidate_grid(frame, "stable_risk_prob")
    recovery_values = candidate_grid(frame, "stable_recovery_prob")
    rows = []
    for risk_threshold in risk_values:
        for recovery_threshold in recovery_values:
            rows.append(eval_policy(frame, risk_threshold, recovery_threshold))
    sweep = pd.DataFrame(rows)
    supported = sweep[sweep["supported"]].copy()
    supported = supported.sort_values(
        by=["lost_solution_est", "recovered_timeout_est", "delta_solved_est", "mean_time_est", "selected"],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)
    strict = supported[
        (supported.get("use_3sat_163.cnf", 0) == 1)
        & (supported.get("use_3sat_88.cnf", 0) == 0)
        & (supported.get("use_3sat_25.cnf", 0) == 0)
    ]
    semi = supported[
        (supported.get("use_3sat_163.cnf", 0) == 1)
        & (supported.get("use_3sat_88.cnf", 0) == 0)
    ]

    current_stable = eval_policy(
        frame,
        float(frame["stable_risk_threshold"].iloc[0]),
        float(frame["stable_recovery_threshold"].iloc[0]),
    )
    old_thresholds = eval_policy(
        frame,
        float(frame["old_risk_threshold"].iloc[0]),
        float(frame["old_recovery_threshold"].iloc[0]),
    )
    best = supported.iloc[0].to_dict()
    compare = pd.DataFrame([current_stable, old_thresholds, best])
    compare.insert(0, "policy", ["current_stable", "old_thresholds_on_stable_weights", "best_supported_focused"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sweep_path = OUT_DIR / "full400_stable_threshold_sweep_focused.csv"
    best_path = OUT_DIR / "full400_stable_threshold_sweep_focused_best.csv"
    compare_path = OUT_DIR / "full400_stable_threshold_sweep_focused_compare.csv"
    sweep.to_csv(sweep_path, index=False)
    supported.head(50).to_csv(best_path, index=False)
    compare.to_csv(compare_path, index=False)

    impossible = (
        "`3sat_163` 要打开需要 `risk_threshold > 0.6994` 且 `recovery_threshold <= 0.6826`；"
        "`3sat_25` 的 `risk_prob=0.5259, recovery_prob=0.7150`，因此任何打开 `3sat_163` 的全局矩形阈值都会同时打开 `3sat_25`。"
    )
    columns = [
        "policy",
        "risk_threshold",
        "recovery_threshold",
        "selected",
        "unknown_adapter_opened",
        "selector_solved_est",
        "delta_solved_est",
        "lost_solution_est",
        "recovered_timeout_est",
        "mean_time_est",
        "use_3sat_163.cnf",
        "use_3sat_88.cnf",
        "use_3sat_25.cnf",
        "use_3sat_140.cnf",
        "use_3sat_82.cnf",
    ]
    best_columns = [column for column in columns if column != "policy"]
    doc = [
        "# Full400 Stable Selector 阈值扫描",
        "",
        "本扫描固定 compact stable 的线性 risk/recovery 权重，只扫描 `risk_threshold` 和 `recovery_threshold`。",
        "使用 0.01 全局网格，并额外加入重点样本的概率邻域；排序只使用已观察过 adapter 结果的 supported 候选。",
        "",
        "## 当前结论",
        "",
        "- 仅靠全局二阈值不能同时做到：打开 `3sat_163.cnf`，关闭 `3sat_88.cnf`，并关闭 `3sat_25.cnf`。",
        f"- 原因：{impossible}",
        "- 这说明问题不是简单 threshold 太松/太紧，而是 stable recovery score 对 easy slowdown 的排序已经和 hard recovery 混在一起。",
        "- 旧 compact 仍应保留为主线；stable 分支目前更适合作为负结果/边界不稳定分析。",
        "",
        "## 代表策略对比",
        "",
        markdown_table(compare, columns),
        "",
        "## 最优 supported 候选 Top 20",
        "",
        markdown_table(supported, best_columns, max_rows=20),
        "",
        "## 重点约束可行性",
        "",
        f"- 严格约束 `use_163=1, use_88=0, use_25=0` 候选数：`{len(strict)}`。",
        f"- 半约束 `use_163=1, use_88=0` 候选数：`{len(semi)}`。",
        "",
        "## 输出文件",
        "",
        f"- `{sweep_path}`",
        f"- `{best_path}`",
        f"- `{compare_path}`",
        "",
    ]
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(compare[columns].to_string(index=False))
    print(f"strict constrained candidates: {len(strict)}")
    print(f"semi constrained candidates: {len(semi)}")
    print(f"wrote {sweep_path}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
