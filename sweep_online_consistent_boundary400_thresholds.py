from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


AUDIT_CSV = Path("runs/analysis/online_consistent_boundary400_decision_audit.csv")
OUT_DIR = Path("runs/analysis")
SWEEP_CSV = OUT_DIR / "online_consistent_boundary400_threshold_sweep.csv"
BEST_CSV = OUT_DIR / "online_consistent_boundary400_threshold_sweep_best.csv"
COMPARE_CSV = OUT_DIR / "online_consistent_boundary400_threshold_sweep_compare.csv"
DOC_PATH = Path("docs/online_consistent_boundary400_threshold_sweep.md")
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
FOCUS_KEYS = [
    "3sat_46.cnf",
    "3sat_196.cnf",
    "3sat_140.cnf",
    "3sat_82.cnf",
    "3sat_188.cnf",
    "3sat_97.cnf",
    "3sat_163.cnf",
    "3sat_25.cnf",
    "3sat_88.cnf",
]


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def threshold_candidates(
    values: pd.Series,
    *,
    current: float | None = None,
    focus_values: pd.Series | None = None,
    step: float = 0.05,
) -> list[float]:
    candidates = set(np.arange(0.0, 1.0001, step).round(6).tolist())
    numeric = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if not numeric.empty:
        for quantile in np.linspace(0.05, 0.95, 19):
            candidates.add(float(numeric.quantile(float(quantile))))
    if current is not None:
        candidates.add(float(current))
    if focus_values is not None:
        focus_numeric = pd.to_numeric(focus_values, errors="coerce").dropna().astype(float)
        for value in focus_numeric.tolist():
            candidates.add(float(value))
            candidates.add(float(np.nextafter(value, 1.0)))
            candidates.add(float(np.nextafter(value, 0.0)))
    candidates.update([0.0, 0.5, 1.0, 1.000001])
    return sorted(value for value in candidates if 0.0 <= value <= 1.000001)


def prepare_policy_branches(audit: pd.DataFrame) -> pd.DataFrame:
    frame = audit.copy()
    for canonical, fallback in [
        ("new_risk_prob", "risk_prob"),
        ("new_recovery_prob", "recovery_prob"),
        ("new_slowdown_prob", "slowdown_prob"),
    ]:
        if canonical not in frame.columns and fallback in frame.columns:
            frame[canonical] = frame[fallback]
    frame["base_solved_est"] = frame["base_solved"].astype(bool)
    frame["base_time_est"] = frame["base_time"].astype(float)
    frame["current_solved"] = frame["new_solved"].astype(bool)
    frame["current_time"] = frame["new_time"].astype(float)
    current_use_column = "new_use_adapter_actual"
    if current_use_column not in frame.columns:
        current_use_column = "selector_use_adapter"
    frame["current_use_adapter"] = frame[current_use_column].astype(bool)
    frame["old_original_use_adapter"] = frame["old_original_use_adapter"].astype(bool)

    adapter_solved = []
    adapter_time = []
    adapter_source = []
    adapter_observed = []
    for _, row in frame.iterrows():
        if bool(row["current_use_adapter"]):
            adapter_solved.append(bool(row["new_solved"]))
            adapter_time.append(float(row["new_time"]))
            adapter_source.append("new_actual")
            adapter_observed.append(True)
        elif bool(row["old_original_use_adapter"]):
            adapter_solved.append(bool(row["old_solved"]))
            adapter_time.append(float(row["old_time"]))
            adapter_source.append("old_compact_proxy")
            adapter_observed.append(True)
        else:
            adapter_solved.append(False)
            adapter_time.append(np.nan)
            adapter_source.append("unobserved")
            adapter_observed.append(False)
    frame["adapter_solved_obs"] = adapter_solved
    frame["adapter_time_obs"] = adapter_time
    frame["adapter_observation_source"] = adapter_source
    frame["adapter_observed"] = adapter_observed
    return frame


def evaluate_threshold_policy(
    frame: pd.DataFrame,
    risk_threshold: float,
    recovery_threshold: float,
    slowdown_threshold: float,
) -> dict[str, object]:
    use_adapter = (
        (frame["new_risk_prob"].astype(float) < float(risk_threshold))
        & (frame["new_recovery_prob"].astype(float) >= float(recovery_threshold))
        & (frame["new_slowdown_prob"].astype(float) < float(slowdown_threshold))
    )
    supported_use = use_adapter & frame["adapter_observed"].astype(bool)
    unsupported_open = use_adapter & ~frame["adapter_observed"].astype(bool)
    current_use = frame["current_use_adapter"].astype(bool)
    closed_current = current_use & ~use_adapter
    opened_supported = supported_use & ~current_use

    solved = frame["current_solved"].astype(bool).copy()
    time = frame["current_time"].astype(float).copy()
    solved.loc[closed_current] = frame.loc[closed_current, "base_solved_est"].astype(bool)
    time.loc[closed_current] = frame.loc[closed_current, "base_time_est"].astype(float)
    solved.loc[opened_supported] = frame.loc[opened_supported, "adapter_solved_obs"].astype(bool)
    time.loc[opened_supported] = frame.loc[opened_supported, "adapter_time_obs"].astype(float)

    base_solved = frame["base_solved_est"].astype(bool)
    current_solved = frame["current_solved"].astype(bool)
    lost_vs_base = base_solved & ~solved
    recovered_vs_base = ~base_solved & solved
    row = {
        "risk_threshold": float(risk_threshold),
        "recovery_threshold": float(recovery_threshold),
        "slowdown_threshold": float(slowdown_threshold),
        "selected": int(use_adapter.sum()),
        "selected_fraction": float(use_adapter.mean()),
        "supported_selected": int(supported_use.sum()),
        "unsupported_opened": int(unsupported_open.sum()),
        "selector_solved_est": int(solved.sum()),
        "base_solved_est": int(base_solved.sum()),
        "current_solved": int(current_solved.sum()),
        "delta_solved_vs_base_est": int(solved.sum() - base_solved.sum()),
        "delta_solved_vs_current_est": int(solved.sum() - current_solved.sum()),
        "lost_solution_vs_base_est": int(lost_vs_base.sum()),
        "recovered_timeout_vs_base_est": int(recovered_vs_base.sum()),
        "mean_time_est": float(time.mean()),
        "delta_mean_time_vs_base_est": float(time.mean() - frame["base_time_est"].astype(float).mean()),
        "delta_mean_time_vs_current_est": float(time.mean() - frame["current_time"].astype(float).mean()),
        "closed_current_adapter": int(closed_current.sum()),
        "reopened_old_adapter_proxy": int(
            (
                use_adapter
                & ~frame["current_use_adapter"].astype(bool)
                & frame["old_original_use_adapter"].astype(bool)
            ).sum()
        ),
    }
    for key in FOCUS_KEYS:
        mask = frame["file_key"].eq(key)
        if mask.any():
            row[f"use_{key}"] = int(use_adapter.loc[mask].iloc[0])
    return row


def sweep_thresholds(frame: pd.DataFrame) -> pd.DataFrame:
    focus = frame[frame["file_key"].isin(FOCUS_KEYS)]
    risk_values = threshold_candidates(
        frame["new_risk_prob"],
        current=float(frame["new_risk_threshold"].iloc[0]),
        focus_values=focus["new_risk_prob"],
    )
    recovery_values = threshold_candidates(
        frame["new_recovery_prob"],
        current=float(frame["new_recovery_threshold"].iloc[0]),
        focus_values=focus["new_recovery_prob"],
    )
    slowdown_values = threshold_candidates(
        frame["new_slowdown_prob"],
        current=float(frame["new_slowdown_threshold"].iloc[0]),
        focus_values=focus["new_slowdown_prob"],
    )
    risk_prob = frame["new_risk_prob"].to_numpy(dtype=np.float32)
    recovery_prob = frame["new_recovery_prob"].to_numpy(dtype=np.float32)
    slowdown_prob = frame["new_slowdown_prob"].to_numpy(dtype=np.float32)
    adapter_observed = frame["adapter_observed"].to_numpy(dtype=bool)
    adapter_solved = frame["adapter_solved_obs"].to_numpy(dtype=bool)
    adapter_time = frame["adapter_time_obs"].to_numpy(dtype=np.float32)
    base_solved = frame["base_solved_est"].to_numpy(dtype=bool)
    base_time = frame["base_time_est"].to_numpy(dtype=np.float32)
    current_solved = frame["current_solved"].to_numpy(dtype=bool)
    current_time = frame["current_time"].to_numpy(dtype=np.float32)
    current_use = frame["current_use_adapter"].to_numpy(dtype=bool)
    old_use = frame["old_original_use_adapter"].to_numpy(dtype=bool)
    current_time_mean = float(frame["current_time"].astype(float).mean())
    base_time_mean = float(base_time.mean())
    base_solved_count = int(base_solved.sum())
    current_solved_count = int(current_solved.sum())
    focus_indices = {
        key: int(indices[0])
        for key in FOCUS_KEYS
        for indices in [np.flatnonzero(frame["file_key"].eq(key).to_numpy())]
        if len(indices) > 0
    }
    rows = []
    for risk_threshold in risk_values:
        risk_ok = risk_prob < float(risk_threshold)
        for recovery_threshold in recovery_values:
            rec_ok = recovery_prob >= float(recovery_threshold)
            base_mask = risk_ok & rec_ok
            for slowdown_threshold in slowdown_values:
                use_adapter = base_mask & (slowdown_prob < float(slowdown_threshold))
                supported_use = use_adapter & adapter_observed
                unsupported_open = use_adapter & ~adapter_observed
                closed_current = current_use & ~use_adapter
                opened_supported = supported_use & ~current_use
                solved = current_solved.copy()
                time = current_time.copy()
                solved[closed_current] = base_solved[closed_current]
                time[closed_current] = base_time[closed_current]
                solved[opened_supported] = adapter_solved[opened_supported]
                time[opened_supported] = adapter_time[opened_supported]
                lost = base_solved & ~solved
                recovered = ~base_solved & solved
                row = {
                    "risk_threshold": float(risk_threshold),
                    "recovery_threshold": float(recovery_threshold),
                    "slowdown_threshold": float(slowdown_threshold),
                    "selected": int(use_adapter.sum()),
                    "selected_fraction": float(use_adapter.mean()),
                    "supported_selected": int(supported_use.sum()),
                    "unsupported_opened": int(unsupported_open.sum()),
                    "selector_solved_est": int(solved.sum()),
                    "base_solved_est": base_solved_count,
                    "current_solved": current_solved_count,
                    "delta_solved_vs_base_est": int(solved.sum() - base_solved_count),
                    "delta_solved_vs_current_est": int(solved.sum() - current_solved_count),
                    "lost_solution_vs_base_est": int(lost.sum()),
                    "recovered_timeout_vs_base_est": int(recovered.sum()),
                    "mean_time_est": float(time.mean()),
                    "delta_mean_time_vs_base_est": float(time.mean() - base_time_mean),
                    "delta_mean_time_vs_current_est": float(time.mean() - current_time_mean),
                    "closed_current_adapter": int(closed_current.sum()),
                    "reopened_old_adapter_proxy": int((use_adapter & ~current_use & old_use).sum()),
                }
                for key, index in focus_indices.items():
                    row[f"use_{key}"] = int(use_adapter[index])
                rows.append(row)
    return pd.DataFrame(rows)


def sort_candidates(sweep: pd.DataFrame) -> pd.DataFrame:
    supported = sweep[sweep["unsupported_opened"].eq(0)].copy()
    return supported.sort_values(
        by=[
            "lost_solution_vs_base_est",
            "selector_solved_est",
            "recovered_timeout_vs_base_est",
            "mean_time_est",
            "selected",
        ],
        ascending=[True, False, False, True, True],
    ).reset_index(drop=True)


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


def current_threshold_row(frame: pd.DataFrame) -> dict[str, object]:
    return evaluate_threshold_policy(
        frame,
        risk_threshold=float(frame["new_risk_threshold"].iloc[0]),
        recovery_threshold=float(frame["new_recovery_threshold"].iloc[0]),
        slowdown_threshold=float(frame["new_slowdown_threshold"].iloc[0]),
    )


def main() -> None:
    audit = pd.read_csv(AUDIT_CSV)
    frame = prepare_policy_branches(audit)
    sweep = sweep_thresholds(frame)
    best = sort_candidates(sweep)
    current = current_threshold_row(frame)
    best_row = best.iloc[0].to_dict() if not best.empty else current
    compare = pd.DataFrame([current, best_row])
    compare.insert(0, "policy", ["current_online_boundary400", "best_supported_threshold"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SWEEP_CSV.write_text(sweep.to_csv(index=False), encoding="utf-8")
    BEST_CSV.write_text(best.head(100).to_csv(index=False), encoding="utf-8")
    COMPARE_CSV.write_text(compare.to_csv(index=False), encoding="utf-8")

    columns = [
        "policy",
        "risk_threshold",
        "recovery_threshold",
        "slowdown_threshold",
        "selected",
        "unsupported_opened",
        "selector_solved_est",
        "delta_solved_vs_base_est",
        "delta_solved_vs_current_est",
        "lost_solution_vs_base_est",
        "recovered_timeout_vs_base_est",
        "mean_time_est",
        "delta_mean_time_vs_current_est",
        "closed_current_adapter",
        "reopened_old_adapter_proxy",
        "use_3sat_46.cnf",
        "use_3sat_196.cnf",
        "use_3sat_140.cnf",
        "use_3sat_82.cnf",
        "use_3sat_188.cnf",
        "use_3sat_97.cnf",
        "use_3sat_163.cnf",
    ]
    columns = [column for column in columns if column in compare.columns]
    best_columns = [column for column in columns if column != "policy"]
    no_unsupported = sweep[sweep["unsupported_opened"].eq(0)]
    preserve_solved = no_unsupported[
        no_unsupported["selector_solved_est"].ge(int(current["selector_solved_est"]))
    ]
    lower_time = preserve_solved[
        preserve_solved["mean_time_est"].lt(float(current["mean_time_est"]) - 1.0e-9)
    ]
    doc = [
        "# Online-consistent Boundary400 阈值扫描",
        "",
        "本扫描固定 online-consistent boundary400 的 risk/recovery/slowdown 线性权重，只扫描三个阈值。",
        "候选策略只对已有真实观测的 adapter 分支记功：当前新 checkpoint 开过的样本使用新实测，旧 compact 开过但新关掉的样本可用旧 compact adapter 分支作保守 proxy；没有任何 adapter 观测的样本若被打开，记为 `unsupported_opened`，不进入主排序。",
        "",
        "## 当前结论",
        "",
        f"- 当前策略估计为 `{int(current['selector_solved_est'])}/200`，均时 `{float(current['mean_time_est']):.4f}s`，与实测 full400 一致。",
        f"- 在不打开未知 adapter 分支的 supported 搜索空间内，可保持/超过当前解出数的候选数为 `{len(preserve_solved)}`，其中均时更低的候选数为 `{len(lower_time)}`。",
        "- 如果最优 supported 候选只带来估计收益，仍需要单独跑 wall-clock 确认；因为旧 compact proxy 与新 checkpoint 的 adapter 分支不是完全同一运行路径。",
        "",
        "## 代表策略",
        "",
        markdown_table(compare, columns),
        "",
        "## supported 候选 Top 30",
        "",
        markdown_table(best, best_columns, max_rows=30),
        "",
        "## 输出文件",
        "",
        f"- `{SWEEP_CSV}`",
        f"- `{BEST_CSV}`",
        f"- `{COMPARE_CSV}`",
        "",
    ]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(compare[columns].to_string(index=False))
    print(f"wrote {SWEEP_CSV}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
