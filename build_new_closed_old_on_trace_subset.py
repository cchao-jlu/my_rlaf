from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd


AUDIT_CSV = Path("runs/analysis/online_consistent_boundary400_decision_audit.csv")
SOURCE_DIR = Path("data/test/3sat/400")
OUTPUT_DIR = Path("data/new_closed_old_on_boundary/3sat/400")
MANIFEST_CSV = Path("data/new_closed_old_on_boundary/manifest.csv")
DOC_PATH = Path("docs/new_closed_old_on_boundary_subset.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local new_closed_old_on boundary CNF subset.")
    parser.add_argument("--audit-csv", default=str(AUDIT_CSV))
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--manifest-csv", default=str(MANIFEST_CSV))
    parser.add_argument("--doc-path", default=str(DOC_PATH))
    return parser.parse_args()


def select_new_closed_old_on(frame: pd.DataFrame) -> pd.DataFrame:
    if "decision_change" not in frame.columns:
        raise ValueError("frame must contain decision_change")
    selected = frame[frame["decision_change"].eq("new_closed_old_on")].copy()
    return selected.sort_values("file_key").reset_index(drop=True)


def add_local_boundary_labels(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    delta_vs_old = pd.to_numeric(result["delta_time_vs_old"], errors="coerce")
    base_time = pd.to_numeric(result["base_time"], errors="coerce")
    old_time = pd.to_numeric(result["old_time"], errors="coerce")
    new_time = pd.to_numeric(result["new_time"], errors="coerce")
    outcome_vs_old = result["outcome_vs_old"].fillna("").astype(str)
    base_solved = result["base_solved"].astype(bool)
    old_solved = result["old_solved"].astype(bool)
    new_solved = result["new_solved"].astype(bool)

    reopen = (
        old_solved
        & new_solved
        & (outcome_vs_old.eq("slower_both_solved"))
        & (delta_vs_old >= 1.0)
        & ((new_time >= old_time * 1.10) | ((new_time - old_time) >= 5.0))
    )
    reopen = reopen | (
        old_solved
        & ~new_solved
        & base_solved
    )
    keep_closed = (
        old_solved
        & new_solved
        & outcome_vs_old.eq("faster_both_solved")
        & (delta_vs_old <= -0.5)
    )
    keep_closed = keep_closed | (
        old_solved
        & new_solved
        & (new_time <= base_time + 1.0)
        & (old_time >= new_time + 1.0)
    )

    result["local_closed_old_label"] = pd.NA
    result["local_closed_old_reason"] = "neutral"
    result["local_closed_old_weight"] = 0.0
    result.loc[reopen, "local_closed_old_label"] = 1
    result.loc[reopen, "local_closed_old_reason"] = "reopen_old_adapter"
    result.loc[reopen, "local_closed_old_weight"] = 8.0
    result.loc[keep_closed, "local_closed_old_label"] = 0
    result.loc[keep_closed, "local_closed_old_reason"] = "keep_closed"
    result.loc[keep_closed, "local_closed_old_weight"] = 8.0
    result["local_closed_old_labelled"] = result["local_closed_old_label"].notna()
    result["local_old_gain_vs_new"] = new_time - old_time
    result["local_new_gain_vs_base"] = base_time - new_time
    result["local_old_gain_vs_base"] = base_time - old_time
    return result


def copy_subset_files(subset: pd.DataFrame, source_dir: str, output_dir: str) -> None:
    source = Path(source_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for existing in out.glob("*.cnf"):
        existing.unlink()
    for file_key in subset["file_key"]:
        src = source / str(file_key)
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, out / src.name)


def _fmt(value: object) -> str:
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
        lines.append("| " + " | ".join(_fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_doc(path: str, subset: pd.DataFrame, output_dir: str, manifest_csv: str) -> None:
    reason_counts = (
        subset["local_closed_old_reason"]
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="count")
    )
    columns = [
        "file_key",
        "difficulty_bucket",
        "base_time",
        "old_time",
        "new_time",
        "delta_time_vs_old",
        "outcome_vs_old",
        "new_risk_prob",
        "new_recovery_prob",
        "new_slowdown_prob",
        "local_closed_old_label",
        "local_closed_old_reason",
    ]
    doc = [
        "# New-Closed-Old-On 局部边界子集",
        "",
        "该子集只包含正式 full400 审计中的 `new_closed_old_on` 样本：旧 compact 曾开启 adapter，而当前 online-consistent boundary400 selector 关闭 adapter。",
        "目标是生成局部 counterfactual trace，区分 `3sat_46/196` 这类旧 adapter 有效样本和 `3sat_82/188` 这类保持关闭更好的样本。",
        "",
        f"- 输出 CNF 目录：`{output_dir}`",
        f"- manifest：`{manifest_csv}`",
        f"- 子集大小：`{len(subset)}`",
        "",
        "## 局部标签计数",
        "",
        markdown_table(reason_counts, ["reason", "count"]),
        "",
        "## 样本清单",
        "",
        markdown_table(subset, [column for column in columns if column in subset.columns]),
        "",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    audit = pd.read_csv(args.audit_csv)
    subset = add_local_boundary_labels(select_new_closed_old_on(audit))
    copy_subset_files(subset, args.source_dir, args.output_dir)
    manifest = Path(args.manifest_csv)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(manifest, index=False)
    write_doc(args.doc_path, subset, args.output_dir, args.manifest_csv)
    print(f"wrote {len(subset)} CNFs to {args.output_dir}")
    print(subset["local_closed_old_reason"].value_counts().to_string())
    print(f"wrote {manifest}")
    print(f"wrote {args.doc_path}")


if __name__ == "__main__":
    main()
