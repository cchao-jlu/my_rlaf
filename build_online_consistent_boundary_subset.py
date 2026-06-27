from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


FEATURES_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv")
AUDIT_CSV = Path("runs/analysis/online_pairwise_veto_threshold_sweep_instance_audit.csv")
OLD_COMPARISON_CSV = Path("runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_vs_old_compact.csv")
SOURCE_DIR = Path("data/test/3sat/400")
OUTPUT_DIR = Path("data/online_consistent_boundary/3sat/400")
MANIFEST_CSV = Path("data/online_consistent_boundary/manifest.csv")
DOC_PATH = Path("docs/online_consistent_boundary_subset.md")

RISK_THRESHOLD = 0.7952608466148375
RECOVERY_THRESHOLD = 0.38448874490165713
SLOWDOWN_THRESHOLD = 0.23295481503009796

FOCUS_KEYS = [
    "3sat_89.cnf",
    "3sat_163.cnf",
    "3sat_122.cnf",
    "3sat_88.cnf",
    "3sat_25.cnf",
    "3sat_46.cnf",
    "3sat_82.cnf",
    "3sat_140.cnf",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an online-consistent full400 boundary CNF subset.")
    parser.add_argument("--features-csv", default=str(FEATURES_CSV))
    parser.add_argument("--audit-csv", default=str(AUDIT_CSV))
    parser.add_argument("--old-comparison-csv", default=str(OLD_COMPARISON_CSV))
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--manifest-csv", default=str(MANIFEST_CSV))
    parser.add_argument("--doc-path", default=str(DOC_PATH))
    parser.add_argument("--max-size", type=int, default=64)
    parser.add_argument("--near-threshold-count", type=int, default=24)
    parser.add_argument("--slowdown-count", type=int, default=24)
    parser.add_argument("--timeout-background-count", type=int, default=8)
    return parser.parse_args()


def _file_key(value: object) -> str:
    return Path(str(value)).name


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].astype(str).str.lower().isin(["1", "true", "yes"])


def _append_tags(tags: dict[str, list[str]], keys: list[str] | pd.Series, tag: str) -> None:
    for key in keys:
        if pd.isna(key):
            continue
        name = str(key)
        if tag not in tags.setdefault(name, []):
            tags[name].append(tag)


def _read_online_frame(features_csv: str, audit_csv: str, source_dir: str) -> pd.DataFrame:
    audit = pd.read_csv(audit_csv)
    if "policy" in audit.columns:
        audit = audit[audit["policy"] == "current_pairwise_veto"].copy()
    features = pd.read_csv(features_csv).copy()
    if "file_key" not in features.columns:
        files = sorted(Path(source_dir).glob("*.cnf"))
        features["file_key"] = features["cnf_id"].map(lambda idx: files[int(idx)].name)
    drop = [
        column
        for column in ["risk_prob", "recovery_prob", "slowdown_prob", "selector_use_adapter"]
        if column in features.columns
    ]
    return audit.merge(features.drop(columns=drop), on="file_key", how="left")


def _merge_old_comparison(frame: pd.DataFrame, old_comparison_csv: str) -> pd.DataFrame:
    path = Path(old_comparison_csv)
    if not path.exists():
        frame["outcome_vs_old"] = "unknown"
        frame["delta_time_vs_old"] = np.nan
        return frame
    old = pd.read_csv(path)
    keep = [
        column
        for column in [
            "file_key",
            "outcome_vs_old",
            "delta_time_vs_old",
            "old_solved",
            "old_time",
            "pairwise_solved",
            "pairwise_time",
        ]
        if column in old.columns
    ]
    return frame.merge(old[keep], on="file_key", how="left")


def select_boundary_subset(
    frame: pd.DataFrame,
    *,
    max_size: int = 64,
    near_threshold_count: int = 24,
    slowdown_count: int = 24,
    timeout_background_count: int = 8,
    focus_keys: list[str] | None = None,
) -> pd.DataFrame:
    frame = frame.copy()
    if "file_key" not in frame.columns:
        raise ValueError("frame must contain file_key")
    focus_keys = focus_keys or FOCUS_KEYS
    tags: dict[str, list[str]] = {}

    _append_tags(tags, [key for key in focus_keys if key in set(frame["file_key"])], "focus")
    _append_tags(tags, frame.loc[_bool_series(frame, "recovered_timeout_est"), "file_key"], "current_recovered")
    _append_tags(tags, frame.loc[_bool_series(frame, "lost_solution_est"), "file_key"], "current_lost")

    base_solved = _bool_series(frame, "base_solved")
    selected_solved = _bool_series(frame, "selected_solved")
    use_adapter = _bool_series(frame, "use_adapter")
    selected_time = pd.to_numeric(frame["selected_time_est"], errors="coerce")
    base_time = pd.to_numeric(frame["base_time"], errors="coerce")
    current_time = pd.to_numeric(frame.get("current_time", selected_time), errors="coerce")
    old_time = pd.to_numeric(frame.get("old_time", base_time), errors="coerce")
    slowdown_score = (current_time - np.minimum(base_time, old_time)).fillna(0.0)
    frame["_slowdown_score"] = slowdown_score
    selected_slowdown = use_adapter & base_solved & selected_solved & (
        (slowdown_score >= 0.15) | (current_time >= 1.10 * base_time.clip(lower=1.0e-9))
    )
    if "outcome_vs_old" in frame.columns:
        selected_slowdown = selected_slowdown | frame["outcome_vs_old"].isin(["lost_vs_old", "slower_both_solved"])
    slowdown_keys = (
        frame.loc[selected_slowdown]
        .sort_values("_slowdown_score", ascending=False)
        .head(int(slowdown_count))["file_key"]
    )
    _append_tags(tags, slowdown_keys, "selected_slowdown")

    for column, threshold in [
        ("risk_prob", RISK_THRESHOLD),
        ("recovery_prob", RECOVERY_THRESHOLD),
        ("slowdown_prob", SLOWDOWN_THRESHOLD),
    ]:
        if column not in frame.columns:
            frame[f"_{column}_margin"] = np.inf
            continue
        frame[f"_{column}_margin"] = (pd.to_numeric(frame[column], errors="coerce") - float(threshold)).abs()
    frame["_min_threshold_margin"] = frame[
        ["_risk_prob_margin", "_recovery_prob_margin", "_slowdown_prob_margin"]
    ].min(axis=1)
    near = frame.sort_values("_min_threshold_margin").head(int(near_threshold_count))["file_key"]
    _append_tags(tags, near, "near_threshold")

    timeout_mask = ~base_solved & ~selected_solved
    if "max_abs_train_z" in frame.columns:
        timeout_ranked = frame.loc[timeout_mask].sort_values("max_abs_train_z", ascending=False)
    else:
        timeout_ranked = frame.loc[timeout_mask].sort_values("_min_threshold_margin")
    _append_tags(tags, timeout_ranked.head(int(timeout_background_count))["file_key"], "timeout_boundary")

    selected_keys = list(tags)
    if len(selected_keys) > int(max_size):
        priority = {
            "focus": 100,
            "current_recovered": 90,
            "current_lost": 90,
            "selected_slowdown": 70,
            "near_threshold": 60,
            "timeout_boundary": 40,
        }
        order = pd.DataFrame(
            [
                {
                    "file_key": key,
                    "priority": max(priority.get(tag, 0) for tag in tag_list),
                    "tag_count": len(tag_list),
                    "min_margin": float(
                        frame.loc[frame["file_key"].eq(key), "_min_threshold_margin"].iloc[0]
                    ),
                    "slowdown_score": float(frame.loc[frame["file_key"].eq(key), "_slowdown_score"].iloc[0]),
                }
                for key, tag_list in tags.items()
            ]
        )
        selected_keys = (
            order.sort_values(
                ["priority", "tag_count", "slowdown_score", "min_margin", "file_key"],
                ascending=[False, False, False, True, True],
            )
            .head(int(max_size))["file_key"]
            .tolist()
        )

    subset = frame[frame["file_key"].isin(selected_keys)].copy()
    subset["selection_tags"] = subset["file_key"].map(lambda key: ",".join(tags.get(str(key), [])))
    subset["selection_tag_count"] = subset["selection_tags"].map(lambda value: len([tag for tag in value.split(",") if tag]))
    subset = subset.sort_values(
        ["selection_tag_count", "_min_threshold_margin", "file_key"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    return subset.drop(columns=[column for column in subset.columns if column.startswith("_")])


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    text = frame[columns].copy()
    for column in columns:
        if pd.api.types.is_float_dtype(text[column]):
            text[column] = text[column].map(lambda value: f"{value:.6f}")
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in text.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(rows)


def write_doc(path: str, subset: pd.DataFrame, output_dir: str, manifest_csv: str) -> None:
    tag_counts = (
        subset.assign(selection_tags=subset["selection_tags"].str.split(","))
        .explode("selection_tags")
        .groupby("selection_tags", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "selection_tags"], ascending=[False, True])
    )
    focus = subset[subset["file_key"].isin(FOCUS_KEYS)].copy()
    columns = [
        "file_key",
        "selection_tags",
        "use_adapter",
        "base_solved",
        "selected_solved",
        "lost_solution_est",
        "recovered_timeout_est",
        "base_time",
        "current_time",
        "risk_prob",
        "recovery_prob",
        "slowdown_prob",
    ]
    doc = [
        "# Online-Consistent Boundary 子集",
        "",
        "该子集从 full400 的真实 online selector feature cache 和当前 pairwise+veto 审计表中构造。",
        "目的不是覆盖全部 200 个实例，而是优先覆盖 recovery、lost、slowdown 和阈值边界样本，",
        "用于生成与线上决策一致的 counterfactual trace。",
        "",
        f"- 输出 CNF 目录：`{output_dir}`",
        f"- manifest：`{manifest_csv}`",
        f"- 子集大小：`{len(subset)}`",
        "",
        "## 选择标签计数",
        "",
        markdown_table(tag_counts, ["selection_tags", "count"]),
        "",
        "## 重点样本",
        "",
        markdown_table(focus, [column for column in columns if column in focus.columns]),
        "",
        "## 全部样本",
        "",
        markdown_table(subset, [column for column in columns if column in subset.columns]),
        "",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def copy_subset_files(subset: pd.DataFrame, source_dir: str, output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for existing in out.glob("*.cnf"):
        existing.unlink()
    source = Path(source_dir)
    for key in subset["file_key"]:
        src = source / str(key)
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, out / src.name)


def main() -> None:
    args = parse_args()
    frame = _read_online_frame(args.features_csv, args.audit_csv, args.source_dir)
    frame = _merge_old_comparison(frame, args.old_comparison_csv)
    subset = select_boundary_subset(
        frame,
        max_size=args.max_size,
        near_threshold_count=args.near_threshold_count,
        slowdown_count=args.slowdown_count,
        timeout_background_count=args.timeout_background_count,
        focus_keys=FOCUS_KEYS,
    )
    copy_subset_files(subset, args.source_dir, args.output_dir)
    manifest = Path(args.manifest_csv)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(manifest, index=False)
    write_doc(args.doc_path, subset, args.output_dir, args.manifest_csv)
    print(f"wrote {len(subset)} CNFs to {args.output_dir}")
    print(subset["selection_tags"].str.get_dummies(sep=",").sum().sort_values(ascending=False).to_string())
    print(f"wrote manifest: {args.manifest_csv}")
    print(f"wrote doc: {args.doc_path}")


if __name__ == "__main__":
    main()
