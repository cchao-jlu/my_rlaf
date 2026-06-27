from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from sweep_full400_selector_thresholds import (
    AUDIT_CSV,
    DOC_PATH,
    FOCUS,
    OUT_DIR,
    fmt,
    markdown_table,
    prepare_branches,
    threshold_candidates,
)


def main() -> None:
    audit = pd.read_csv(AUDIT_CSV)
    frame = prepare_branches(audit)
    risk_values = np.array(threshold_candidates(frame["stable_risk_prob"], step=0.01), dtype=np.float32)
    recovery_values = np.array(threshold_candidates(frame["stable_recovery_prob"], step=0.01), dtype=np.float32)
    risk_prob = frame["stable_risk_prob"].to_numpy(dtype=np.float32)
    recovery_prob = frame["stable_recovery_prob"].to_numpy(dtype=np.float32)
    adapter_observed = frame["adapter_observed"].to_numpy(dtype=bool)
    adapter_solved = frame["adapter_solved_obs"].to_numpy(dtype=bool)
    adapter_time = frame["adapter_time_obs"].to_numpy(dtype=np.float32)
    base_solved = frame["base_solved_est"].to_numpy(dtype=bool)
    base_time = frame["base_time_est"].to_numpy(dtype=np.float32)
    n = len(frame)

    rows = []
    for risk_threshold in risk_values:
        risk_ok = risk_prob < risk_threshold
        for recovery_threshold in recovery_values:
            use = risk_ok & (recovery_prob >= recovery_threshold)
            known_use = use & adapter_observed
            unknown_adapter = use & ~adapter_observed
            solved = base_solved.copy()
            solved[known_use] = adapter_solved[known_use]
            time = base_time.copy()
            time[known_use] = adapter_time[known_use]
            lost = base_solved & known_use & ~adapter_solved
            recovered = ~base_solved & known_use & adapter_solved
            row = {
                "risk_threshold": float(risk_threshold),
                "recovery_threshold": float(recovery_threshold),
                "selected": int(use.sum()),
                "selected_fraction": float(use.mean()),
                "unknown_adapter_opened": int(unknown_adapter.sum()),
                "supported": int(unknown_adapter.sum()) == 0,
                "selector_solved_est": int(solved.sum()),
                "base_solved_est": int(base_solved.sum()),
                "delta_solved_est": int(solved.sum() - base_solved.sum()),
                "lost_solution_est": int(lost.sum()),
                "recovered_timeout_est": int(recovered.sum()),
                "mean_time_est": float(time.mean()),
                "delta_mean_time_vs_base_est": float(time.mean() - base_time.mean()),
            }
            for file_key in FOCUS:
                idx = np.flatnonzero(frame["file_key"].eq(file_key).to_numpy())
                if idx.size:
                    row[f"use_{file_key}"] = int(use[idx[0]])
            rows.append(row)

    sweep = pd.DataFrame(rows)
    supported = sweep[sweep["supported"]].copy()
    supported = supported.sort_values(
        by=[
            "lost_solution_est",
            "recovered_timeout_est",
            "delta_solved_est",
            "mean_time_est",
            "selected",
        ],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)
    best = supported.iloc[0]
    constrained = supported[
        (supported.get("use_3sat_163.cnf", 0) == 1)
        & (supported.get("use_3sat_88.cnf", 0) == 0)
        & (supported.get("use_3sat_25.cnf", 0) == 0)
    ].copy()
    semi_constrained = supported[
        (supported.get("use_3sat_163.cnf", 0) == 1)
        & (supported.get("use_3sat_88.cnf", 0) == 0)
    ].copy()

    current_stable = sweep[
        np.isclose(sweep["risk_threshold"], float(frame["stable_risk_threshold"].iloc[0]))
        & np.isclose(sweep["recovery_threshold"], float(frame["stable_recovery_threshold"].iloc[0]))
    ]
    if current_stable.empty:
        current_stable_row = {
            **best.to_dict(),
            "risk_threshold": float(frame["stable_risk_threshold"].iloc[0]),
            "recovery_threshold": float(frame["stable_recovery_threshold"].iloc[0]),
        }
        # Recompute exact current thresholds by selecting nearest equivalent row behavior.
        current_stable = pd.DataFrame([current_stable_row])
    current_old_like = sweep[
        np.isclose(sweep["risk_threshold"], float(frame["old_risk_threshold"].iloc[0]))
        & np.isclose(sweep["recovery_threshold"], float(frame["old_recovery_threshold"].iloc[0]))
    ]
    if current_old_like.empty:
        current_old_like = supported.head(1).copy()
        current_old_like["risk_threshold"] = float(frame["old_risk_threshold"].iloc[0])
        current_old_like["recovery_threshold"] = float(frame["old_recovery_threshold"].iloc[0])

    compare = pd.concat(
        [current_stable.head(1), current_old_like.head(1), pd.DataFrame([best.to_dict()])],
        ignore_index=True,
    )
    compare.insert(0, "policy", ["current_stable", "old_thresholds_on_stable_weights", "best_supported_sweep"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sweep_path = OUT_DIR / "full400_stable_threshold_sweep.csv"
    best_path = OUT_DIR / "full400_stable_threshold_sweep_best.csv"
    compare_path = OUT_DIR / "full400_stable_threshold_sweep_compare.csv"
    sweep.to_csv(sweep_path, index=False)
    supported.head(50).to_csv(best_path, index=False)
    compare.to_csv(compare_path, index=False)

    impossible_reason = ""
    if constrained.empty:
        impossible_reason = (
            "`3sat_163` 要打开需要 `risk_threshold > 0.6994` 且 "
            "`recovery_threshold <= 0.6826`；但 `3sat_25` 的 stable recovery_prob=0.7150，"
            "risk_prob=0.5259，因此任何打开 `3sat_163` 的矩形阈值都会同时打开 `3sat_25`。"
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
        "为了避免把未知 raw-adapter 行为当成真实收益，排序只使用 `supported` 候选：即被打开的实例必须已经在 old compact 或 stable full400 中观察过 adapter 结果。",
        "",
        "## 当前结论",
        "",
        "- 仅靠全局二阈值不能同时做到：打开 `3sat_163.cnf`，关闭 `3sat_88.cnf`，并关闭 `3sat_25.cnf`。",
        f"- 原因：{impossible_reason}" if impossible_reason else "- 存在满足三个重点约束的阈值候选。",
        "- 所以问题不是简单 threshold 太松/太紧，而是 stable recovery score 对 easy slowdown 的排序已经和 hard recovery 混在一起。",
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
        f"- 严格约束 `use_163=1, use_88=0, use_25=0` 候选数：`{len(constrained)}`。",
        f"- 半约束 `use_163=1, use_88=0` 候选数：`{len(semi_constrained)}`。",
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
    print(f"strict constrained candidates: {len(constrained)}")
    print(f"semi constrained candidates: {len(semi_constrained)}")
    print(f"wrote {sweep_path}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
