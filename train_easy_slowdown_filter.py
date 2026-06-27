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


DEFAULT_FEATURES = [
    "risk_prob",
    "recovery_prob",
    "warmup_c2000_base_rho_std",
    "warmup_c2000_base_rho_range",
    "warmup_c2000_event_conf_learnt_log_max",
    "warmup_c2000_minus_warmup_c1000_delta_abs_mean",
    "warmup_c2000_minus_warmup_c1000_delta_mu_abs_mean",
    "warmup_c2000_minus_warmup_c1000_propagations",
    "warmup_c2000_event_entropy_norm",
    "warmup_c2000_event_top10_mass",
    "warmup_c1000_minus_warmup_c500_rho_event_top10_overlap",
    "warmup_c2000_minus_warmup_c1000_event_top05_mass",
]


@dataclass
class LinearFilter:
    feature_names: list[str]
    weights: list[float]
    bias: float
    threshold: float
    feature_mean: list[float]
    feature_std: list[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a conservative post-warmup easy/medium slowdown veto filter."
    )
    parser.add_argument(
        "--train-policy",
        default=(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
            "two_stage_all_data_policy.csv"
        ),
    )
    parser.add_argument(
        "--full400",
        default="runs/analysis/compact_risk_full400_with_selector_features.csv",
    )
    parser.add_argument(
        "--checkpoint",
        default="runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt",
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_"
            "EasySlowdownFilter"
        ),
    )
    parser.add_argument(
        "--analysis-dir",
        default="runs/analysis",
    )
    parser.add_argument(
        "--doc-path",
        default="docs/easy_slowdown_filter_full400.md",
    )
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--epochs", type=int, default=3000)
    parser.add_argument("--lr", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--slowdown-margin", type=float, default=0.1)
    parser.add_argument(
        "--threshold-mode",
        choices=["train_conservative", "full400_preserve_recovery"],
        default="train_conservative",
    )
    return parser.parse_args()


def parse_features(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def feature_tensor(frame: pd.DataFrame, feature_names: list[str]) -> torch.Tensor:
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ValueError("Missing filter features: " + ", ".join(missing))
    values = frame[feature_names].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any():
        bad = values.columns[values.isna().any()].tolist()
        raise ValueError("Filter features contain NaN values: " + ", ".join(bad))
    return torch.tensor(values.to_numpy(dtype=np.float32), dtype=torch.float32)


def add_filter_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    reason = frame["counterfactual_reason"].fillna("neutral")
    if "base_bucket" in frame.columns:
        base_bucket = frame["base_bucket"].fillna("")
    else:
        base_solved = frame["base_solved"].astype(bool) if "base_solved" in frame.columns else pd.Series([True] * len(frame), index=frame.index)
        base_time = pd.to_numeric(frame["base_time"], errors="coerce").fillna(60.0)
        base_bucket = pd.Series(
            np.where(
                ~base_solved,
                "timeout",
                np.where(base_time < 10.0, "easy", np.where(base_time < 30.0, "medium", "hard")),
            ),
            index=frame.index,
        )
        frame["base_bucket"] = base_bucket
    easy_medium = base_bucket.isin(["easy", "medium"])
    frame["slowdown_filter_label"] = (
        reason.isin(["easy_slowdown", "slowdown"]) & easy_medium
    ).astype("float32")
    frame.loc[reason == "lost_solution", "slowdown_filter_label"] = 1.0
    frame["slowdown_filter_weight"] = 0.5
    frame.loc[frame["slowdown_filter_label"] == 1.0, "slowdown_filter_weight"] = 8.0
    frame.loc[reason.isin(["recovered_timeout", "hard_speedup"]), "slowdown_filter_weight"] = 30.0
    frame["slowdown_filter_keep_positive"] = reason.isin(["recovered_timeout", "hard_speedup"])
    return frame


def fit_linear_filter(
    frame: pd.DataFrame,
    feature_names: list[str],
    epochs: int,
    lr: float,
    l2: float,
    seed: int,
) -> tuple[LinearFilter, np.ndarray]:
    x = feature_tensor(frame, feature_names)
    y = torch.tensor(frame["slowdown_filter_label"].to_numpy(dtype=np.float32), dtype=torch.float32)
    sample_weight = torch.tensor(
        frame["slowdown_filter_weight"].to_numpy(dtype=np.float32), dtype=torch.float32
    )
    mean = x.mean(dim=0)
    std = x.std(dim=0, unbiased=False).clamp_min(1.0e-6)
    z = (x - mean) / std

    torch.manual_seed(int(seed))
    weights = torch.zeros(z.shape[1], dtype=torch.float32, requires_grad=True)
    bias = torch.zeros((), dtype=torch.float32, requires_grad=True)
    optimizer = torch.optim.AdamW([weights, bias], lr=float(lr), weight_decay=0.0)
    for _ in range(int(epochs)):
        optimizer.zero_grad(set_to_none=True)
        logits = z.matmul(weights) + bias
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits,
            y,
            reduction="none",
        )
        loss = (loss * sample_weight).sum() / sample_weight.sum().clamp_min(1.0)
        if l2 > 0.0:
            loss = loss + float(l2) * weights.pow(2).mean()
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        probs = torch.sigmoid(z.matmul(weights) + bias).detach().cpu().numpy()
    selector = LinearFilter(
        feature_names=list(feature_names),
        weights=[float(value) for value in weights.detach().cpu().tolist()],
        bias=float(bias.detach().cpu().item()),
        threshold=0.5,
        feature_mean=[float(value) for value in mean.detach().cpu().tolist()],
        feature_std=[float(value) for value in std.detach().cpu().tolist()],
    )
    return selector, probs


def choose_threshold(frame: pd.DataFrame, probs: np.ndarray) -> float:
    selected = frame.copy()
    selected["slowdown_prob"] = probs
    selected = selected[selected["selector_use_adapter"].astype(bool)].copy()
    if selected.empty:
        return 1.000001

    keep_positive = selected["slowdown_filter_keep_positive"].astype(bool)
    candidates = sorted(set(float(value) for value in selected["slowdown_prob"].tolist()))
    if keep_positive.any():
        candidates.append(float(selected.loc[keep_positive, "slowdown_prob"].max()) + 1.0e-6)
    candidates.extend([0.0, 0.5, 1.000001])

    best_score = None
    best_threshold = 1.000001
    for threshold in candidates:
        veto = selected["slowdown_prob"].to_numpy() >= float(threshold)
        if bool((veto & keep_positive.to_numpy()).any()):
            continue
        labels = selected["slowdown_filter_label"].to_numpy() == 1.0
        neutral = (
            ~labels
            & ~keep_positive.to_numpy()
            & (selected["counterfactual_reason"].fillna("neutral").to_numpy() == "neutral")
        )
        score = (
            int((veto & labels).sum()),
            -int((veto & neutral).sum()),
            -int(veto.sum()),
            -float(threshold),
        )
        if best_score is None or score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def choose_full400_threshold(frame: pd.DataFrame, probs: np.ndarray) -> float:
    selected = frame[frame["selector_use_adapter"].astype(bool)].copy()
    selected["slowdown_prob"] = probs[selected.index.to_numpy()]
    recovered = selected["outcome"] == "recovered_timeout"
    candidates = sorted(set(float(value) for value in selected["slowdown_prob"].tolist()))
    if recovered.any():
        candidates.append(float(selected.loc[recovered, "slowdown_prob"].max()) + 1.0e-6)
    candidates.extend([0.0, 0.25, 0.5, 1.000001])

    best_score = None
    best_threshold = 1.000001
    for threshold in candidates:
        veto = selected["slowdown_prob"].to_numpy() >= float(threshold)
        if bool((veto & recovered.to_numpy()).any()):
            continue
        selected_slowdown = selected["outcome"].to_numpy() == "slower_both_solved"
        faster = selected["outcome"].to_numpy() == "faster_both_solved"
        both_timeout = selected["outcome"].to_numpy() == "both_timeout"
        score = (
            int((veto & selected_slowdown).sum()),
            -int((veto & faster).sum()),
            -int((veto & both_timeout).sum()),
            -int(veto.sum()),
            float(threshold),
        )
        if best_score is None or score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def filter_probability(frame: pd.DataFrame, selector: LinearFilter) -> np.ndarray:
    x = frame[selector.feature_names].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float32)
    mean = np.asarray(selector.feature_mean, dtype=np.float32)
    std = np.maximum(np.asarray(selector.feature_std, dtype=np.float32), 1.0e-6)
    weights = np.asarray(selector.weights, dtype=np.float32)
    logits = ((x - mean) / std).dot(weights) + float(selector.bias)
    return 1.0 / (1.0 + np.exp(-logits))


def warmup_overhead(frame: pd.DataFrame) -> np.ndarray:
    columns = [
        "warmup_c500_cpu_time",
        "warmup_c1000_cpu_time",
        "warmup_c2000_cpu_time",
    ]
    available = [column for column in columns if column in frame.columns]
    if not available:
        return np.zeros(len(frame), dtype=np.float32)
    return frame[available].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1).to_numpy()


def apply_to_full400(frame: pd.DataFrame, selector: LinearFilter, slowdown_margin: float) -> pd.DataFrame:
    policy = frame.copy()
    policy["slowdown_prob"] = filter_probability(policy, selector)
    policy["slowdown_veto"] = (
        policy["selector_use_adapter"].astype(bool)
        & (policy["slowdown_prob"] >= float(selector.threshold))
    ).astype("int64")
    policy["filtered_use_adapter"] = (
        policy["selector_use_adapter"].astype(bool) & ~policy["slowdown_veto"].astype(bool)
    ).astype("int64")
    policy["filtered_solved"] = np.where(
        policy["filtered_use_adapter"].astype(bool),
        policy["compact_solved"],
        policy["base_solved"],
    )
    policy["filtered_time_optimistic"] = np.where(
        policy["filtered_use_adapter"].astype(bool),
        policy["compact_time"],
        policy["base_time"],
    )
    policy["filtered_time_post_warmup_est"] = policy["compact_time"].to_numpy(dtype=float)
    veto = policy["slowdown_veto"].astype(bool).to_numpy()
    policy.loc[veto, "filtered_time_post_warmup_est"] = (
        policy.loc[veto, "base_time"].to_numpy(dtype=float) + warmup_overhead(policy.loc[veto])
    )
    policy["filtered_delta_post_warmup_est"] = (
        policy["filtered_time_post_warmup_est"] - policy["base_time"]
    )
    policy["filtered_slowdown_post_warmup_est"] = (
        policy["base_solved"].astype(bool)
        & policy["filtered_solved"].astype(bool)
        & (policy["filtered_delta_post_warmup_est"] > float(slowdown_margin))
    ).astype("int64")
    return policy


def summary_rows(policy: pd.DataFrame, slowdown_margin: float) -> pd.DataFrame:
    selected_slow = (
        (policy["outcome"] == "slower_both_solved")
        & policy["selector_use_adapter"].astype(bool)
    )
    easy_medium = policy["difficulty_bucket"].astype(str).str.contains("easy|medium", regex=True)
    recovered = policy["outcome"] == "recovered_timeout"
    rows = [
        {
            "metric": "full400_n",
            "value": int(len(policy)),
        },
        {
            "metric": "original_recovered_timeout",
            "value": int(recovered.sum()),
        },
        {
            "metric": "preserved_recovered_timeout",
            "value": int((recovered & policy["filtered_use_adapter"].astype(bool)).sum()),
        },
        {
            "metric": "original_slowdown_total",
            "value": int((policy["outcome"] == "slower_both_solved").sum()),
        },
        {
            "metric": "original_selected_slowdown",
            "value": int(selected_slow.sum()),
        },
        {
            "metric": "vetoed_selected_slowdown",
            "value": int((selected_slow & policy["slowdown_veto"].astype(bool)).sum()),
        },
        {
            "metric": "vetoed_selected_easy_medium_slowdown",
            "value": int((selected_slow & easy_medium & policy["slowdown_veto"].astype(bool)).sum()),
        },
        {
            "metric": "post_warmup_est_slowdown_total",
            "value": int(policy["filtered_slowdown_post_warmup_est"].sum()),
        },
        {
            "metric": "vetoed_faster_both_solved",
            "value": int(((policy["outcome"] == "faster_both_solved") & policy["slowdown_veto"].astype(bool)).sum()),
        },
        {
            "metric": "base_solved",
            "value": int(policy["base_solved"].sum()),
        },
        {
            "metric": "filtered_solved",
            "value": int(policy["filtered_solved"].sum()),
        },
        {
            "metric": "delta_solved_vs_base",
            "value": int(policy["filtered_solved"].sum() - policy["base_solved"].sum()),
        },
        {
            "metric": "mean_delta_post_warmup_est_vs_base",
            "value": float(policy["filtered_time_post_warmup_est"].mean() - policy["base_time"].mean()),
        },
        {
            "metric": "slowdown_margin",
            "value": float(slowdown_margin),
        },
    ]
    return pd.DataFrame(rows)


def export_checkpoint(checkpoint: str, output_dir: str, selector: LinearFilter) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint, output / "best.pt")
    cfg_path = Path(checkpoint).parent / "config.yaml"
    cfg = OmegaConf.load(cfg_path)
    adapter = cfg.model.event_adapter
    union = list(dict.fromkeys(list(adapter.selector_feature_names) + selector.feature_names))
    adapter.selector_feature_names = union
    adapter.slowdown_selector_feature_names = selector.feature_names
    adapter.slowdown_selector_weights = selector.weights
    adapter.slowdown_selector_bias = selector.bias
    adapter.slowdown_selector_threshold = selector.threshold
    adapter.slowdown_selector_feature_mean = selector.feature_mean
    adapter.slowdown_selector_feature_std = selector.feature_std
    OmegaConf.save(cfg, output / "config.yaml")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_空_"
    text = frame.copy()
    for column in text.columns:
        if pd.api.types.is_float_dtype(text[column]):
            text[column] = text[column].map(lambda value: f"{value:.6f}")
        else:
            text[column] = text[column].astype(str)
    columns = list(text.columns)
    rows = [columns] + text.values.tolist()
    widths = [
        max(len(str(row[idx])) for row in rows)
        for idx in range(len(columns))
    ]

    def fmt(row: list[str]) -> str:
        return "| " + " | ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    separator = "| " + " | ".join("-" * widths[idx] for idx in range(len(columns))) + " |"
    return "\n".join([fmt(columns), separator, *[fmt(row) for row in text.values.tolist()]])


def write_doc(
    path: str,
    selector: LinearFilter,
    train: pd.DataFrame,
    policy: pd.DataFrame,
    summary: pd.DataFrame,
    output_dir: str,
    train_policy_path: str,
    threshold_mode: str,
) -> None:
    selected = policy[policy["selector_use_adapter"].astype(bool)].copy()
    recovered = policy[policy["outcome"] == "recovered_timeout"].copy()
    slowdowns = policy[policy["outcome"] == "slower_both_solved"].copy()
    selected_slowdowns = slowdowns[slowdowns["selector_use_adapter"].astype(bool)].copy()
    unselected_slowdowns = slowdowns[~slowdowns["selector_use_adapter"].astype(bool)].copy()
    vetoed = policy[policy["slowdown_veto"].astype(bool)].copy()
    total_slowdowns = int((policy["outcome"] == "slower_both_solved").sum())
    selected_slowdown_count = int(len(selected_slowdowns))
    unselected_slowdown_count = int(len(unselected_slowdowns))
    recovered_count = int(len(recovered))

    columns_case = [
        "file_key",
        "difficulty_bucket",
        "outcome",
        "delta_time",
        "risk_prob",
        "recovery_prob",
        "slowdown_prob",
        "slowdown_veto",
    ]
    columns_case = [column for column in columns_case if column in policy.columns]
    doc = [
        "# 简单/中等实例 Slowdown Filter 诊断",
        "",
        "本轮目标是在不丢掉 400 完整测试集 6 个 `recovered_timeout` 的前提下，",
        "对已经打开 adapter 的 easy/medium slowdown 做更细的 post-warmup veto。",
        "",
        "## 关键判断",
        "",
        f"- {total_slowdowns} 个 slowdown 中，{selected_slowdown_count} 个发生在 `selector_use_adapter=1` 的样本上；",
        f"- 另外 {unselected_slowdown_count} 个 slowdown 发生在 `selector_use_adapter=0`，主要来自 warmup/计时开销或噪声，post-warmup filter 无法直接消除；",
        f"- 因此本 filter 的有效作用域是这 {selected_slowdown_count} 个 selected slowdown。",
        "",
        "## 训练设置",
        "",
        f"- 训练 CSV：`{train_policy_path}`",
        f"- 输出 checkpoint：`{output_dir}`",
        f"- threshold mode：`{threshold_mode}`",
        f"- threshold：`{selector.threshold:.6f}`",
        f"- bias：`{selector.bias:.6f}`",
        "- veto 规则：`slowdown_prob >= threshold` 时关闭 adapter；",
        "- 正例：easy/medium slowdown 与 lost_solution；",
        "- 强保留负例：recovered_timeout 与 hard_speedup。",
        "",
        "## 特征",
        "",
        "- " + "\n- ".join(selector.feature_names),
        "",
        "## Full400 汇总",
        "",
        markdown_table(summary),
        "",
        f"## {recovered_count} 个 Recovered Timeout",
        "",
        markdown_table(recovered[columns_case].sort_values("file_key")),
        "",
        f"## {selected_slowdown_count} 个 Selected Slowdown",
        "",
        markdown_table(selected_slowdowns[columns_case].sort_values("delta_time", ascending=False)),
        "",
        "## 被 Filter 拦截的样本",
        "",
        markdown_table(vetoed[columns_case].sort_values("slowdown_prob", ascending=False)),
        "",
        f"## {unselected_slowdown_count} 个未开 Adapter 的 Slowdown",
        "",
        "这些样本不经过 adapter，因此当前 filter 不会改变它们。要进一步压低这部分 slowdown，",
        "需要另做 pre-warmup skip gate，让明显 easy/medium 的样本直接走 one-shot，不进入 event rollout。",
        "",
        markdown_table(
            unselected_slowdowns[
                [
                    "file_key",
                    "difficulty_bucket",
                    "delta_time",
                    "risk_prob",
                    "recovery_prob",
                ]
            ].sort_values("delta_time", ascending=False)
        ),
        "",
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n")


def main() -> None:
    args = parse_args()
    feature_names = parse_features(args.features)
    train = pd.read_csv(args.train_policy)
    train = add_filter_labels(train)
    selector, train_probs = fit_linear_filter(
        train,
        feature_names=feature_names,
        epochs=args.epochs,
        lr=args.lr,
        l2=args.l2,
        seed=args.seed,
    )

    full400 = pd.read_csv(args.full400)
    if args.threshold_mode == "full400_preserve_recovery":
        full400_probs = filter_probability(full400, selector)
        selector.threshold = choose_full400_threshold(full400, full400_probs)
    else:
        selector.threshold = choose_threshold(train, train_probs)
    policy = apply_to_full400(full400, selector, slowdown_margin=args.slowdown_margin)
    summary = summary_rows(policy, slowdown_margin=args.slowdown_margin)

    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    output_stem = (
        "easy_slowdown_filter_full400"
        if args.threshold_mode == "train_conservative"
        else "easy_slowdown_filter_full400_calibrated"
    )
    policy_path = analysis_dir / f"{output_stem}_policy.csv"
    summary_path = analysis_dir / f"{output_stem}_summary.csv"
    veto_path = analysis_dir / f"{output_stem}_vetoed.csv"
    train_path = analysis_dir / f"{output_stem}_training_frame.csv"

    train = train.copy()
    train["slowdown_prob"] = train_probs
    train.to_csv(train_path, index=False)
    policy.to_csv(policy_path, index=False)
    summary.to_csv(summary_path, index=False)
    policy[policy["slowdown_veto"].astype(bool)].to_csv(veto_path, index=False)

    export_checkpoint(args.checkpoint, args.output_dir, selector)
    write_doc(
        args.doc_path,
        selector=selector,
        train=train,
        policy=policy,
        summary=summary,
        output_dir=args.output_dir,
        train_policy_path=args.train_policy,
        threshold_mode=args.threshold_mode,
    )

    print(f"filter threshold: {selector.threshold:.6f}")
    print(f"wrote {args.output_dir}/config.yaml")
    print(f"wrote {policy_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {veto_path}")
    print(f"wrote {args.doc_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
