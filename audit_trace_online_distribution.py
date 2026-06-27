from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_TRAIN_TRACES = [
    "data/counterfactual_trace/boundary_focused_pairwise_trace.csv",
    "data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_outcomes.csv",
    "data/counterfactual_trace/hard_recovery_400_train_outcomes.csv",
]
DEFAULT_ONLINE_FEATURES = "runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv"
DEFAULT_INSTANCE_AUDIT = "runs/analysis/online_pairwise_veto_threshold_sweep_instance_audit.csv"
DEFAULT_CHECKPOINT_CONFIG = (
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto/config.yaml"
)
DEFAULT_OUTPUT_PREFIX = "runs/analysis/trace_online_distribution_audit"
DEFAULT_DOC = "docs/trace_online_distribution_audit.md"
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit train-trace vs online selector feature distribution drift.")
    parser.add_argument("--train-trace", action="append", default=None)
    parser.add_argument("--online-features", default=DEFAULT_ONLINE_FEATURES)
    parser.add_argument("--instance-audit", default=DEFAULT_INSTANCE_AUDIT)
    parser.add_argument("--checkpoint-config", default=DEFAULT_CHECKPOINT_CONFIG)
    parser.add_argument("--output-prefix", default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument("--doc-path", default=DEFAULT_DOC)
    return parser.parse_args()


def _list_from_yaml_block(path: Path, key: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    indent = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == f"{key}:":
            start = idx + 1
            indent = len(line) - len(line.lstrip())
            break
    if start is None:
        return []
    values = []
    for line in lines[start:]:
        if not line.strip():
            continue
        current_indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if current_indent <= indent and not stripped.startswith("- "):
            break
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("'\""))
    return values


def selector_features_from_config(path: str | Path) -> list[str]:
    config_path = Path(path)
    names = []
    for key in [
        "risk_selector_feature_names",
        "recovery_selector_feature_names",
        "slowdown_selector_feature_names",
    ]:
        names.extend(_list_from_yaml_block(config_path, key))
    return list(dict.fromkeys(names))


def file_key(value: object) -> str:
    return Path(str(value)).name


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def load_train_traces(paths: Iterable[str | Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path).copy()
        frame["trace_source"] = str(path)
        if "file_key" not in frame.columns and "file" in frame.columns:
            frame["file_key"] = frame["file"].map(file_key)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def load_online_frame(features_path: str | Path, instance_audit_path: str | Path) -> pd.DataFrame:
    features = pd.read_csv(features_path).copy()
    if "file_key" not in features.columns:
        files = sorted(Path("data/test/3sat/400").glob("*.cnf"))
        features["file_key"] = features["cnf_id"].map(lambda idx: files[int(idx)].name)
    audit = pd.read_csv(instance_audit_path).copy()
    if "policy" in audit.columns:
        audit = audit[audit["policy"].eq("current_pairwise_veto")].copy()
    return features.merge(audit, on="file_key", how="left", suffixes=("", "_audit"))


def _numeric_pair(train: pd.DataFrame, online: pd.DataFrame, feature: str) -> tuple[pd.Series, pd.Series]:
    train_values = pd.to_numeric(train[feature], errors="coerce").dropna().astype(float)
    online_values = pd.to_numeric(online[feature], errors="coerce").dropna().astype(float)
    return train_values, online_values


def feature_distribution_summary(train: pd.DataFrame, online: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for feature in features:
        if feature not in train.columns or feature not in online.columns:
            continue
        train_values, online_values = _numeric_pair(train, online, feature)
        if train_values.empty or online_values.empty:
            continue
        train_mean = float(train_values.mean())
        train_std = float(train_values.std(ddof=0))
        online_mean = float(online_values.mean())
        p05 = float(train_values.quantile(0.05))
        p50 = float(train_values.quantile(0.50))
        p95 = float(train_values.quantile(0.95))
        outside = (online_values < p05) | (online_values > p95)
        rows.append(
            {
                "feature": feature,
                "train_n": int(train_values.shape[0]),
                "online_n": int(online_values.shape[0]),
                "train_mean": train_mean,
                "online_mean": online_mean,
                "mean_shift": online_mean - train_mean,
                "mean_shift_z": 0.0 if train_std <= 1.0e-12 else (online_mean - train_mean) / train_std,
                "train_p05": p05,
                "train_p50": p50,
                "train_p95": p95,
                "online_min": float(online_values.min()),
                "online_max": float(online_values.max()),
                "online_outside_p05_p95": int(outside.sum()),
                "online_outside_fraction": float(outside.mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["online_outside_fraction", "mean_shift_z"],
        key=lambda values: values.abs() if values.name == "mean_shift_z" else values,
        ascending=[False, False],
    ).reset_index(drop=True)


def policy_outcome_label(base_solved: object, selected_solved: object) -> str:
    base = bool(base_solved)
    selected = bool(selected_solved)
    if base and not selected:
        return "lost_solution"
    if not base and selected:
        return "recovered_timeout"
    if base and selected:
        return "kept_solved"
    return "kept_timeout"


def instance_feature_audit(train: pd.DataFrame, online: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    stats = {}
    for feature in features:
        if feature not in train.columns or feature not in online.columns:
            continue
        train_values = pd.to_numeric(train[feature], errors="coerce").dropna().astype(float)
        if train_values.empty:
            continue
        stats[feature] = (
            float(train_values.mean()),
            float(train_values.std(ddof=0)),
            float(train_values.quantile(0.05)),
            float(train_values.quantile(0.95)),
        )
    rows = []
    for _, row in online.iterrows():
        z_scores = {}
        outside_count = 0
        for feature, (mean, std, p05, p95) in stats.items():
            value = pd.to_numeric(pd.Series([row.get(feature)]), errors="coerce").iloc[0]
            if pd.isna(value):
                continue
            value = float(value)
            z_scores[feature] = 0.0 if std <= 1.0e-12 else abs((value - mean) / std)
            outside_count += int(value < p05 or value > p95)
        if z_scores:
            max_feature = max(z_scores, key=z_scores.get)
            max_abs_z = float(z_scores[max_feature])
        else:
            max_feature = ""
            max_abs_z = 0.0
        base_solved = bool(row.get("base_solved", False))
        selected_solved = bool(row.get("selected_solved", False))
        rows.append(
            {
                "file_key": row.get("file_key", ""),
                "outcome_group": policy_outcome_label(base_solved, selected_solved),
                "use_adapter": int(row.get("use_adapter", 0)) if not pd.isna(row.get("use_adapter", 0)) else 0,
                "base_solved": int(base_solved),
                "selected_solved": int(selected_solved),
                "risk_prob": float(row.get("risk_prob", np.nan)),
                "recovery_prob": float(row.get("recovery_prob", np.nan)),
                "slowdown_prob": float(row.get("slowdown_prob", np.nan)),
                "max_abs_train_z": max_abs_z,
                "max_abs_feature": max_feature,
                "outside_p05_p95_features": int(outside_count),
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["outcome_group", "max_abs_train_z"],
        ascending=[True, False],
    ).reset_index(drop=True)


def group_summary(instance_audit_frame: pd.DataFrame) -> pd.DataFrame:
    if instance_audit_frame.empty:
        return pd.DataFrame()
    return (
        instance_audit_frame.groupby("outcome_group", sort=False)
        .agg(
            n=("file_key", "count"),
            use_adapter=("use_adapter", "sum"),
            mean_max_abs_train_z=("max_abs_train_z", "mean"),
            median_max_abs_train_z=("max_abs_train_z", "median"),
            mean_outside_features=("outside_p05_p95_features", "mean"),
            mean_risk_prob=("risk_prob", "mean"),
            mean_recovery_prob=("recovery_prob", "mean"),
            mean_slowdown_prob=("slowdown_prob", "mean"),
        )
        .reset_index()
    )


def markdown_table(frame: pd.DataFrame, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_空_"
    table = frame.head(max_rows).copy() if max_rows is not None else frame.copy()
    columns = [str(column) for column in table.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in table.iterrows():
        values = []
        for column in table.columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    train_paths = args.train_trace or DEFAULT_TRAIN_TRACES
    features = selector_features_from_config(args.checkpoint_config)
    train = load_train_traces(train_paths)
    online = load_online_frame(args.online_features, args.instance_audit)
    available_features = [feature for feature in features if feature in train.columns and feature in online.columns]
    distribution = feature_distribution_summary(train, online, available_features)
    instance = instance_feature_audit(train, online, available_features)
    grouped = group_summary(instance)

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    distribution_path = prefix.with_name(prefix.name + "_feature_summary.csv")
    instance_path = prefix.with_name(prefix.name + "_instance_audit.csv")
    group_path = prefix.with_name(prefix.name + "_group_summary.csv")
    distribution.to_csv(distribution_path, index=False)
    instance.to_csv(instance_path, index=False)
    grouped.to_csv(group_path, index=False)

    high_drift = distribution.head(12)[
        [
            "feature",
            "train_mean",
            "online_mean",
            "mean_shift_z",
            "train_p05",
            "train_p95",
            "online_min",
            "online_max",
            "online_outside_fraction",
        ]
    ]
    focus = instance[
        instance["file_key"].isin(["3sat_89.cnf", "3sat_163.cnf", "3sat_122.cnf", "3sat_88.cnf", "3sat_25.cnf"])
    ].copy()
    doc = [
        "# Trace / Online Selector Feature 分布审计",
        "",
        "本报告只使用最终 checkpoint 在线提取的 selector feature cache；旧 compact cache 不参与决策。",
        "目的不是继续增加 selector 复杂度，而是检查 counterfactual trace 与真实 online rollout evidence 是否存在分布偏差。",
        "",
        "## 输入",
        "",
        f"- online feature cache：`{args.online_features}`",
        f"- instance audit：`{args.instance_audit}`",
        "- training traces：",
        *[f"  - `{path}`" for path in train_paths],
        f"- selector feature 数：`{len(available_features)}`",
        "",
        "## Outcome 分组",
        "",
        markdown_table(grouped),
        "",
        "## 漂移最大的特征",
        "",
        markdown_table(high_drift),
        "",
        "## 重点实例",
        "",
        markdown_table(focus),
        "",
        "## 结论",
        "",
        "- 如果 `online_outside_fraction` 高，说明 online rollout evidence 已经明显偏离训练 trace；这种情况下继续调阈值意义有限。",
        "- 如果 lost/recovered 实例的 `max_abs_train_z` 较高，说明边界样本处于训练分布尾部，需要改 trace 覆盖或 rollout 采样，而不是堆 selector 容量。",
        "- 下一步应优先补在线一致的 counterfactual trace：使用与正式评估相同 checkpoint、相同 multi-point feature、相同 selector feature override 路径，并增加 full400 边界样本。",
        "",
        "## 输出文件",
        "",
        f"- `{distribution_path}`",
        f"- `{instance_path}`",
        f"- `{group_path}`",
        "",
    ]
    doc_path = Path(args.doc_path)
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(doc), encoding="utf-8")
    print(grouped.to_string(index=False))
    print(f"wrote {doc_path}")


if __name__ == "__main__":
    main()
