from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch


DEFAULT_TRACE_PATHS = [
    "data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_traces.pt",
    "data/counterfactual_trace/hard_recovery_400_train_traces.pt",
]
DEFAULT_AUDIT_FEATURES = "runs/analysis/compact_risk_full400_with_selector_features.csv"
DEFAULT_OUTPUT = "data/counterfactual_trace/boundary_focused_pairwise_trace.csv"
DEFAULT_DOC = "docs/boundary_focused_pairwise_trace.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a boundary-focused selector training frame.")
    parser.add_argument("--trace", action="append", default=[])
    parser.add_argument("--audit-features", default=DEFAULT_AUDIT_FEATURES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--doc-path", default=DEFAULT_DOC)
    parser.add_argument("--include-full400-audit", action="store_true", default=True)
    parser.add_argument("--no-full400-audit", dest="include_full400_audit", action="store_false")
    return parser.parse_args()


def file_key(path: object) -> str:
    return os.path.basename(str(path))


def is_solved(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value) in {"SATISFIABLE", "UNSATISFIABLE"}


def _numeric(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([default] * len(frame), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def add_boundary_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "file_key" not in frame.columns:
        source = frame["file"] if "file" in frame.columns else frame.get("cnf_id", frame.index)
        frame["file_key"] = source.map(file_key)
    if "counterfactual_reason" not in frame.columns:
        frame["counterfactual_reason"] = "neutral"
    if "base_solved" not in frame.columns and "base_result" in frame.columns:
        frame["base_solved"] = frame["base_result"].map(is_solved)
    if "adapter_solved" not in frame.columns and "adapter_result" in frame.columns:
        frame["adapter_solved"] = frame["adapter_result"].map(is_solved)

    base_time = _numeric(frame, "base_time", default=60.0)
    adapter_time = _numeric(frame, "adapter_time", default=60.0)
    base_solved = frame["base_solved"].astype(bool)
    adapter_solved = frame["adapter_solved"].astype(bool)
    reason = frame["counterfactual_reason"].fillna("neutral").astype(str)

    if "base_bucket" in frame.columns:
        bucket = frame["base_bucket"].fillna("")
    else:
        bucket = np.where(~base_solved, "timeout", np.where(base_time < 10.0, "easy", np.where(base_time < 30.0, "medium", "hard")))
        bucket = pd.Series(bucket, index=frame.index)
    bucket = bucket.astype(str)

    recovered_timeout = (~base_solved) & adapter_solved
    hard_speedup = (
        base_solved
        & adapter_solved
        & (base_time >= 30.0)
        & ((adapter_time <= 0.8 * base_time) | ((base_time - adapter_time) >= 10.0))
    )
    easy_slowdown = (
        base_solved
        & adapter_solved
        & ((base_time < 10.0) | bucket.str.contains("easy", case=False, regex=False))
        & ((adapter_time >= 1.05 * base_time) | ((adapter_time - base_time) >= 0.25))
    )
    lost_solution = base_solved & ~adapter_solved
    slowdown = (
        base_solved
        & adapter_solved
        & (adapter_time > base_time)
        & ((adapter_time - base_time) >= 1.0)
    )

    frame["boundary_label"] = np.nan
    frame["boundary_reason"] = "neutral"
    frame["boundary_weight"] = 0.0
    frame["boundary_pair_weight"] = 0.0

    positive = recovered_timeout | hard_speedup | reason.isin(["recovered_timeout", "hard_speedup"])
    negative = lost_solution | easy_slowdown | reason.isin(["lost_solution", "easy_slowdown"]) | slowdown

    frame.loc[positive, "boundary_label"] = 1.0
    frame.loc[positive, "boundary_reason"] = "hard_speedup"
    frame.loc[positive, "boundary_weight"] = 8.0
    frame.loc[positive, "boundary_pair_weight"] = 2.0
    frame.loc[recovered_timeout | reason.eq("recovered_timeout"), "boundary_reason"] = "hard_recovery"
    frame.loc[recovered_timeout | reason.eq("recovered_timeout"), "boundary_weight"] = 32.0
    frame.loc[recovered_timeout | reason.eq("recovered_timeout"), "boundary_pair_weight"] = 6.0

    frame.loc[negative, "boundary_label"] = 0.0
    frame.loc[negative, "boundary_reason"] = "slowdown"
    frame.loc[negative, "boundary_weight"] = 10.0
    frame.loc[negative, "boundary_pair_weight"] = 2.0
    frame.loc[lost_solution | reason.eq("lost_solution"), "boundary_reason"] = "lost_solution"
    frame.loc[lost_solution | reason.eq("lost_solution"), "boundary_weight"] = 36.0
    frame.loc[lost_solution | reason.eq("lost_solution"), "boundary_pair_weight"] = 6.0
    frame.loc[easy_slowdown | reason.eq("easy_slowdown"), "boundary_reason"] = "easy_slowdown"
    frame.loc[easy_slowdown | reason.eq("easy_slowdown"), "boundary_weight"] = 28.0
    frame.loc[easy_slowdown | reason.eq("easy_slowdown"), "boundary_pair_weight"] = 6.0

    frame["boundary_labelled"] = frame["boundary_label"].notna()
    frame["boundary_source_weight"] = np.where(frame.get("boundary_source", "") == "full400_audit", 1.5, 1.0)
    frame["boundary_weight"] = frame["boundary_weight"].astype(float) * frame["boundary_source_weight"].astype(float)
    frame["boundary_pair_weight"] = frame["boundary_pair_weight"].astype(float) * frame["boundary_source_weight"].astype(float)
    return frame


def load_trace_frame(path: str, trace_id: int) -> pd.DataFrame:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "outcome_frame" not in payload:
        raise ValueError(f"{path} must contain an outcome_frame")
    frame = payload["outcome_frame"]
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    frame = frame.copy()
    frame["trace_path"] = path
    frame["trace_id"] = trace_id
    frame["boundary_source"] = "counterfactual_trace"
    if "file_key" not in frame.columns:
        frame["file_key"] = frame["file"].map(file_key)
    return frame


def load_audit_boundary_frame(path: str) -> pd.DataFrame:
    audit = pd.read_csv(path)
    frame = audit.copy()
    frame["boundary_source"] = "full400_audit"
    frame["trace_path"] = path
    frame["trace_id"] = -1
    frame["file"] = frame["file_key"].map(lambda name: f"data/test/3sat/400/{name}")
    frame["sample_id"] = 0
    frame["base_result"] = frame["base_result"]
    frame["adapter_result"] = frame["compact_result"]
    frame["adapter_solved"] = frame["compact_solved"].astype(bool)
    frame["adapter_time"] = frame["compact_time"].astype(float)
    if "warmup_solved" not in frame.columns:
        warmup_cols = [column for column in ["warmup_c500_solved", "warmup_c1000_solved", "warmup_c2000_solved"] if column in frame.columns]
        frame["warmup_solved"] = False
        for column in warmup_cols:
            frame["warmup_solved"] = frame["warmup_solved"] | frame[column].astype(bool)
    if "counterfactual_reason" not in frame.columns:
        frame["counterfactual_reason"] = frame["outcome"].map(
            {
                "recovered_timeout": "recovered_timeout",
                "lost_solution": "lost_solution",
                "slower_both_solved": "slowdown",
                "faster_both_solved": "hard_speedup",
            }
        ).fillna("neutral")
    return frame


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame[columns].iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def write_doc(path: str, frame: pd.DataFrame, output: str) -> None:
    labelled = frame[frame["boundary_labelled"]].copy()
    counts = (
        labelled.groupby(["boundary_source", "size", "boundary_reason"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["boundary_source", "size", "boundary_reason"])
    )
    focus = labelled[labelled["file_key"].isin(["3sat_163.cnf", "3sat_25.cnf", "3sat_88.cnf", "3sat_140.cnf", "3sat_82.cnf"])].copy()
    focus_cols = [
        "boundary_source",
        "size",
        "file_key",
        "boundary_label",
        "boundary_reason",
        "base_time",
        "adapter_time",
        "boundary_weight",
        "boundary_pair_weight",
    ]
    doc = [
        "# Boundary-Focused Pairwise Trace",
        "",
        "该训练帧用于修复 recovery selector 的排序边界：让 hard recovery / hard speedup 排在 easy slowdown / lost solution 前面。",
        "这里不重新跑 solver，而是合并已有 counterfactual trace 和 full400 审计中的边界样本。",
        "",
        "注意：`full400_audit` 行用于诊断和排序约束，不应直接当作最终 held-out 评估结果。",
        "",
        "## 标签计数",
        "",
        markdown_table(counts, ["boundary_source", "size", "boundary_reason", "count"]),
        "",
        "## 重点样本",
        "",
        markdown_table(focus, focus_cols),
        "",
        "## 输出文件",
        "",
        f"- `{output}`",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    trace_paths = args.trace or DEFAULT_TRACE_PATHS
    frames = [load_trace_frame(path, idx) for idx, path in enumerate(trace_paths)]
    if args.include_full400_audit:
        frames.append(load_audit_boundary_frame(args.audit_features))
    merged = pd.concat(frames, ignore_index=True, sort=False)
    merged = add_boundary_labels(merged)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output, index=False)
    write_doc(args.doc_path, merged, str(output))
    labelled = merged[merged["boundary_labelled"]]
    print(f"wrote {output}")
    print(f"labelled rows: {len(labelled)} / {len(merged)}")
    print(labelled["boundary_reason"].value_counts().to_string())
    print(f"wrote {args.doc_path}")


if __name__ == "__main__":
    main()
