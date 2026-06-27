from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


MANIFEST_CSV = Path("data/new_closed_old_on_boundary/manifest.csv")
TRACE_CSV = Path("data/counterfactual_trace/new_closed_old_on_boundary400_outcomes.csv")
SUMMARY_CSV = Path("runs/analysis/new_closed_old_on_boundary_trace_summary.csv")
FOCUS_CSV = Path("runs/analysis/new_closed_old_on_boundary_trace_focus.csv")
FEATURE_CSV = Path("runs/analysis/new_closed_old_on_boundary_trace_feature_compare.csv")
DOC_PATH = Path("docs/new_closed_old_on_boundary_trace_results.md")

FOCUS_KEYS = [
    "3sat_46.cnf",
    "3sat_196.cnf",
    "3sat_188.cnf",
    "3sat_82.cnf",
    "3sat_93.cnf",
]

FEATURE_COLUMNS = [
    "warmup_c2000_base_rho_mean",
    "warmup_c2000_base_rho_std",
    "warmup_c2000_base_rho_range",
    "warmup_c2000_delta_abs_mean",
    "warmup_c2000_event_entropy_norm",
    "warmup_c2000_event_top10_mass",
    "warmup_c2000_rho_event_corr",
    "warmup_c2000_rho_event_top10_overlap",
    "warmup_c2000_event_conf_learnt_log_max",
    "warmup_c500_minus_warmup_c250_decisions",
    "warmup_c750_minus_warmup_c500_decisions",
    "warmup_c1000_minus_warmup_c750_decisions",
    "warmup_c1000_minus_warmup_c500_decisions",
    "warmup_c1500_minus_warmup_c1000_decisions",
    "warmup_c2000_minus_warmup_c1500_decisions",
    "warmup_c2000_minus_warmup_c1000_decisions",
    "warmup_c750_minus_warmup_c500_event_top10_mass",
    "warmup_c1000_minus_warmup_c750_event_top10_mass",
    "warmup_c1000_minus_warmup_c500_event_top10_mass",
    "warmup_c1500_minus_warmup_c1000_event_top10_mass",
    "warmup_c2000_minus_warmup_c1500_event_top10_mass",
    "warmup_c2000_minus_warmup_c1000_event_top10_mass",
    "warmup_c750_minus_warmup_c500_rho_event_corr",
    "warmup_c1000_minus_warmup_c750_rho_event_corr",
    "warmup_c1000_minus_warmup_c500_rho_event_corr",
    "warmup_c1500_minus_warmup_c1000_rho_event_corr",
    "warmup_c2000_minus_warmup_c1500_rho_event_corr",
    "warmup_c2000_minus_warmup_c1000_rho_event_corr",
]

FOCUS_COLUMNS = [
    "file_key",
    "counterfactual_class",
    "counterfactual_reason",
    "base_pipeline_time",
    "adapter_pipeline_time",
    "adapter_minus_base_time",
    "manifest_label",
    "manifest_reason",
    "trace_reopen_label",
    "trace_reopen_reason",
    "feature_profile",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize local new_closed_old_on counterfactual trace evidence."
    )
    parser.add_argument("--manifest-csv", default=str(MANIFEST_CSV))
    parser.add_argument("--trace-csv", default=str(TRACE_CSV))
    parser.add_argument("--summary-csv", default=str(SUMMARY_CSV))
    parser.add_argument("--focus-csv", default=str(FOCUS_CSV))
    parser.add_argument("--feature-csv", default=str(FEATURE_CSV))
    parser.add_argument("--doc-path", default=str(DOC_PATH))
    return parser.parse_args()


def _file_key(path: object) -> str:
    return Path(str(path)).name


def merge_manifest_and_trace(manifest: pd.DataFrame, trace: pd.DataFrame) -> pd.DataFrame:
    manifest = manifest.copy()
    trace = trace.copy()
    if "file_key" not in trace.columns:
        if "file" not in trace.columns:
            raise ValueError("trace must contain either file_key or file")
        trace["file_key"] = trace["file"].map(_file_key)
    if "file_key" not in manifest.columns:
        raise ValueError("manifest must contain file_key")

    manifest_keep = manifest.rename(
        columns={
            "local_closed_old_label": "manifest_label",
            "local_closed_old_reason": "manifest_reason",
            "local_closed_old_weight": "manifest_weight",
        }
    )
    merged = manifest_keep.merge(trace, on="file_key", how="inner", suffixes=("_audit", ""))
    if len(merged) != len(trace):
        missing = sorted(set(trace["file_key"]) - set(merged["file_key"]))
        raise ValueError("manifest is missing trace rows: " + ", ".join(missing[:10]))
    return merged.sort_values("file_key").reset_index(drop=True)


def local_reopen_labels(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    klass = result["counterfactual_class"].fillna("neutral").astype(str)
    result["trace_reopen_label"] = pd.NA
    result["trace_reopen_reason"] = "neutral"
    result["trace_reopen_weight"] = 0.0

    positive = klass.eq("positive")
    negative = klass.eq("negative")
    if "counterfactual_weight" in result.columns:
        weight = pd.to_numeric(result["counterfactual_weight"], errors="coerce")
    else:
        weight = pd.Series(index=result.index, dtype="float64")
    result.loc[positive, "trace_reopen_label"] = 1
    result.loc[positive, "trace_reopen_reason"] = "reopen_by_current_trace"
    result.loc[positive, "trace_reopen_weight"] = weight.loc[positive].fillna(4.0)
    result.loc[negative, "trace_reopen_label"] = 0
    result.loc[negative, "trace_reopen_reason"] = "keep_closed_by_current_trace"
    result.loc[negative, "trace_reopen_weight"] = weight.loc[negative].fillna(8.0)

    manifest_label = pd.to_numeric(result.get("manifest_label", pd.Series(index=result.index)), errors="coerce")
    trace_label = pd.to_numeric(result["trace_reopen_label"], errors="coerce")
    result["manifest_trace_disagreement"] = (
        manifest_label.notna() & trace_label.notna() & (manifest_label != trace_label)
    )
    result["trace_adapter_gain"] = -pd.to_numeric(result["adapter_minus_base_time"], errors="coerce")
    return result


def build_summary(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame["counterfactual_class"].fillna("neutral").value_counts()
    reason_counts = frame["counterfactual_reason"].fillna("neutral").value_counts()
    return pd.DataFrame(
        [
            {
                "n": int(len(frame)),
                "positive": int(counts.get("positive", 0)),
                "negative": int(counts.get("negative", 0)),
                "neutral": int(counts.get("neutral", 0)),
                "recovered_timeout": int(reason_counts.get("recovered_timeout", 0)),
                "hard_speedup": int(reason_counts.get("hard_speedup", 0)),
                "slowdown": int(reason_counts.get("slowdown", 0)),
                "manifest_trace_disagreement": int(frame.get("manifest_trace_disagreement", pd.Series(dtype=bool)).sum()),
                "mean_adapter_minus_base": float(
                    pd.to_numeric(frame["adapter_minus_base_time"], errors="coerce").mean()
                ),
            }
        ]
    )


def _feature_profile(row: pd.Series) -> str:
    parts = []
    names = [
        ("rho_mean", "warmup_c2000_base_rho_mean"),
        ("delta", "warmup_c2000_delta_abs_mean"),
        ("entropy", "warmup_c2000_event_entropy_norm"),
        ("top10", "warmup_c2000_event_top10_mass"),
        ("corr", "warmup_c2000_rho_event_corr"),
        ("overlap", "warmup_c2000_rho_event_top10_overlap"),
        ("d_top10", "warmup_c2000_minus_warmup_c1000_event_top10_mass"),
        ("d_corr", "warmup_c2000_minus_warmup_c1000_rho_event_corr"),
    ]
    for label, column in names:
        if column not in row or pd.isna(row[column]):
            continue
        parts.append(f"{label}={float(row[column]):.4f}")
    return "; ".join(parts)


def build_focus_frame(frame: pd.DataFrame, focus_keys: list[str] | None = None) -> pd.DataFrame:
    keys = focus_keys or FOCUS_KEYS
    focus = frame[frame["file_key"].isin(keys)].copy()
    order = {key: idx for idx, key in enumerate(keys)}
    focus["_order"] = focus["file_key"].map(order).fillna(len(order)).astype(int)
    focus["feature_profile"] = focus.apply(_feature_profile, axis=1)
    columns = [column for column in FOCUS_COLUMNS if column in focus.columns]
    return focus.sort_values("_order")[columns].reset_index(drop=True)


def feature_compare(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    labelled = frame[frame["counterfactual_class"].isin(["positive", "negative"])].copy()
    for feature in FEATURE_COLUMNS:
        if feature not in labelled.columns:
            continue
        values = pd.to_numeric(labelled[feature], errors="coerce")
        if values.isna().all():
            continue
        pos = labelled[labelled["counterfactual_class"].eq("positive")]
        neg = labelled[labelled["counterfactual_class"].eq("negative")]
        pos_values = pd.to_numeric(pos[feature], errors="coerce")
        neg_values = pd.to_numeric(neg[feature], errors="coerce")
        rows.append(
            {
                "feature": feature,
                "positive_mean": float(pos_values.mean()),
                "negative_mean": float(neg_values.mean()),
                "pos_minus_neg": float(pos_values.mean() - neg_values.mean()),
                "positive_min": float(pos_values.min()),
                "positive_max": float(pos_values.max()),
                "negative_min": float(neg_values.min()),
                "negative_max": float(neg_values.max()),
            }
        )
    return pd.DataFrame(rows).sort_values("pos_minus_neg", key=lambda s: s.abs(), ascending=False)


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if pd.isna(value):
        return ""
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_空_"
    table = frame.copy()
    if columns is not None:
        table = table[[column for column in columns if column in table.columns]]
    if max_rows is not None:
        table = table.head(max_rows)
    lines = [
        "| " + " | ".join(str(column) for column in table.columns) + " |",
        "| " + " | ".join("---" for _ in table.columns) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(_fmt(row[column]) for column in table.columns) + " |")
    return "\n".join(lines)


def write_doc(path: str, summary: pd.DataFrame, focus: pd.DataFrame, features: pd.DataFrame) -> None:
    doc = [
        "# New-Closed-Old-On 局部 Trace 审计",
        "",
        "本报告只分析 `new_closed_old_on` 局部边界：旧 compact 曾开启 adapter，当前 online-consistent selector 关闭 adapter。",
        "这里使用当前 boundary400 checkpoint 的强制 adapter counterfactual trace，避免继续依赖旧 feature cache 或全局阈值扫描。",
        "",
        "## 结论",
        "",
        "- 当前局部 trace 中，`3sat_46`、`3sat_196` 是 hard_speedup 正例，`3sat_188` 是 recovered_timeout 正例。",
        "- `3sat_82`、`3sat_93` 是 slowdown 负例，应继续关闭 adapter。",
        "- `3sat_188` 与早期 manifest 的 `keep_closed` 标签冲突，后续局部门控应以当前 trace 为准。",
        "- 样本量只有 5 个强标签，适合做局部 reopen override 的诊断，不适合包装成新的全局 selector 结论。",
        "",
        "## 标签概览",
        "",
        markdown_table(summary),
        "",
        "## 焦点样本",
        "",
        markdown_table(focus),
        "",
        "## 特征均值差异",
        "",
        "下表只比较 positive/negative 强标签样本。由于样本极少，该表用于定位下一轮 trace 增强方向，而不是统计显著性证明。",
        "",
        markdown_table(features, max_rows=15),
        "",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def run(
    *,
    manifest_csv: str,
    trace_csv: str,
    summary_csv: str,
    focus_csv: str,
    feature_csv: str,
    doc_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(manifest_csv)
    trace = pd.read_csv(trace_csv)
    frame = local_reopen_labels(merge_manifest_and_trace(manifest, trace))
    summary = build_summary(frame)
    focus = build_focus_frame(frame)
    features = feature_compare(frame)

    Path(summary_csv).parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_csv, index=False)
    focus.to_csv(focus_csv, index=False)
    features.to_csv(feature_csv, index=False)
    write_doc(doc_path, summary, focus, features)
    return summary, focus, features


def main() -> None:
    args = parse_args()
    summary, focus, features = run(
        manifest_csv=args.manifest_csv,
        trace_csv=args.trace_csv,
        summary_csv=args.summary_csv,
        focus_csv=args.focus_csv,
        feature_csv=args.feature_csv,
        doc_path=args.doc_path,
    )
    print(summary.to_string(index=False))
    print(f"wrote {args.summary_csv}")
    print(f"wrote {args.focus_csv}")
    print(f"wrote {args.feature_csv}")
    print(f"wrote {args.doc_path}")
    if not focus.empty:
        print(focus[["file_key", "counterfactual_class", "counterfactual_reason", "trace_reopen_reason"]].to_string(index=False))
    if not features.empty:
        print(features.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
