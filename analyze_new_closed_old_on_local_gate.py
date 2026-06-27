from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import pandas as pd

from summarize_new_closed_old_on_boundary_trace import (
    FEATURE_COLUMNS,
    local_reopen_labels,
    markdown_table,
    merge_manifest_and_trace,
)


MANIFEST_CSV = Path("data/new_closed_old_on_boundary/manifest.csv")
TRACE_CSV = Path("data/counterfactual_trace/new_closed_old_on_dense400_outcomes.csv")
RULES_CSV = Path("runs/analysis/new_closed_old_on_local_reopen_gate_rules.csv")
BEST_SELECTION_CSV = Path("runs/analysis/new_closed_old_on_local_reopen_gate_best_selection.csv")
DOC_PATH = Path("docs/new_closed_old_on_local_reopen_gate.md")

DEFAULT_FEATURES = [
    "warmup_c750_minus_warmup_c500_decisions",
    "warmup_c1000_minus_warmup_c750_decisions",
    "warmup_c1500_minus_warmup_c1000_decisions",
    "warmup_c2000_minus_warmup_c1500_decisions",
    "warmup_c2000_rho_event_corr",
    "warmup_c2000_rho_event_top10_overlap",
    "warmup_c2000_base_rho_std",
    "warmup_c2000_event_top10_mass",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search local reopen-gate rules for new_closed_old_on boundary samples."
    )
    parser.add_argument("--manifest-csv", default=str(MANIFEST_CSV))
    parser.add_argument("--trace-csv", default=str(TRACE_CSV))
    parser.add_argument("--rules-csv", default=str(RULES_CSV))
    parser.add_argument("--selection-csv", default=str(BEST_SELECTION_CSV))
    parser.add_argument("--doc-path", default=str(DOC_PATH))
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--min-opened-positive", type=int, default=3)
    parser.add_argument("--max-opened-negative", type=int, default=0)
    parser.add_argument("--max-terms", type=int, default=2)
    return parser.parse_args()


def parse_features(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def evaluate_rule(frame: pd.DataFrame, rule: str, use_adapter: pd.Series) -> dict[str, object]:
    use = use_adapter.fillna(False).astype(bool)
    klass = frame["counterfactual_class"].fillna("neutral").astype(str)
    opened_positive = (klass.eq("positive") & use).sum()
    opened_negative = (klass.eq("negative") & use).sum()
    opened_neutral = (klass.eq("neutral") & use).sum()
    missed_positive = (klass.eq("positive") & ~use).sum()
    gain = -float(pd.to_numeric(frame.loc[use, "adapter_minus_base_time"], errors="coerce").sum())
    selected_keys = frame.loc[use, "file_key"].astype(str).tolist()
    selected_negative_keys = frame.loc[klass.eq("negative") & use, "file_key"].astype(str).tolist()
    selected_neutral_keys = frame.loc[klass.eq("neutral") & use, "file_key"].astype(str).tolist()
    selected_positive_keys = frame.loc[klass.eq("positive") & use, "file_key"].astype(str).tolist()
    return {
        "rule": rule,
        "selected": int(use.sum()),
        "opened_positive": int(opened_positive),
        "opened_negative": int(opened_negative),
        "opened_neutral": int(opened_neutral),
        "missed_positive": int(missed_positive),
        "net_gain_seconds": gain,
        "selected_positive_keys": ",".join(selected_positive_keys),
        "selected_negative_keys": ",".join(selected_negative_keys),
        "selected_neutral_keys": ",".join(selected_neutral_keys),
        "selected_keys": ",".join(selected_keys),
    }


def _atomic_rules(frame: pd.DataFrame, feature_names: list[str]) -> list[tuple[str, pd.Series]]:
    rules = []
    for feature in feature_names:
        if feature not in frame.columns:
            continue
        values = _numeric(frame, feature)
        for threshold in sorted(values.dropna().unique().tolist()):
            rules.append((f"{feature} >= {float(threshold):.6g}", values >= float(threshold)))
            rules.append((f"{feature} <= {float(threshold):.6g}", values <= float(threshold)))
    return rules


def find_candidate_rules(
    frame: pd.DataFrame,
    feature_names: list[str],
    min_opened_positive: int = 3,
    max_opened_negative: int = 0,
    max_terms: int = 2,
) -> pd.DataFrame:
    atomic = _atomic_rules(frame, feature_names)
    rows = []
    if int(max_terms) >= 1:
        for rule, mask in atomic:
            metrics = evaluate_rule(frame, rule, mask)
            if (
                metrics["opened_positive"] >= int(min_opened_positive)
                and metrics["opened_negative"] <= int(max_opened_negative)
            ):
                rows.append(metrics)
    if int(max_terms) >= 2:
        for (rule_a, mask_a), (rule_b, mask_b) in itertools.combinations(atomic, 2):
            left_a = rule_a.split(" ", 1)[0]
            left_b = rule_b.split(" ", 1)[0]
            if left_a == left_b:
                continue
            rule = f"{rule_a} AND {rule_b}"
            metrics = evaluate_rule(frame, rule, mask_a & mask_b)
            if (
                metrics["opened_positive"] >= int(min_opened_positive)
                and metrics["opened_negative"] <= int(max_opened_negative)
            ):
                rows.append(metrics)
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    return result.sort_values(
        by=[
            "opened_positive",
            "opened_negative",
            "missed_positive",
            "opened_neutral",
            "selected",
            "net_gain_seconds",
        ],
        ascending=[False, True, True, True, True, False],
    ).drop_duplicates("rule").reset_index(drop=True)


def load_trace_frame(manifest_csv: str, trace_csv: str) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_csv)
    trace = pd.read_csv(trace_csv)
    return local_reopen_labels(merge_manifest_and_trace(manifest, trace))


def best_selection(frame: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    if rules.empty:
        return pd.DataFrame()
    selected = set(str(value) for value in str(rules.iloc[0]["selected_keys"]).split(",") if value)
    result = frame.copy()
    result["local_gate_open"] = result["file_key"].isin(selected).astype("int64")
    cols = [
        "file_key",
        "counterfactual_class",
        "counterfactual_reason",
        "base_pipeline_time",
        "adapter_pipeline_time",
        "adapter_minus_base_time",
        "local_gate_open",
        *[feature for feature in DEFAULT_FEATURES if feature in result.columns],
    ]
    return result[cols].sort_values(["local_gate_open", "counterfactual_class", "file_key"], ascending=[False, True, True])


def write_doc(path: str, rules: pd.DataFrame, selection: pd.DataFrame, feature_names: list[str]) -> None:
    best = rules.head(1)
    selected = selection[selection["local_gate_open"].eq(1)] if not selection.empty else pd.DataFrame()
    doc = [
        "# New-Closed-Old-On 局部 Reopen Gate 诊断",
        "",
        "该诊断只面向 `new_closed_old_on` 边界样本：旧 compact 开启 adapter，而当前 online-consistent selector 关闭 adapter。",
        "目标不是再调全局阈值，而是判断是否存在局部 override 证据，能打开 `3sat_46/196/188`，同时挡住 `3sat_82/93`。",
        "",
        "## 使用特征",
        "",
        "- " + "\n- ".join(feature_names),
        "",
        "## 最优候选规则",
        "",
        markdown_table(
            best,
            [
                "rule",
                "selected",
                "opened_positive",
                "opened_negative",
                "opened_neutral",
                "missed_positive",
                "net_gain_seconds",
                "selected_positive_keys",
                "selected_negative_keys",
                "selected_neutral_keys",
            ],
        ),
        "",
        "## 候选规则 Top 10",
        "",
        markdown_table(
            rules,
            [
                "rule",
                "selected",
                "opened_positive",
                "opened_negative",
                "opened_neutral",
                "missed_positive",
                "net_gain_seconds",
            ],
            max_rows=10,
        ),
        "",
        "## 最优规则打开的样本",
        "",
        markdown_table(
            selected,
            [
                "file_key",
                "counterfactual_class",
                "counterfactual_reason",
                "adapter_minus_base_time",
                "local_gate_open",
            ],
        ),
        "",
        "## 当前判断",
        "",
        "- dense trace 支持一个局部 reopen 方向：中早期 decision drift 较高时，当前 adapter 更可能救回旧 selector 误关样本。",
        "- 但最优规则仍会打开少量 neutral timeout 样本；当前最佳规则只误开 `3sat_66.cnf`，其增益接近 0，需要下一轮重复 seed 或更长 final limit 判断是否真实安全。",
        "- 因此这一步适合进入 `new_closed_old_on` 局部 override 原型，不应替换全局 risk/recovery/slowdown gate。",
        "",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def run(
    *,
    manifest_csv: str,
    trace_csv: str,
    rules_csv: str,
    selection_csv: str,
    doc_path: str,
    feature_names: list[str],
    min_opened_positive: int,
    max_opened_negative: int,
    max_terms: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = load_trace_frame(manifest_csv, trace_csv)
    feature_names = [name for name in feature_names if name in frame.columns]
    rules = find_candidate_rules(
        frame,
        feature_names=feature_names,
        min_opened_positive=min_opened_positive,
        max_opened_negative=max_opened_negative,
        max_terms=max_terms,
    )
    selection = best_selection(frame, rules)
    Path(rules_csv).parent.mkdir(parents=True, exist_ok=True)
    rules.to_csv(rules_csv, index=False)
    selection.to_csv(selection_csv, index=False)
    write_doc(doc_path, rules, selection, feature_names)
    return rules, selection


def main() -> None:
    args = parse_args()
    rules, selection = run(
        manifest_csv=args.manifest_csv,
        trace_csv=args.trace_csv,
        rules_csv=args.rules_csv,
        selection_csv=args.selection_csv,
        doc_path=args.doc_path,
        feature_names=parse_features(args.features),
        min_opened_positive=args.min_opened_positive,
        max_opened_negative=args.max_opened_negative,
        max_terms=args.max_terms,
    )
    print(rules.head(10).to_string(index=False))
    if not selection.empty:
        print(selection[selection["local_gate_open"].eq(1)][["file_key", "counterfactual_class", "counterfactual_reason", "adapter_minus_base_time"]].to_string(index=False))
    print(f"wrote {args.rules_csv}")
    print(f"wrote {args.selection_csv}")
    print(f"wrote {args.doc_path}")


if __name__ == "__main__":
    main()
