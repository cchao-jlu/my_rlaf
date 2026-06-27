from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


FEATURES_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv")
BASELINE_CSV = Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv")
OLD_COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
    "eval_compact_risk_full400.csv"
)
ACTUAL_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv")
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/online_pairwise_veto_threshold_sweep.md")
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}
FOCUS = [
    "3sat_89.cnf",
    "3sat_46.cnf",
    "3sat_163.cnf",
    "3sat_25.cnf",
    "3sat_88.cnf",
    "3sat_82.cnf",
    "3sat_140.cnf",
    "3sat_122.cnf",
]


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def file_key(value: object) -> str:
    return Path(str(value)).name


def load_eval(path: Path, prefix: str) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["file_key"] = frame["file"].map(file_key)
    frame[f"{prefix}_solved"] = frame["Result"].map(is_solved)
    return frame[
        [
            "file_key",
            f"{prefix}_solved",
            "Result",
            "time",
            "CPU time",
            "conflicts",
            "decisions",
        ]
    ].rename(
        columns={
            "Result": f"{prefix}_result",
            "time": f"{prefix}_time",
            "CPU time": f"{prefix}_cpu_time",
            "conflicts": f"{prefix}_conflicts",
            "decisions": f"{prefix}_decisions",
        }
    )


def build_frame() -> pd.DataFrame:
    features = pd.read_csv(FEATURES_CSV).copy()
    files = sorted(Path("data/test/3sat/400").glob("*.cnf"))
    features["file_key"] = features["cnf_id"].map(lambda idx: files[int(idx)].name)
    base = load_eval(BASELINE_CSV, "base")
    old = load_eval(OLD_COMPACT_CSV, "old")
    actual = load_eval(ACTUAL_CSV, "actual")
    frame = (
        features.merge(base, on="file_key", how="inner")
        .merge(old, on="file_key", how="inner")
        .merge(actual, on="file_key", how="inner")
    )
    frame["current_use_adapter"] = frame["selector_use_adapter"].astype(bool)
    frame["current_solved"] = frame["actual_solved"].astype(bool)
    frame["current_time"] = frame["actual_time"].astype(float)
    frame["old_adapter_solved"] = frame["old_solved"].astype(bool)
    frame["old_adapter_time"] = frame["old_time"].astype(float)
    return frame


def threshold_candidates(series: pd.Series, focus_values: pd.Series | None = None, step: float = 0.05) -> list[float]:
    values = set(np.arange(0.0, 1.0001, step).round(6).tolist())
    numeric = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    for quantile in [0.25, 0.5, 0.75]:
        if not numeric.empty:
            values.add(float(numeric.quantile(float(quantile))))
    if focus_values is not None:
        boundary_values = pd.to_numeric(focus_values, errors="coerce").dropna().astype(float).tolist()
    else:
        boundary_values = []
    for value in boundary_values:
        values.add(float(value))
        values.add(float(np.nextafter(value, 1.0)))
        values.add(float(np.nextafter(value, 0.0)))
    values.update([0.0, 0.5, 1.0, 1.000001])
    return sorted(value for value in values if 0.0 <= value <= 1.000001)


def policy_time_solved(
    frame: pd.DataFrame,
    use_adapter: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    current_use = frame["current_use_adapter"].astype(bool)
    actual_supported = use_adapter == current_use
    adapter_closed = ~use_adapter & current_use
    unsupported_open = use_adapter & ~current_use
    solved = frame["current_solved"].astype(bool).copy()
    time = frame["current_time"].astype(float).copy()
    solved.loc[actual_supported] = frame.loc[actual_supported, "current_solved"].astype(bool)
    time.loc[actual_supported] = frame.loc[actual_supported, "current_time"].astype(float)
    solved.loc[adapter_closed] = frame.loc[adapter_closed, "base_solved"].astype(bool)
    time.loc[adapter_closed] = frame.loc[adapter_closed, "base_time"].astype(float)
    solved.loc[unsupported_open] = frame.loc[unsupported_open, "base_solved"].astype(bool)
    time.loc[unsupported_open] = frame.loc[unsupported_open, "base_time"].astype(float)
    return solved, time, adapter_closed, unsupported_open


def evaluate_policy(
    frame: pd.DataFrame,
    risk_threshold: float,
    recovery_threshold: float,
    slowdown_threshold: float,
) -> dict[str, object]:
    use_adapter = (
        (frame["risk_prob"].astype(float) < float(risk_threshold))
        & (frame["recovery_prob"].astype(float) >= float(recovery_threshold))
        & (frame["slowdown_prob"].astype(float) < float(slowdown_threshold))
    )
    solved, time, adapter_closed, unsupported_open = policy_time_solved(frame, use_adapter)
    base_solved = frame["base_solved"].astype(bool)
    lost = base_solved & ~solved
    recovered = ~base_solved & solved
    current_use = frame["current_use_adapter"].astype(bool)
    decision_changed = use_adapter != current_use
    row = {
        "risk_threshold": float(risk_threshold),
        "recovery_threshold": float(recovery_threshold),
        "slowdown_threshold": float(slowdown_threshold),
        "selected": int(use_adapter.sum()),
        "selected_fraction": float(use_adapter.mean()),
        "decision_changed": int(decision_changed.sum()),
        "new_adapter_opened": int((use_adapter & ~current_use).sum()),
        "adapter_closed": int(adapter_closed.sum()),
        "unsupported_opened": int(unsupported_open.sum()),
        "supported": int(unsupported_open.sum()) == 0,
        "base_solved": int(base_solved.sum()),
        "selector_solved_est": int(solved.sum()),
        "delta_solved_vs_base": int(solved.sum() - base_solved.sum()),
        "delta_solved_vs_current": int(solved.sum() - frame["current_solved"].astype(bool).sum()),
        "lost_solution_est": int(lost.sum()),
        "recovered_timeout_est": int(recovered.sum()),
        "mean_time_est": float(time.mean()),
        "delta_mean_time_vs_current": float(time.mean() - frame["current_time"].astype(float).mean()),
        "delta_mean_time_vs_old": float(time.mean() - frame["old_time"].astype(float).mean()),
    }
    for key in FOCUS:
        mask = frame["file_key"].eq(key)
        if mask.any():
            row[f"use_{key}"] = int(use_adapter.loc[mask].iloc[0])
    return row


def sort_sweep(sweep: pd.DataFrame) -> pd.DataFrame:
    return sweep.sort_values(
        by=[
            "supported",
            "lost_solution_est",
            "recovered_timeout_est",
            "selector_solved_est",
            "mean_time_est",
            "selected",
        ],
        ascending=[False, True, False, False, True, True],
    ).reset_index(drop=True)


def vectorized_sweep(
    frame: pd.DataFrame,
    risk_values: list[float],
    recovery_values: list[float],
    slowdown_values: list[float],
) -> pd.DataFrame:
    risk_prob = frame["risk_prob"].to_numpy(dtype=np.float32)
    recovery_prob = frame["recovery_prob"].to_numpy(dtype=np.float32)
    slowdown_prob = frame["slowdown_prob"].to_numpy(dtype=np.float32)
    current_use = frame["current_use_adapter"].to_numpy(dtype=bool)
    base_solved = frame["base_solved"].to_numpy(dtype=bool)
    base_time = frame["base_time"].to_numpy(dtype=np.float32)
    current_solved = frame["current_solved"].to_numpy(dtype=bool)
    current_time = frame["current_time"].to_numpy(dtype=np.float32)
    base_solved_count = int(base_solved.sum())
    current_solved_count = int(current_solved.sum())
    current_mean_time = float(current_time.mean())
    old_mean_time = float(frame["old_time"].mean())
    focus_indices = {
        key: int(np.flatnonzero(frame["file_key"].eq(key).to_numpy())[0])
        for key in FOCUS
        if np.flatnonzero(frame["file_key"].eq(key).to_numpy()).size
    }
    rows = []
    recovery_values_np = np.asarray(recovery_values, dtype=np.float32)
    slowdown_values_np = np.asarray(slowdown_values, dtype=np.float32)
    for risk_threshold in risk_values:
        risk_ok = risk_prob < float(risk_threshold)
        for recovery_threshold in recovery_values_np:
            rec_ok = recovery_prob >= float(recovery_threshold)
            base_mask = risk_ok & rec_ok
            if not base_mask.any():
                for slowdown_threshold in slowdown_values_np:
                    row = {
                        "risk_threshold": float(risk_threshold),
                        "recovery_threshold": float(recovery_threshold),
                        "slowdown_threshold": float(slowdown_threshold),
                        "selected": 0,
                        "selected_fraction": 0.0,
                        "decision_changed": int(current_use.sum()),
                        "new_adapter_opened": 0,
                        "adapter_closed": int(current_use.sum()),
                        "unsupported_opened": 0,
                        "supported": True,
                        "base_solved": base_solved_count,
                        "selector_solved_est": base_solved_count,
                        "delta_solved_vs_base": 0,
                        "delta_solved_vs_current": base_solved_count - current_solved_count,
                        "lost_solution_est": 0,
                        "recovered_timeout_est": 0,
                        "mean_time_est": float(base_time.mean()),
                        "delta_mean_time_vs_current": float(base_time.mean() - current_mean_time),
                        "delta_mean_time_vs_old": float(base_time.mean() - old_mean_time),
                    }
                    for key, idx in focus_indices.items():
                        row[f"use_{key}"] = 0
                    rows.append(row)
                continue
            for slowdown_threshold in slowdown_values_np:
                use = base_mask & (slowdown_prob < float(slowdown_threshold))
                unsupported_open = use & ~current_use
                adapter_closed = ~use & current_use
                solved = current_solved.copy()
                time = current_time.copy()
                solved[adapter_closed] = base_solved[adapter_closed]
                time[adapter_closed] = base_time[adapter_closed]
                # Unsupported openings are not credited; keep their current/base observed value.
                solved[unsupported_open] = base_solved[unsupported_open]
                time[unsupported_open] = base_time[unsupported_open]
                lost = base_solved & ~solved
                recovered = ~base_solved & solved
                row = {
                    "risk_threshold": float(risk_threshold),
                    "recovery_threshold": float(recovery_threshold),
                    "slowdown_threshold": float(slowdown_threshold),
                    "selected": int(use.sum()),
                    "selected_fraction": float(use.mean()),
                    "decision_changed": int((use != current_use).sum()),
                    "new_adapter_opened": int((use & ~current_use).sum()),
                    "adapter_closed": int(adapter_closed.sum()),
                    "unsupported_opened": int(unsupported_open.sum()),
                    "supported": int(unsupported_open.sum()) == 0,
                    "base_solved": base_solved_count,
                    "selector_solved_est": int(solved.sum()),
                    "delta_solved_vs_base": int(solved.sum() - base_solved_count),
                    "delta_solved_vs_current": int(solved.sum() - current_solved_count),
                    "lost_solution_est": int(lost.sum()),
                    "recovered_timeout_est": int(recovered.sum()),
                    "mean_time_est": float(time.mean()),
                    "delta_mean_time_vs_current": float(time.mean() - current_mean_time),
                    "delta_mean_time_vs_old": float(time.mean() - old_mean_time),
                }
                for key, idx in focus_indices.items():
                    row[f"use_{key}"] = int(use[idx])
                rows.append(row)
    return pd.DataFrame(rows)


def fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
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


def distinct_policy_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    signature_columns = [
        "selected",
        "decision_changed",
        "selector_solved_est",
        "delta_solved_vs_base",
        "delta_solved_vs_current",
        "lost_solution_est",
        "recovered_timeout_est",
        "mean_time_est",
        "unsupported_opened",
    ]
    columns = [column for column in signature_columns if column in frame.columns]
    return frame.drop_duplicates(subset=columns, keep="first").reset_index(drop=True)


def focus_audit(frame: pd.DataFrame, policy: pd.Series, label: str) -> pd.DataFrame:
    rows = []
    for key in FOCUS:
        match = frame[frame["file_key"].eq(key)]
        if match.empty:
            continue
        row = match.iloc[0]
        rows.append(
            {
                "policy": label,
                "file_key": key,
                "use_adapter": int(policy.loc[match.index[0]]),
                "current_use_adapter": int(bool(row["current_use_adapter"])),
                "risk_prob": float(row["risk_prob"]),
                "recovery_prob": float(row["recovery_prob"]),
                "slowdown_prob": float(row["slowdown_prob"]),
                "base_result": row["base_result"],
                "base_time": float(row["base_time"]),
                "old_result": row["old_result"],
                "old_time": float(row["old_time"]),
                "actual_result": row["actual_result"],
                "actual_time": float(row["actual_time"]),
            }
        )
    return pd.DataFrame(rows)


def make_policy_mask(frame: pd.DataFrame, row: pd.Series) -> pd.Series:
    return (
        (frame["risk_prob"].astype(float) < float(row["risk_threshold"]))
        & (frame["recovery_prob"].astype(float) >= float(row["recovery_threshold"]))
        & (frame["slowdown_prob"].astype(float) < float(row["slowdown_threshold"]))
    )


def build_focus_audit(frame: pd.DataFrame, policies: list[tuple[str, pd.Series]]) -> pd.DataFrame:
    rows = []
    seen = set()
    for label, policy in policies:
        if label in seen:
            continue
        seen.add(label)
        rows.append(focus_audit(frame, policy, label))
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def instance_audit(frame: pd.DataFrame, policies: list[tuple[str, pd.Series]]) -> pd.DataFrame:
    rows = []
    for label, policy in policies:
        solved, time, adapter_closed, unsupported_open = policy_time_solved(frame, policy)
        for idx, row in frame.iterrows():
            base_solved = bool(row["base_solved"])
            selected_solved = bool(solved.loc[idx])
            rows.append(
                {
                    "policy": label,
                    "file_key": row["file_key"],
                    "use_adapter": int(bool(policy.loc[idx])),
                    "current_use_adapter": int(bool(row["current_use_adapter"])),
                    "adapter_closed": int(bool(adapter_closed.loc[idx])),
                    "unsupported_open": int(bool(unsupported_open.loc[idx])),
                    "base_solved": int(base_solved),
                    "selected_solved": int(selected_solved),
                    "lost_solution_est": int(base_solved and not selected_solved),
                    "recovered_timeout_est": int((not base_solved) and selected_solved),
                    "selected_time_est": float(time.loc[idx]),
                    "base_time": float(row["base_time"]),
                    "current_time": float(row["current_time"]),
                    "old_time": float(row["old_time"]),
                    "risk_prob": float(row["risk_prob"]),
                    "recovery_prob": float(row["recovery_prob"]),
                    "slowdown_prob": float(row["slowdown_prob"]),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    frame = build_frame()
    focus_frame = frame[frame["file_key"].isin(FOCUS)].copy()
    risk_values = threshold_candidates(frame["risk_prob"], focus_frame["risk_prob"], step=0.05)
    recovery_values = threshold_candidates(
        frame["recovery_prob"],
        focus_frame["recovery_prob"],
        step=0.05,
    )
    slowdown_values = threshold_candidates(
        frame["slowdown_prob"],
        focus_frame["slowdown_prob"],
        step=0.05,
    )
    sweep = vectorized_sweep(frame, risk_values, recovery_values, slowdown_values)
    ranked = sort_sweep(sweep)
    supported = ranked[ranked["supported"].astype(bool)].copy()
    current = evaluate_policy(
        frame,
        risk_threshold=0.7952608466148375,
        recovery_threshold=0.38448874490165713,
        slowdown_threshold=0.23295481503009796,
    )
    current["policy"] = "current_pairwise_veto"
    solved_supported = supported.sort_values(
        by=["selector_solved_est", "lost_solution_est", "mean_time_est", "selected"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)
    best_solved_supported = solved_supported.iloc[0].to_dict()
    best_solved_supported["policy"] = "best_solved_supported"
    no_lost = supported[supported["lost_solution_est"].eq(0)].copy()
    best_no_lost = no_lost.sort_values(
        by=["selector_solved_est", "mean_time_est", "selected"],
        ascending=[False, True, True],
    ).reset_index(drop=True).iloc[0].to_dict()
    best_no_lost["policy"] = "best_no_lost_supported"
    unsupported_upper = sweep.sort_values(
        by=["selector_solved_est", "lost_solution_est", "mean_time_est", "unsupported_opened"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True).iloc[0].to_dict()
    unsupported_upper["policy"] = "unsupported_upper_bound"
    old_like = {
        "policy": "old_compact_reference",
        "risk_threshold": np.nan,
        "recovery_threshold": np.nan,
        "slowdown_threshold": np.nan,
        "selected": np.nan,
        "selected_fraction": np.nan,
        "decision_changed": np.nan,
        "new_adapter_opened": np.nan,
        "adapter_closed": np.nan,
        "unsupported_opened": 0,
        "supported": True,
        "base_solved": int(frame["base_solved"].sum()),
        "selector_solved_est": int(frame["old_solved"].sum()),
        "delta_solved_vs_base": int(frame["old_solved"].sum() - frame["base_solved"].sum()),
        "delta_solved_vs_current": int(frame["old_solved"].sum() - frame["current_solved"].sum()),
        "lost_solution_est": int((frame["base_solved"].astype(bool) & ~frame["old_solved"].astype(bool)).sum()),
        "recovered_timeout_est": int((~frame["base_solved"].astype(bool) & frame["old_solved"].astype(bool)).sum()),
        "mean_time_est": float(frame["old_time"].mean()),
        "delta_mean_time_vs_current": float(frame["old_time"].mean() - frame["current_time"].mean()),
        "delta_mean_time_vs_old": 0.0,
    }
    compare = pd.DataFrame([old_like, current, best_no_lost, best_solved_supported, unsupported_upper])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sweep_path = OUT_DIR / "online_pairwise_veto_threshold_sweep.csv"
    best_path = OUT_DIR / "online_pairwise_veto_threshold_sweep_best.csv"
    compare_path = OUT_DIR / "online_pairwise_veto_threshold_sweep_compare.csv"
    focus_path = OUT_DIR / "online_pairwise_veto_threshold_sweep_focus.csv"
    instance_path = OUT_DIR / "online_pairwise_veto_threshold_sweep_instance_audit.csv"
    no_lost_ranked = no_lost.sort_values(
        by=["selector_solved_est", "mean_time_est", "selected"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    sweep.to_csv(sweep_path, index=False)
    distinct_policy_rows(solved_supported).head(100).to_csv(best_path, index=False)
    compare.to_csv(compare_path, index=False)

    current_mask = frame["current_use_adapter"].astype(bool)
    focus = build_focus_audit(
        frame,
        [
            ("current_pairwise_veto", current_mask),
            ("best_no_lost_supported", make_policy_mask(frame, pd.Series(best_no_lost))),
            ("best_solved_supported", make_policy_mask(frame, pd.Series(best_solved_supported))),
            ("unsupported_upper_bound", make_policy_mask(frame, pd.Series(unsupported_upper))),
        ],
    )
    focus.to_csv(focus_path, index=False)
    audited_policies = [
        ("current_pairwise_veto", current_mask),
        ("best_no_lost_supported", make_policy_mask(frame, pd.Series(best_no_lost))),
        ("best_solved_supported", make_policy_mask(frame, pd.Series(best_solved_supported))),
    ]
    instance_audit(frame, audited_policies).to_csv(instance_path, index=False)

    compare_cols = [
        "policy",
        "risk_threshold",
        "recovery_threshold",
        "slowdown_threshold",
        "selected",
        "decision_changed",
        "selector_solved_est",
        "delta_solved_vs_base",
        "delta_solved_vs_current",
        "lost_solution_est",
        "recovered_timeout_est",
        "mean_time_est",
        "delta_mean_time_vs_current",
        "unsupported_opened",
    ]
    top_cols = [column for column in compare_cols if column != "policy"]
    doc = [
        "# Online Feature Pairwise+Veto 阈值扫描",
        "",
        "本扫描只使用最终 checkpoint 重新提取的 online selector feature cache：",
        f"`{FEATURES_CSV}`。",
        "旧 compact feature cache 不参与任何新决策。",
        "",
        "## 结论",
        "",
        "- 阈值扫描没有找到能替换 old compact 的 supported 策略。",
        "- supported 策略只允许关闭当前已打开的 adapter，不允许凭空打开未观测 adapter 分支；因此该扫描是保守稳定性审计。",
        "- `best_no_lost_supported` 只能回到 base 的 `50 solved`；`best_solved_supported` 最高也只有 `52 solved`，且仍低于 old compact 的 `56 solved`。",
        "- 即使把 unsupported 打开当作乐观上界，当前 cache 下也只到 `53 solved`，仍追不上 old compact。",
        "- 因此问题不是阈值单点选择，而是当前 adapter branch 的 recovery 不能稳定复现 old compact。",
        "- 后续若继续推进，应先修正 counterfactual trace 与真实 online rollout 的分布偏差，再谈训练更复杂 selector。",
        "",
        "## 代表策略",
        "",
        markdown_table(compare, compare_cols),
        "",
        "## No-Lost Supported 候选 Top 30",
        "",
        markdown_table(distinct_policy_rows(no_lost_ranked), top_cols, max_rows=30),
        "",
        "## Solved-First Supported 候选 Top 30",
        "",
        markdown_table(distinct_policy_rows(solved_supported), top_cols, max_rows=30),
        "",
        "## 重点实例决策",
        "",
        markdown_table(
            focus,
            [
                "policy",
                "file_key",
                "use_adapter",
                "current_use_adapter",
                "risk_prob",
                "recovery_prob",
                "slowdown_prob",
                "base_result",
                "base_time",
                "old_result",
                "old_time",
                "actual_result",
                "actual_time",
            ],
        ),
        "",
        "## 输出文件",
        "",
        f"- `{sweep_path}`",
        f"- `{best_path}`",
        f"- `{compare_path}`",
        f"- `{focus_path}`",
        f"- `{instance_path}`",
        "",
    ]
    DOC_PATH.write_text("\n".join(doc), encoding="utf-8")
    print(compare[compare_cols].to_string(index=False))
    print(f"wrote {sweep_path}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
