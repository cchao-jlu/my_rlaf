from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


AUDIT_CSV = Path("runs/analysis/full400_selector_decision_audit.csv")
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/full400_selector_threshold_sweep.md")
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
FOCUS = ["3sat_163.cnf", "3sat_122.cnf", "3sat_88.cnf", "3sat_25.cnf", "3sat_140.cnf", "3sat_82.cnf"]


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def threshold_candidates(values: pd.Series, step: float = 0.01) -> list[float]:
    candidates = set(np.arange(0.0, 1.0001, step).round(6).tolist())
    for value in values.astype(float).tolist():
        candidates.add(float(value))
        candidates.add(float(np.nextafter(value, 1.0)))
        candidates.add(float(np.nextafter(value, 0.0)))
    candidates.update([0.0, 0.5, 1.0, 1.000001])
    return sorted(value for value in candidates if 0.0 <= value <= 1.000001)


def prepare_branches(audit: pd.DataFrame) -> pd.DataFrame:
    frame = audit.copy()
    frame["base_result_est"] = frame["oneshot_result"]
    frame["base_solved_est"] = frame["oneshot_solved"].astype(bool)
    off_observed = []
    for _, row in frame.iterrows():
        if not bool(row["stable_use_adapter"]):
            off_observed.append(float(row["compact_stable_time"]))
        elif not bool(row["old_use_adapter"]):
            off_observed.append(float(row["old_compact_time"]))
        else:
            off_observed.append(np.nan)
    off_observed = pd.Series(off_observed)
    overhead_pool = []
    stable_off = frame[~frame["stable_use_adapter"].astype(bool)]
    old_off = frame[~frame["old_use_adapter"].astype(bool)]
    if not stable_off.empty:
        overhead_pool.extend((stable_off["compact_stable_time"] - stable_off["oneshot_time"]).tolist())
    if not old_off.empty:
        overhead_pool.extend((old_off["old_compact_time"] - old_off["oneshot_time"]).tolist())
    overhead_pool = [float(value) for value in overhead_pool if np.isfinite(value)]
    median_overhead = float(np.median(overhead_pool)) if overhead_pool else 0.9
    frame["base_time_est"] = off_observed.fillna(frame["oneshot_time"] + median_overhead)

    adapter_result = []
    adapter_time = []
    adapter_observed = []
    for _, row in frame.iterrows():
        if bool(row["stable_use_adapter"]):
            adapter_result.append(row["compact_stable_result"])
            adapter_time.append(float(row["compact_stable_time"]))
            adapter_observed.append(True)
        elif bool(row["old_use_adapter"]):
            adapter_result.append(row["old_compact_result"])
            adapter_time.append(float(row["old_compact_time"]))
            adapter_observed.append(True)
        else:
            adapter_result.append("UNKNOWN_ADAPTER")
            adapter_time.append(np.nan)
            adapter_observed.append(False)
    frame["adapter_result_obs"] = adapter_result
    frame["adapter_time_obs"] = adapter_time
    frame["adapter_observed"] = adapter_observed
    frame["adapter_solved_obs"] = frame["adapter_result_obs"].map(is_solved)
    frame.attrs["median_off_overhead"] = median_overhead
    return frame


def evaluate_threshold(frame: pd.DataFrame, risk_threshold: float, recovery_threshold: float) -> dict:
    use_adapter = (
        (frame["stable_risk_prob"].astype(float) < float(risk_threshold))
        & (frame["stable_recovery_prob"].astype(float) >= float(recovery_threshold))
    )
    unknown_adapter = use_adapter & ~frame["adapter_observed"].astype(bool)
    known_use = use_adapter & frame["adapter_observed"].astype(bool)
    solved = frame["base_solved_est"].copy()
    time = frame["base_time_est"].astype(float).copy()
    solved.loc[known_use] = frame.loc[known_use, "adapter_solved_obs"].astype(bool)
    time.loc[known_use] = frame.loc[known_use, "adapter_time_obs"].astype(float)
    # Unknown adapter openings are kept as base for numeric stability but marked invalid.
    lost = (frame["base_solved_est"].astype(bool) & known_use & ~frame["adapter_solved_obs"].astype(bool))
    recovered = (~frame["base_solved_est"].astype(bool) & known_use & frame["adapter_solved_obs"].astype(bool))
    row = {
        "risk_threshold": float(risk_threshold),
        "recovery_threshold": float(recovery_threshold),
        "selected": int(use_adapter.sum()),
        "selected_fraction": float(use_adapter.mean()),
        "unknown_adapter_opened": int(unknown_adapter.sum()),
        "supported": int(unknown_adapter.sum()) == 0,
        "selector_solved_est": int(solved.sum()),
        "base_solved_est": int(frame["base_solved_est"].sum()),
        "delta_solved_est": int(solved.sum() - frame["base_solved_est"].sum()),
        "lost_solution_est": int(lost.sum()),
        "recovered_timeout_est": int(recovered.sum()),
        "mean_time_est": float(time.mean()),
        "delta_mean_time_vs_base_est": float(time.mean() - frame["base_time_est"].mean()),
    }
    for file_key in FOCUS:
        match = frame["file_key"].eq(file_key)
        if match.any():
            row[f"use_{file_key}"] = int(use_adapter.loc[match].iloc[0])
    return row


def objective_key(row: pd.Series) -> tuple:
    return (
        -int(row["lost_solution_est"]),
        int(row["recovered_timeout_est"]),
        int(row["delta_solved_est"]),
        -float(row["mean_time_est"]),
        -int(row["selected"]),
    )


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


def main() -> None:
    audit = pd.read_csv(AUDIT_CSV)
    frame = prepare_branches(audit)
    risk_values = threshold_candidates(frame["stable_risk_prob"], step=0.01)
    recovery_values = threshold_candidates(frame["stable_recovery_prob"], step=0.01)
    rows = [
        evaluate_threshold(frame, risk_threshold=risk_threshold, recovery_threshold=recovery_threshold)
        for risk_threshold in risk_values
        for recovery_threshold in recovery_values
    ]
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

    current_stable = evaluate_threshold(
        frame,
        risk_threshold=float(frame["stable_risk_threshold"].iloc[0]),
        recovery_threshold=float(frame["stable_recovery_threshold"].iloc[0]),
    )
    current_old_thresholds_on_stable_weights = evaluate_threshold(
        frame,
        risk_threshold=float(frame["old_risk_threshold"].iloc[0]),
        recovery_threshold=float(frame["old_recovery_threshold"].iloc[0]),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sweep_path = OUT_DIR / "full400_stable_threshold_sweep.csv"
    best_path = OUT_DIR / "full400_stable_threshold_sweep_best.csv"
    sweep.to_csv(sweep_path, index=False)
    supported.head(50).to_csv(best_path, index=False)

    impossible_reason = ""
    if constrained.empty:
        impossible_reason = (
            "`3sat_163` 要打开需要 `risk_threshold > 0.6994` 且 "
            "`recovery_threshold <= 0.6826`；但 `3sat_25` 的 stable recovery_prob=0.7150，"
            "risk_prob=0.5259，因此任何打开 `3sat_163` 的矩形阈值都会同时打开 `3sat_25`。"
        )

    compare = pd.DataFrame([current_stable, current_old_thresholds_on_stable_weights, best.to_dict()])
    compare.insert(0, "policy", ["current_stable", "old_thresholds_on_stable_weights", "best_supported_sweep"])
    compare_path = OUT_DIR / "full400_stable_threshold_sweep_compare.csv"
    compare.to_csv(compare_path, index=False)

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
