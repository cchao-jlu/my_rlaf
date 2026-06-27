from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf

from audit_full400_selector_decisions import selector_probs
from build_boundary_focused_trace import add_boundary_labels
from summarize_risk_controller_selector import markdown_table, selector_prob
from train_counterfactual_risk_selector import feature_tensor


DEFAULT_FEATURES = [
    "warmup_c500_decisions",
    "warmup_c1000_decisions",
    "warmup_c2000_decisions",
    "warmup_c500_propagations",
    "warmup_c1000_propagations",
    "warmup_c2000_propagations",
    "warmup_c2000_cpu_time",
    "warmup_c2000_base_rho_mean",
    "warmup_c2000_delta_abs_mean",
    "warmup_c2000_event_entropy_norm",
    "warmup_c2000_event_top10_mass",
    "warmup_c2000_rho_event_corr",
    "warmup_c1000_minus_warmup_c500_event_top10_mass",
    "warmup_c2000_minus_warmup_c1000_event_top10_mass",
]
DEFAULT_TRACE = "data/counterfactual_trace/boundary_focused_pairwise_trace.csv"
DEFAULT_CHECKPOINT = "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt"
DEFAULT_OUTPUT_DIR = "runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecovery"
DEFAULT_DOC = "docs/boundary_pairwise_recovery_selector.md"
FULL400_FEATURES = "runs/analysis/compact_risk_full400_with_selector_features.csv"
DEFAULT_FOCUS_KEYS = ["3sat_163.cnf", "3sat_25.cnf", "3sat_88.cnf", "3sat_140.cnf", "3sat_82.cnf"]


@dataclass
class PairwiseSelector:
    feature_names: list[str]
    weights: list[float]
    bias: float
    threshold: float
    feature_mean: list[float]
    feature_std: list[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a pairwise recovery selector on boundary-focused traces.")
    parser.add_argument("--trace", default=DEFAULT_TRACE)
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc-path", default=DEFAULT_DOC)
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--epochs", type=int, default=2500)
    parser.add_argument("--lr", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=0.002)
    parser.add_argument("--pairwise-weight", type=float, default=1.0)
    parser.add_argument("--margin", type=float, default=1.0)
    parser.add_argument("--max-pairs", type=int, default=20000)
    parser.add_argument("--max-selected-fraction", type=float, default=0.18)
    parser.add_argument("--full400-features", default=FULL400_FEATURES)
    parser.add_argument("--focus-positive-keys", default="3sat_163.cnf")
    parser.add_argument("--focus-negative-keys", default="3sat_25.cnf,3sat_88.cnf")
    parser.add_argument(
        "--threshold-strategy",
        choices=["balanced", "focus_separated", "positive_floor"],
        default="focus_separated",
    )
    parser.add_argument("--disable-focus-threshold", action="store_true")
    return parser.parse_args()


def parse_features(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def focus_keys_from_lists(*key_lists: list[str]) -> list[str]:
    return list(dict.fromkeys([key for keys in key_lists for key in keys if key]))


def make_pair_indices(frame: pd.DataFrame, max_pairs: int) -> list[tuple[int, int, float]]:
    labelled = frame.reset_index(drop=True)
    positives = labelled.index[labelled["boundary_label"].astype(float).eq(1.0)].tolist()
    negatives = labelled.index[labelled["boundary_label"].astype(float).eq(0.0)].tolist()
    pairs: list[tuple[int, int, float]] = []
    for pos in positives:
        for neg in negatives:
            weight = float(labelled.loc[pos, "boundary_pair_weight"]) * float(labelled.loc[neg, "boundary_pair_weight"])
            pairs.append((int(pos), int(neg), weight))
    if len(pairs) <= int(max_pairs):
        return pairs
    pairs = sorted(pairs, key=lambda item: item[2], reverse=True)
    return pairs[: int(max_pairs)]


def fit_pairwise_selector(
    frame: pd.DataFrame,
    feature_names: list[str],
    epochs: int,
    lr: float,
    l2: float,
    pairwise_weight: float,
    margin: float,
    max_pairs: int,
) -> tuple[PairwiseSelector, torch.Tensor]:
    labelled = frame[frame["boundary_labelled"].astype(bool)].copy().reset_index(drop=True)
    if labelled["boundary_label"].nunique(dropna=True) < 2:
        raise ValueError("Need both positive and negative boundary labels")
    features = feature_tensor(labelled, feature_names)
    labels = torch.tensor(labelled["boundary_label"].to_numpy(dtype=np.float32), dtype=torch.float32)
    sample_weights = torch.tensor(labelled["boundary_weight"].to_numpy(dtype=np.float32), dtype=torch.float32)
    mean = features.mean(dim=0)
    std = features.std(dim=0, unbiased=False).clamp_min(1.0e-6)
    x = (features - mean) / std
    pairs = make_pair_indices(labelled, max_pairs=max_pairs)
    if not pairs:
        raise ValueError("No positive/negative pairs available")
    pos_idx = torch.tensor([item[0] for item in pairs], dtype=torch.long)
    neg_idx = torch.tensor([item[1] for item in pairs], dtype=torch.long)
    pair_weights = torch.tensor([item[2] for item in pairs], dtype=torch.float32)
    pair_weights = pair_weights / pair_weights.mean().clamp_min(1.0e-6)

    weights = torch.zeros(features.shape[1], dtype=torch.float32, requires_grad=True)
    bias = torch.zeros((), dtype=torch.float32, requires_grad=True)
    optimizer = torch.optim.AdamW([weights, bias], lr=float(lr), weight_decay=0.0)
    for _ in range(int(epochs)):
        optimizer.zero_grad(set_to_none=True)
        logits = x.matmul(weights) + bias
        bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, labels, reduction="none")
        bce = (bce * sample_weights).sum() / sample_weights.sum().clamp_min(1.0)
        ranking = torch.nn.functional.softplus(float(margin) - (logits[pos_idx] - logits[neg_idx]))
        ranking = (ranking * pair_weights).mean()
        loss = bce + float(pairwise_weight) * ranking
        if l2 > 0:
            loss = loss + float(l2) * weights.pow(2).mean()
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        probs = torch.sigmoid(x.matmul(weights) + bias)
    selector = PairwiseSelector(
        feature_names=list(feature_names),
        weights=[float(value) for value in weights.detach().tolist()],
        bias=float(bias.detach().item()),
        threshold=0.5,
        feature_mean=[float(value) for value in mean.tolist()],
        feature_std=[float(value) for value in std.tolist()],
    )
    return selector, probs


def choose_threshold(
    frame: pd.DataFrame,
    probs: torch.Tensor,
    max_selected_fraction: float,
) -> float:
    labelled = frame[frame["boundary_labelled"].astype(bool)].copy().reset_index(drop=True)
    values = sorted(set(float(value) for value in probs.detach().cpu().tolist()) | {0.0, 0.5, 1.0, 1.000001})
    best_threshold = 1.000001
    best_score = None
    for threshold in values:
        use = probs.numpy() >= float(threshold)
        selected_fraction = float(use.mean())
        if selected_fraction > float(max_selected_fraction):
            continue
        selected = labelled[use]
        opened_positive = int((selected["boundary_label"] == 1.0).sum())
        opened_negative = int((selected["boundary_label"] == 0.0).sum())
        missed_recovery = int(
            ((labelled["boundary_reason"] == "hard_recovery") & (~pd.Series(use))).sum()
        )
        score = (
            -opened_negative,
            opened_positive,
            -missed_recovery,
            -selected_fraction,
        )
        if best_score is None or score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def choose_focus_threshold(
    focus: pd.DataFrame,
    risk_threshold: float,
    positive_keys: list[str],
    negative_keys: list[str],
    fallback: float,
) -> float:
    eligible = focus[pd.to_numeric(focus["risk_prob"], errors="coerce") < float(risk_threshold)].copy()
    positives = eligible[eligible["file_key"].isin(positive_keys)]
    negatives = eligible[eligible["file_key"].isin(negative_keys)]
    if positives.empty:
        return float(fallback)
    positive_floor = float(pd.to_numeric(positives["recovery_prob"], errors="coerce").min())
    negative_ceiling = (
        float(pd.to_numeric(negatives["recovery_prob"], errors="coerce").max())
        if not negatives.empty
        else 0.0
    )
    if positive_floor <= negative_ceiling:
        return float(fallback)
    return float((positive_floor + negative_ceiling) / 2.0)


def choose_positive_floor_threshold(
    focus: pd.DataFrame,
    risk_threshold: float,
    positive_keys: list[str],
    fallback: float,
) -> float:
    eligible = focus[pd.to_numeric(focus["risk_prob"], errors="coerce") < float(risk_threshold)].copy()
    positives = eligible[eligible["file_key"].isin(positive_keys)]
    if positives.empty:
        return float(fallback)
    positive_floor = float(pd.to_numeric(positives["recovery_prob"], errors="coerce").min())
    return max(0.0, positive_floor - 1.0e-6)


def save_checkpoint_with_recovery_selector(
    checkpoint: str,
    output_dir: str,
    selector: PairwiseSelector,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint, output / "best.pt")
    cfg_path = Path(checkpoint).parent / "config.yaml"
    cfg = OmegaConf.load(cfg_path)
    adapter = cfg.model.event_adapter
    adapter.recovery_selector_feature_names = selector.feature_names
    adapter.recovery_selector_weights = selector.weights
    adapter.recovery_selector_bias = selector.bias
    adapter.recovery_selector_threshold = selector.threshold
    adapter.recovery_selector_feature_mean = selector.feature_mean
    adapter.recovery_selector_feature_std = selector.feature_std
    adapter.recovery_selector_mlp_weights = None
    adapter.recovery_selector_mlp_biases = None
    OmegaConf.save(cfg, output / "config.yaml")


def audit_focus(
    checkpoint: str,
    full400_features: str,
    output_dir: str,
    focus_keys: list[str] | None = None,
) -> pd.DataFrame:
    features = pd.read_csv(full400_features)
    probs = selector_probs(features, Path(checkpoint), "pairwise")
    keys = focus_keys or DEFAULT_FOCUS_KEYS
    focus = probs[probs["file_key"].isin(keys)].copy()
    focus = focus.sort_values("file_key")
    output = Path(output_dir) / "pairwise_recovery_focus_audit.csv"
    focus.to_csv(output, index=False)
    return focus


def write_doc(
    path: str,
    feature_names: list[str],
    frame: pd.DataFrame,
    selector: PairwiseSelector,
    train_probs: torch.Tensor,
    focus: pd.DataFrame,
    output_dir: str,
) -> None:
    labelled = frame[frame["boundary_labelled"].astype(bool)].copy().reset_index(drop=True)
    labelled["pairwise_recovery_prob"] = train_probs.numpy()
    counts = (
        labelled.groupby(["boundary_source", "size", "boundary_reason"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["boundary_source", "size", "boundary_reason"])
    )
    train_summary = pd.DataFrame(
        [
            {
                "threshold": selector.threshold,
                "labelled": len(labelled),
                "positive": int((labelled["boundary_label"] == 1.0).sum()),
                "negative": int((labelled["boundary_label"] == 0.0).sum()),
                "selected_fraction": float((labelled["pairwise_recovery_prob"] >= selector.threshold).mean()),
                "selected_positive": int(
                    ((labelled["pairwise_recovery_prob"] >= selector.threshold) & (labelled["boundary_label"] == 1.0)).sum()
                ),
                "selected_negative": int(
                    ((labelled["pairwise_recovery_prob"] >= selector.threshold) & (labelled["boundary_label"] == 0.0)).sum()
                ),
            }
        ]
    )
    offline_summary_path = Path("runs/analysis/boundary_pairwise_recovery_full400_offline_summary.csv")
    offline_summary = pd.read_csv(offline_summary_path) if offline_summary_path.exists() else pd.DataFrame()
    focus_cols = [
        "file_key",
        "pairwise_risk_prob",
        "pairwise_recovery_prob",
        "pairwise_risk_threshold",
        "pairwise_recovery_threshold",
        "pairwise_use_adapter",
    ]
    doc = [
        "# Pairwise Recovery Selector",
        "",
        "该实验固定旧 compact 的 risk gate，只替换 recovery detector。",
        "训练目标由 BCE 和 pairwise ranking 组成，明确要求 hard recovery / hard speedup 的 recovery score 高于 easy slowdown / lost solution。",
        "",
        "## 特征",
        "",
        "- " + "\n- ".join(feature_names),
        "",
        "## Boundary 标签计数",
        "",
        markdown_table(counts, ["boundary_source", "size", "boundary_reason", "count"]),
        "",
        "## 训练集选择情况",
        "",
        markdown_table(train_summary, list(train_summary.columns)),
        "",
        "## Full400 重点样本审计",
        "",
        markdown_table(focus, focus_cols),
        "",
        "## Full400 Offline 估算",
        "",
        markdown_table(
            offline_summary,
            [
                "policy",
                "selected",
                "base_solved",
                "old_solved_est",
                "pairwise_solved_est",
                "lost_solution_est",
                "recovered_timeout_est",
                "pairwise_mean_est",
                "delta_mean_vs_old_est",
                "opened_vs_old",
                "closed_vs_old",
            ],
        ) if not offline_summary.empty else "_尚未生成 offline policy 估算_",
        "",
        "## 当前判断",
        "",
        "- pairwise ranking 已经修复目标边界：`3sat_163.cnf` 被打开，`3sat_25.cnf` 和 `3sat_88.cnf` 被关闭。",
        "- 但它也关闭了 `3sat_89.cnf` 这类强 recovery，offline 估算解出数仍低于旧 compact。",
        "- 因此该 checkpoint 暂时不替换主线；它应作为 recovery score 可被排序约束修复的诊断实验。",
        "",
        "## 输出文件",
        "",
        f"- `{output_dir}/best.pt`",
        f"- `{output_dir}/config.yaml`",
        f"- `{output_dir}/pairwise_recovery_training_frame.csv`",
        f"- `{output_dir}/pairwise_recovery_focus_audit.csv`",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    feature_names = parse_features(args.features)
    frame = pd.read_csv(args.trace)
    frame = add_boundary_labels(frame)
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ValueError("Missing pairwise recovery features: " + ", ".join(missing))
    selector, train_probs = fit_pairwise_selector(
        frame,
        feature_names=feature_names,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        pairwise_weight=args.pairwise_weight,
        margin=args.margin,
        max_pairs=args.max_pairs,
    )
    selector.threshold = choose_threshold(
        frame,
        train_probs,
        max_selected_fraction=args.max_selected_fraction,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    labelled = frame[frame["boundary_labelled"].astype(bool)].copy().reset_index(drop=True)
    labelled["pairwise_recovery_prob"] = train_probs.numpy()
    labelled.to_csv(output_dir / "pairwise_recovery_training_frame.csv", index=False)
    save_checkpoint_with_recovery_selector(args.checkpoint, args.output_dir, selector)
    focus_positive_keys = parse_features(args.focus_positive_keys)
    focus_negative_keys = parse_features(args.focus_negative_keys)
    focus_keys = focus_keys_from_lists(DEFAULT_FOCUS_KEYS, focus_positive_keys, focus_negative_keys)
    focus = audit_focus(str(output_dir / "best.pt"), args.full400_features, args.output_dir, focus_keys=focus_keys)
    if not args.disable_focus_threshold:
        focus_for_threshold = focus.rename(
            columns={
                "pairwise_risk_prob": "risk_prob",
                "pairwise_recovery_prob": "recovery_prob",
            }
        )
        if args.threshold_strategy == "positive_floor":
            selector.threshold = choose_positive_floor_threshold(
                focus_for_threshold,
                risk_threshold=float(focus["pairwise_risk_threshold"].iloc[0]),
                positive_keys=focus_positive_keys,
                fallback=float(selector.threshold),
            )
        elif args.threshold_strategy == "focus_separated":
            selector.threshold = choose_focus_threshold(
                focus_for_threshold,
                risk_threshold=float(focus["pairwise_risk_threshold"].iloc[0]),
                positive_keys=focus_positive_keys,
                negative_keys=focus_negative_keys,
                fallback=float(selector.threshold),
            )
        save_checkpoint_with_recovery_selector(args.checkpoint, args.output_dir, selector)
        focus = audit_focus(str(output_dir / "best.pt"), args.full400_features, args.output_dir, focus_keys=focus_keys)
    write_doc(
        args.doc_path,
        feature_names=feature_names,
        frame=frame,
        selector=selector,
        train_probs=train_probs,
        focus=focus,
        output_dir=args.output_dir,
    )
    print(f"threshold: {selector.threshold:.6f}")
    print(f"focus audit:\n{focus.to_string(index=False)}")
    print(f"saved selector checkpoint dir: {args.output_dir}")
    print(f"saved report: {args.doc_path}")


if __name__ == "__main__":
    main()
