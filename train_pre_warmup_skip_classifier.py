from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch


DEFAULT_FEATURES = [
    "base_rho_mean",
    "base_rho_std",
    "base_rho_range",
]


@dataclass
class LinearSkipClassifier:
    feature_names: list[str]
    weights: list[float]
    bias: float
    threshold: float
    feature_mean: list[float]
    feature_std: list[float]
    max_skip_fraction: float | None
    l2: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train an ultra-conservative pre-warmup skip classifier."
    )
    parser.add_argument(
        "--train-policy",
        default=(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
            "two_stage_all_data_policy.csv"
        ),
    )
    parser.add_argument(
        "--full400-policy",
        default="runs/analysis/easy_slowdown_filter_full400_calibrated_policy.csv",
    )
    parser.add_argument(
        "--full400-actual",
        default="runs/analysis/easy_slowdown_filter_full400_actual_per_instance.csv",
    )
    parser.add_argument(
        "--checkpoint",
        default=(
            "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_"
            "EasySlowdownFilterFull400Calibrated/best.pt"
        ),
    )
    parser.add_argument(
        "--config-out",
        default="configs/config_eval_guided_solver_pre_warmup_skip_classifier.yaml",
    )
    parser.add_argument("--analysis-dir", default="runs/analysis")
    parser.add_argument(
        "--doc-path",
        default="docs/pre_warmup_skip_classifier.md",
    )
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--epochs", type=int, default=3000)
    parser.add_argument("--lr", type=float, default=0.03)
    parser.add_argument("--l2-grid", default="0.01,0.05,0.1,0.5,1.0")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-train-skip-fraction", type=float, default=0.08)
    parser.add_argument("--max-eval-skip-fraction", type=float, default=0.03)
    parser.add_argument("--require-train-easy-only", action="store_true", default=True)
    parser.add_argument("--allow-train-non-easy", dest="require_train_easy_only", action="store_false")
    parser.add_argument("--win-eps", type=float, default=0.1)
    return parser.parse_args()


def parse_csv_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_float_grid(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def source_column(frame: pd.DataFrame, feature_name: str) -> str:
    if feature_name in frame.columns:
        return feature_name
    warmup_name = f"warmup_c2000_{feature_name}"
    if warmup_name in frame.columns:
        return warmup_name
    if feature_name == "base_rho_range":
        if "base_rho_max" in frame.columns and "base_rho_min" in frame.columns:
            return feature_name
        if "warmup_c2000_base_rho_max" in frame.columns and "warmup_c2000_base_rho_min" in frame.columns:
            return feature_name
    raise ValueError(f"Missing pre-warmup feature {feature_name}")


def attach_static_feature_columns(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for name in feature_names:
        if name == "base_rho_range" and name not in frame.columns:
            if "base_rho_max" in frame.columns and "base_rho_min" in frame.columns:
                frame[name] = frame["base_rho_max"] - frame["base_rho_min"]
                continue
            if "warmup_c2000_base_rho_max" in frame.columns and "warmup_c2000_base_rho_min" in frame.columns:
                frame[name] = frame["warmup_c2000_base_rho_max"] - frame["warmup_c2000_base_rho_min"]
                continue
        column = source_column(frame, name)
        frame[name] = pd.to_numeric(frame[column], errors="coerce")
    missing = [name for name in feature_names if frame[name].isna().any()]
    if missing:
        raise ValueError("Pre-warmup features contain NaN values: " + ", ".join(missing))
    return frame


def feature_tensor(frame: pd.DataFrame, feature_names: list[str]) -> torch.Tensor:
    values = frame[feature_names].to_numpy(dtype=np.float32)
    return torch.tensor(values, dtype=torch.float32)


def add_skip_labels(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    reason = frame["counterfactual_reason"].fillna("neutral")
    bucket = frame["base_bucket"].fillna("")

    easy_risk = (bucket == "easy") & reason.isin(["easy_slowdown", "lost_solution"])
    strong_keep = reason.isin(["recovered_timeout", "hard_speedup"])
    hard_keep = bucket.isin(["hard", "timeout"])
    medium_keep = bucket == "medium"

    frame["skip_label"] = easy_risk.astype("float32")
    frame["skip_strong_keep"] = strong_keep.astype("int64")
    frame["skip_easy_candidate"] = (bucket == "easy").astype("int64")
    frame["skip_weight"] = 0.25
    frame.loc[medium_keep, "skip_weight"] = 2.0
    frame.loc[hard_keep, "skip_weight"] = 6.0
    frame.loc[easy_risk, "skip_weight"] = 8.0
    frame.loc[strong_keep, "skip_weight"] = 50.0
    return frame


def fit_classifier(
    frame: pd.DataFrame,
    feature_names: list[str],
    epochs: int,
    lr: float,
    l2: float,
    seed: int,
) -> tuple[LinearSkipClassifier, np.ndarray]:
    x = feature_tensor(frame, feature_names)
    y = torch.tensor(frame["skip_label"].to_numpy(dtype=np.float32), dtype=torch.float32)
    sample_weight = torch.tensor(frame["skip_weight"].to_numpy(dtype=np.float32), dtype=torch.float32)
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

    classifier = LinearSkipClassifier(
        feature_names=list(feature_names),
        weights=[float(value) for value in weights.detach().cpu().tolist()],
        bias=float(bias.detach().cpu().item()),
        threshold=1.000001,
        feature_mean=[float(value) for value in mean.detach().cpu().tolist()],
        feature_std=[float(value) for value in std.detach().cpu().tolist()],
        max_skip_fraction=None,
        l2=float(l2),
    )
    return classifier, probs


def choose_threshold(
    frame: pd.DataFrame,
    probs: np.ndarray,
    max_train_skip_fraction: float,
    require_train_easy_only: bool,
) -> float:
    work = frame.copy()
    work["skip_prob"] = probs
    candidates = sorted(set(float(value) for value in probs.tolist()))
    strong_keep = work["skip_strong_keep"].astype(bool)
    if strong_keep.any():
        candidates.append(float(work.loc[strong_keep, "skip_prob"].max()) + 1.0e-6)
    candidates.extend([0.0, 0.25, 0.5, 1.000001])

    best_score = None
    best_threshold = 1.000001
    max_skip = int(float(max_train_skip_fraction) * len(work))
    if float(max_train_skip_fraction) > 0.0 and max_skip < 1:
        max_skip = 1
    labels = work["skip_label"].to_numpy() == 1.0
    strong = work["skip_strong_keep"].to_numpy() == 1
    non_easy = work["skip_easy_candidate"].to_numpy() == 0
    for threshold in candidates:
        selected = probs >= float(threshold)
        if int(selected.sum()) > max_skip:
            continue
        if bool((selected & strong).any()):
            continue
        if require_train_easy_only and bool((selected & non_easy).any()):
            continue
        score = (
            int((selected & labels).sum()),
            -int((selected & ~labels).sum()),
            -int(selected.sum()),
            float(threshold),
        )
        if best_score is None or score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def predict_probability(frame: pd.DataFrame, classifier: LinearSkipClassifier) -> np.ndarray:
    x = frame[classifier.feature_names].to_numpy(dtype=np.float32)
    mean = np.asarray(classifier.feature_mean, dtype=np.float32)
    std = np.maximum(np.asarray(classifier.feature_std, dtype=np.float32), 1.0e-6)
    weights = np.asarray(classifier.weights, dtype=np.float32)
    logits = ((x - mean) / std).dot(weights) + float(classifier.bias)
    return 1.0 / (1.0 + np.exp(-logits))


def apply_max_skip_fraction(mask: np.ndarray, scores: np.ndarray, max_skip_fraction: float | None) -> np.ndarray:
    if max_skip_fraction is None:
        return mask
    max_skip = int(float(max_skip_fraction) * len(mask))
    if float(max_skip_fraction) > 0.0 and max_skip < 1:
        max_skip = 1
    if int(mask.sum()) <= max_skip:
        return mask
    selected_indices = np.flatnonzero(mask)
    order = selected_indices[np.argsort(scores[selected_indices])[::-1]]
    keep = set(int(index) for index in order[:max_skip])
    return np.asarray([idx in keep for idx in range(len(mask))], dtype=bool)


def difficulty_bucket_from_base(row: pd.Series) -> str:
    if not bool(row["base_solved"]):
        return "timeout"
    time = float(row["base_time"])
    if time < 10.0:
        return "easy(<10s)"
    if time < 30.0:
        return "medium(10-30s)"
    return "hard(>=30s)"


def method_outcome(row: pd.Series, method_prefix: str, win_eps: float) -> str:
    base_solved = bool(row["base_solved"])
    method_solved = bool(row[f"{method_prefix}_solved"])
    delta = float(row[f"{method_prefix}_time"] - row["base_time"])
    if base_solved and method_solved:
        if delta < -float(win_eps):
            return "faster_both_solved"
        if delta > float(win_eps):
            return "slower_both_solved"
        return "tie_both_solved"
    if not base_solved and method_solved:
        return "recovered_timeout"
    if base_solved and not method_solved:
        return "lost_solution"
    return "both_timeout"


def load_full400_frame(
    full400_policy_path: str,
    full400_actual_path: str,
    feature_names: list[str],
    win_eps: float,
) -> pd.DataFrame:
    feature_source = pd.read_csv(full400_policy_path)
    feature_source = attach_static_feature_columns(feature_source, feature_names)
    feature_columns = ["file_key", "cnf_id", *feature_names]
    for optional in ["selector_use_adapter", "risk_prob", "recovery_prob", "slowdown_prob"]:
        if optional in feature_source.columns:
            feature_columns.append(optional)
    features = feature_source[feature_columns].copy()

    actual_path = Path(full400_actual_path)
    if actual_path.exists():
        actual = pd.read_csv(actual_path)
        frame = actual.merge(features, on="file_key", how="left")
        frame["cal_solved"] = frame["cal_solved"].astype(bool)
        frame["cal_time"] = pd.to_numeric(frame["cal_time"], errors="coerce")
        frame["cal_outcome"] = frame["cal_outcome"].fillna(
            frame.apply(lambda row: method_outcome(row, "cal", win_eps), axis=1)
        )
    else:
        policy = feature_source.copy()
        policy["cal_solved"] = (
            policy["filtered_solved"] if "filtered_solved" in policy.columns else policy["compact_solved"]
        ).astype(bool)
        policy["cal_time"] = (
            policy["filtered_time_post_warmup_est"]
            if "filtered_time_post_warmup_est" in policy.columns
            else policy["compact_time"]
        )
        policy["cal_outcome"] = policy.apply(lambda row: method_outcome(row, "cal", win_eps), axis=1)
        frame = policy

    frame["base_solved"] = frame["base_solved"].astype(bool)
    if "difficulty_bucket" not in frame.columns:
        frame["difficulty_bucket"] = frame.apply(difficulty_bucket_from_base, axis=1)
    return frame


def apply_skip_policy(
    frame: pd.DataFrame,
    classifier: LinearSkipClassifier,
    win_eps: float,
) -> pd.DataFrame:
    policy = attach_static_feature_columns(frame, classifier.feature_names)
    scores = predict_probability(policy, classifier)
    skip = scores >= float(classifier.threshold)
    skip = apply_max_skip_fraction(skip, scores, classifier.max_skip_fraction)
    policy["pre_warmup_skip_score"] = scores
    policy["pre_warmup_skip"] = skip.astype("int64")
    policy["skip_solved"] = np.where(skip, policy["base_solved"], policy["cal_solved"]).astype(bool)
    policy["skip_time"] = np.where(skip, policy["base_time"], policy["cal_time"])
    policy["skip_delta_time"] = policy["skip_time"] - policy["base_time"]
    policy["skip_outcome"] = policy.apply(lambda row: method_outcome(row, "skip", win_eps), axis=1)
    policy["skip_vs_cal_time"] = policy["skip_time"] - policy["cal_time"]
    policy["skipped_recovered_timeout"] = (
        policy["pre_warmup_skip"].astype(bool) & (policy["cal_outcome"] == "recovered_timeout")
    ).astype("int64")
    hard_bucket = policy["difficulty_bucket"].astype(str).str.contains("hard|timeout", regex=True)
    policy["skipped_hard_speedup"] = (
        policy["pre_warmup_skip"].astype(bool)
        & hard_bucket
        & (policy["base_solved"].astype(bool))
        & (policy["cal_solved"].astype(bool))
        & ((policy["cal_time"] + float(win_eps)) < policy["base_time"])
    ).astype("int64")
    return policy


def summary_frame(policy: pd.DataFrame) -> pd.DataFrame:
    recovered = policy["cal_outcome"] == "recovered_timeout"
    hard_speedup = policy["skipped_hard_speedup"].astype(bool)
    skip = policy["pre_warmup_skip"].astype(bool)
    return pd.DataFrame(
        [
            {
                "n": int(len(policy)),
                "skip_count": int(skip.sum()),
                "skip_fraction": float(skip.mean()),
                "base_solved": int(policy["base_solved"].sum()),
                "cal_solved": int(policy["cal_solved"].sum()),
                "skip_solved": int(policy["skip_solved"].sum()),
                "base_mean": float(policy["base_time"].mean()),
                "cal_mean": float(policy["cal_time"].mean()),
                "skip_mean": float(policy["skip_time"].mean()),
                "skip_delta_vs_base": float(policy["skip_time"].mean() - policy["base_time"].mean()),
                "skip_delta_vs_cal": float(policy["skip_time"].mean() - policy["cal_time"].mean()),
                "cal_recovered": int(recovered.sum()),
                "skip_recovered": int((policy["skip_outcome"] == "recovered_timeout").sum()),
                "skipped_recovered": int((skip & recovered).sum()),
                "skipped_hard_speedup": int(hard_speedup.sum()),
            }
        ]
    )


def bucket_summary(policy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for bucket, group in policy.groupby("difficulty_bucket", sort=True):
        skip = group["pre_warmup_skip"].astype(bool)
        rows.append(
            {
                "difficulty_bucket": bucket,
                "n": int(len(group)),
                "skip_count": int(skip.sum()),
                "cal_delta_mean": float((group["cal_time"] - group["base_time"]).mean()),
                "skip_delta_mean": float((group["skip_time"] - group["base_time"]).mean()),
                "skip_vs_cal_mean": float((group["skip_time"] - group["cal_time"]).mean()),
                "skipped_recovered": int(group["skipped_recovered_timeout"].sum()),
                "skipped_hard_speedup": int(group["skipped_hard_speedup"].sum()),
            }
        )
    return pd.DataFrame(rows)


def train_selection_summary(frame: pd.DataFrame, classifier: LinearSkipClassifier, probs: np.ndarray) -> pd.DataFrame:
    selected = probs >= float(classifier.threshold)
    selected = apply_max_skip_fraction(selected, probs, classifier.max_skip_fraction)
    work = frame.copy()
    work["pre_warmup_skip_score"] = probs
    work["pre_warmup_skip"] = selected.astype("int64")
    rows = []
    for key, group in work.groupby("counterfactual_reason", dropna=False):
        rows.append(
            {
                "counterfactual_reason": str(key),
                "n": int(len(group)),
                "selected": int(group["pre_warmup_skip"].sum()),
                "score_mean": float(group["pre_warmup_skip_score"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["selected", "score_mean"], ascending=[False, False])


def model_score(summary: pd.Series) -> tuple:
    if int(summary["skipped_recovered"]) > 0 or int(summary["skipped_hard_speedup"]) > 0:
        return (-10_000, -10_000.0, 0)
    if int(summary["skip_solved"]) < int(summary["cal_solved"]):
        return (-5_000, -10_000.0, 0)
    return (
        1,
        -float(summary["skip_delta_vs_cal"]),
        int(summary["skip_count"]),
    )


def yaml_list(values: list[object], indent: int = 4) -> str:
    prefix = " " * indent
    return "\n".join(f"{prefix}- {repr(value) if isinstance(value, str) else value}" for value in values)


def write_eval_config(path: str, classifier: LinearSkipClassifier, checkpoint: str) -> None:
    config = [
        "# @package _global_",
        "",
        "defaults:",
        "  - config_eval_guided_solver_counterfactual_risk_selector",
        "  - _self_",
        "",
        f"checkpoint: {checkpoint}",
        "save_file: eval_pre_warmup_skip_full400_conservative_classifier.csv",
        "",
        "dataset:",
        '  eval_path: "data/test/3sat/400/*.cnf"',
        "",
        "feedback_refinement:",
        "  pre_warmup_skip:",
        "    enabled: true",
        "    mode: linear_classifier",
        "    feature_names:",
        yaml_list(classifier.feature_names, indent=6),
        "    weights:",
        yaml_list(classifier.weights, indent=6),
        f"    bias: {classifier.bias}",
        f"    threshold: {classifier.threshold}",
        "    feature_mean:",
        yaml_list(classifier.feature_mean, indent=6),
        "    feature_std:",
        yaml_list(classifier.feature_std, indent=6),
    ]
    if classifier.max_skip_fraction is not None:
        config.append(f"    max_skip_fraction: {classifier.max_skip_fraction}")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(config) + "\n")


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
    widths = [max(len(str(row[idx])) for row in rows) for idx in range(len(columns))]

    def fmt(row: list[str]) -> str:
        return "| " + " | ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    separator = "| " + " | ".join("-" * widths[idx] for idx in range(len(columns))) + " |"
    return "\n".join([fmt(columns), separator, *[fmt(row) for row in text.values.tolist()]])


def write_doc(
    path: str,
    classifier: LinearSkipClassifier,
    train_summary: pd.DataFrame,
    offline_summary: pd.DataFrame,
    bucket: pd.DataFrame,
    skipped_cases: pd.DataFrame,
    config_out: str,
    train_policy: str,
    full400_actual: str,
    require_train_easy_only: bool,
) -> None:
    case_columns = [
        "file_key",
        "difficulty_bucket",
        "base_time",
        "cal_time",
        "skip_time",
        "skip_vs_cal_time",
        "cal_outcome",
        "skip_outcome",
        "pre_warmup_skip_score",
    ]
    case_columns = [column for column in case_columns if column in skipped_cases.columns]
    doc = [
        "# Pre-Warmup 极保守 Skip Classifier",
        "",
        "本轮实现的是 `pre-warmup skip gate`：在事件 rollout 之前，只根据第一次 one-shot GNN 的静态变量权重分布判断是否跳过 warmup/refinement。",
        "目标不是大幅多跳，而是在不牺牲 `recovered_timeout` 和 `hard_speedup` 的前提下，跳过极少数几乎只会产生 easy slowdown 的样本。",
        "",
        "## 训练设置",
        "",
        f"- 训练数据：`{train_policy}`",
        f"- Full400 离线对照：`{full400_actual}`",
        f"- 生成评估配置：`{config_out}`",
        f"- L2：`{classifier.l2}`",
        f"- threshold：`{classifier.threshold:.6f}`",
        f"- max skip fraction：`{classifier.max_skip_fraction}`",
        "- 正例：`base_bucket=easy` 且 `counterfactual_reason` 为 `easy_slowdown` 或 `lost_solution`。",
        "- 强负例：`recovered_timeout` 与 `hard_speedup`，阈值选择阶段要求训练集零误跳。",
        "- 额外约束："
        + ("训练集中被 skip 的样本必须全部来自 easy bucket。" if require_train_easy_only else "允许训练集中少量非 easy 的低风险样本被 skip，但仍要求强负例零误跳。"),
        "",
        "## 静态特征",
        "",
        "- " + "\n- ".join(classifier.feature_names),
        "",
        "## 训练集选择分布",
        "",
        markdown_table(train_summary),
        "",
        "## Full400 离线模拟",
        "",
        markdown_table(offline_summary),
        "",
        "## Bucket 离线结果",
        "",
        markdown_table(bucket),
        "",
        "## 离线被 Skip 的样本",
        "",
        markdown_table(skipped_cases[case_columns].sort_values("pre_warmup_skip_score", ascending=False)),
        "",
        "## 正式评估命令",
        "",
        "```bash",
        f"python3 evaluate_guided_solver.py --config-name {Path(config_out).stem}",
        "```",
        "",
        "注意：离线模拟用既有 full400 结果估算 skip 后时间；正式 wall-clock 仍需要运行上面的配置确认。",
        "",
    ]
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(doc) + "\n")


def main() -> None:
    args = parse_args()
    feature_names = parse_csv_list(args.features)
    train = pd.read_csv(args.train_policy)
    train = attach_static_feature_columns(add_skip_labels(train), feature_names)
    full400 = load_full400_frame(
        args.full400_policy,
        args.full400_actual,
        feature_names=feature_names,
        win_eps=args.win_eps,
    )

    candidates = []
    for l2 in parse_float_grid(args.l2_grid):
        classifier, train_probs = fit_classifier(
            train,
            feature_names=feature_names,
            epochs=args.epochs,
            lr=args.lr,
            l2=l2,
            seed=args.seed,
        )
        classifier.threshold = choose_threshold(
            train,
            train_probs,
            max_train_skip_fraction=args.max_train_skip_fraction,
            require_train_easy_only=args.require_train_easy_only,
        )
        classifier.max_skip_fraction = float(args.max_eval_skip_fraction)
        policy = apply_skip_policy(full400, classifier, win_eps=args.win_eps)
        summary = summary_frame(policy).iloc[0]
        candidates.append((model_score(summary), classifier, train_probs, policy, summary))

    candidates.sort(key=lambda item: item[0], reverse=True)
    _, classifier, train_probs, policy, _ = candidates[0]
    train["pre_warmup_skip_score"] = train_probs
    train["pre_warmup_skip"] = (
        apply_max_skip_fraction(
            train_probs >= float(classifier.threshold),
            train_probs,
            classifier.max_skip_fraction,
        )
    ).astype("int64")

    analysis_dir = Path(args.analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    train_path = analysis_dir / "pre_warmup_skip_classifier_training_frame.csv"
    policy_path = analysis_dir / "pre_warmup_skip_classifier_full400_offline_policy.csv"
    summary_path = analysis_dir / "pre_warmup_skip_classifier_full400_offline_summary.csv"
    bucket_path = analysis_dir / "pre_warmup_skip_classifier_full400_bucket_summary.csv"
    skipped_path = analysis_dir / "pre_warmup_skip_classifier_full400_skipped.csv"
    candidate_path = analysis_dir / "pre_warmup_skip_classifier_candidates.csv"

    summaries = []
    for score, item_classifier, _, item_policy, item_summary in candidates:
        row = item_summary.to_dict()
        row.update(
            {
                "l2": item_classifier.l2,
                "threshold": item_classifier.threshold,
                "score_tuple": str(score),
            }
        )
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(candidate_path, index=False)

    summary = summary_frame(policy)
    bucket = bucket_summary(policy)
    train_summary = train_selection_summary(train, classifier, train_probs)
    skipped_cases = policy[policy["pre_warmup_skip"].astype(bool)].copy()

    train.to_csv(train_path, index=False)
    policy.to_csv(policy_path, index=False)
    summary.to_csv(summary_path, index=False)
    bucket.to_csv(bucket_path, index=False)
    skipped_cases.to_csv(skipped_path, index=False)
    write_eval_config(args.config_out, classifier=classifier, checkpoint=args.checkpoint)
    write_doc(
        args.doc_path,
        classifier=classifier,
        train_summary=train_summary,
        offline_summary=summary,
        bucket=bucket,
        skipped_cases=skipped_cases,
        config_out=args.config_out,
        train_policy=args.train_policy,
        full400_actual=args.full400_actual,
        require_train_easy_only=args.require_train_easy_only,
    )

    print(f"selected l2: {classifier.l2}")
    print(f"threshold: {classifier.threshold:.6f}")
    print(f"wrote {args.config_out}")
    print(f"wrote {args.doc_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
