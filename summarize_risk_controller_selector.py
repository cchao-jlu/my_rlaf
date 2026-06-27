from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch_geometric.loader import DataLoader

from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch
from src.training.adapter_selector import choose_threshold_for_time, fit_linear_selector, selected_time
from train_adapter_selector import extract_selector_features


CHECKPOINT = Path("runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/best.pt")
BASE_PATH = "runs/GNN_Glucose_3SAT_V1/eval_oneshot_{size}_optimized_events_gated.csv"
ADAPTER_PATH = (
    "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
    "eval_trace_adapter_rho_gate_{size}_optimized_events_gated.csv"
)
OUT_DIR = Path("runs/analysis")
DOC_PATH = Path("docs/risk_controller_selector_results.md")
FEATURE_CACHE = OUT_DIR / "risk_controller_micro_features_300350.csv"
SIZES = [300, 350]
SEEDS = list(range(1729, 1779))
MICRO_FEATURES = [
    "event_entropy_norm",
    "event_top05_mass",
    "event_top10_mass",
    "rho_event_corr",
    "rho_event_top10_overlap",
]
ALL_FEATURES = ["base_rho_mean", "num_vars_log", *MICRO_FEATURES]


@dataclass
class LinearSelector:
    feature_names: list[str]
    weights: list[float]
    bias: float
    threshold: float
    feature_mean: list[float]
    feature_std: list[float]


def size_from_dataset(value: str) -> int:
    match = re.search(r"/(\d+)/", value)
    if match is None:
        raise ValueError(f"Cannot infer size from selector_dataset={value!r}")
    return int(match.group(1))


def feature_cache_is_valid(path: Path) -> bool:
    if not path.exists():
        return False
    columns = set(pd.read_csv(path, nrows=1).columns)
    required = {"size", "cnf_id", *ALL_FEATURES}
    return required.issubset(columns)


def build_feature_cache() -> pd.DataFrame:
    model, transform, model_cfg = load_checkpoint(str(CHECKPOINT), var_output=True)
    if not getattr(model, "event_adapter_enabled", False):
        raise ValueError("Risk-controller feature extraction requires an event-adapter checkpoint")
    model.eval()

    frames = []
    for size in SIZES:
        dataset_path = f"data/test/3sat/{size}/*.cnf"
        dataset = DimacsCNFDataset(path=dataset_path, transform=transform, lazy=True)
        loader = DataLoader(dataset=dataset, batch_size=20, num_workers=0, shuffle=False)
        warmup_data = sample_var_params(
            model=model,
            loader=loader,
            device="cpu",
            use_mode=True,
            num_samples=1,
            scale_sigma=model_cfg.scale_sigma,
            add_timing=True,
            cache_var_features=True,
        )
        warmup_params = apply_rollout_budget(
            dict(model_cfg.solver.params),
            budget_type="conflicts",
            cpu_lim=10.0,
            conflicts=500,
        )
        warmup_params["collect-events"] = True
        warmup_stats = compute_solver_stats(
            dataset=dataset,
            data_list=warmup_data,
            num_workers=8,
            solver=model_cfg.solver.solver,
            **warmup_params,
        )
        refined_graphs = attach_var_event_state_batch(
            warmup_data,
            warmup_stats,
            var_state_dim=model.var_state_dim,
            momentum=0.5,
            feature_mode="enhanced",
        )
        feature_loader = DataLoader(dataset=refined_graphs, batch_size=20, num_workers=0, shuffle=False)
        frame = extract_selector_features(model, feature_loader, ALL_FEATURES)
        frame["size"] = size
        frame["selector_dataset"] = dataset_path
        frames.append(frame)
    feature_frame = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feature_frame.to_csv(FEATURE_CACHE, index=False)
    return feature_frame


def load_features() -> pd.DataFrame:
    if feature_cache_is_valid(FEATURE_CACHE):
        return pd.read_csv(FEATURE_CACHE)
    return build_feature_cache()


def load_frame() -> pd.DataFrame:
    features = load_features()
    features = features[["selector_dataset", "cnf_id", "size", *ALL_FEATURES]].copy()
    if "num_vars_log" not in features or features["num_vars_log"].isna().any():
        features["num_vars_log"] = np.log1p(features["size"].astype(float))

    frames = []
    for size in SIZES:
        base = pd.read_csv(BASE_PATH.format(size=size))[
            ["cnf_id", "time", "Result", "conflicts", "decisions"]
        ].rename(
            columns={
                "time": "base_time",
                "Result": "base_result",
                "conflicts": "base_conflicts",
                "decisions": "base_decisions",
            }
        )
        adapter = pd.read_csv(ADAPTER_PATH.format(size=size))[
            ["cnf_id", "time", "Result", "conflicts", "decisions"]
        ].rename(
            columns={
                "time": "adapter_time",
                "Result": "adapter_result",
                "conflicts": "adapter_conflicts",
                "decisions": "adapter_decisions",
            }
        )
        current = (
            features[features["size"] == size]
            .merge(base, on="cnf_id", how="inner")
            .merge(adapter, on="cnf_id", how="inner")
        )
        current["base_solved"] = current["base_result"] != "INDETERMINATE"
        current["adapter_solved"] = current["adapter_result"] != "INDETERMINATE"
        current["gain"] = current["base_time"] - current["adapter_time"]
        current["base_bucket"] = current.apply(base_bucket, axis=1)
        current["time_label"] = (current["gain"] > 0.0).astype("float32")
        current["risk_label"] = current.apply(risk_label, axis=1).astype("float32")
        current["risk_weight"] = current.apply(risk_weight, axis=1).astype("float32")
        frames.append(current)
    return pd.concat(frames, ignore_index=True)


def base_bucket(row: pd.Series) -> str:
    if not bool(row["base_solved"]):
        return "timeout"
    time = float(row["base_time"])
    if time < 10.0:
        return "easy"
    if time < 30.0:
        return "medium"
    return "hard"


def risk_label(row: pd.Series) -> float:
    base_solved = bool(row["base_solved"])
    adapter_solved = bool(row["adapter_solved"])
    gain = float(row["gain"])
    bucket = row["base_bucket"]
    if not base_solved and adapter_solved:
        return 1.0
    if base_solved and not adapter_solved:
        return 0.0
    if not base_solved and not adapter_solved:
        return 0.0
    if bucket == "easy":
        return 1.0 if gain > 2.0 else 0.0
    if bucket == "medium":
        return 1.0 if gain > 0.5 else 0.0
    return 1.0 if gain > 0.1 else 0.0


def risk_weight(row: pd.Series) -> float:
    base_solved = bool(row["base_solved"])
    adapter_solved = bool(row["adapter_solved"])
    bucket = row["base_bucket"]
    if base_solved and not adapter_solved:
        return 10.0
    if not base_solved and adapter_solved:
        return 6.0
    if bucket == "easy":
        return 3.0
    if bucket == "hard":
        return 2.5
    if bucket == "timeout":
        return 2.0
    return 1.5


def fit_weighted_linear_selector(
    features: torch.Tensor,
    labels: torch.Tensor,
    sample_weights: torch.Tensor,
    feature_names: list[str],
    epochs: int = 1000,
    lr: float = 0.05,
    l2: float = 1.0e-3,
) -> tuple[LinearSelector, torch.Tensor]:
    features = features.to(dtype=torch.float32)
    labels = labels.to(dtype=torch.float32).view(-1)
    sample_weights = sample_weights.to(dtype=torch.float32).view(-1)
    mean = features.mean(dim=0)
    std = features.std(dim=0, unbiased=False).clamp_min(1.0e-6)
    x = (features - mean) / std
    weights = torch.zeros(features.shape[1], dtype=torch.float32, requires_grad=True)
    bias = torch.zeros((), dtype=torch.float32, requires_grad=True)
    optimizer = torch.optim.AdamW([weights, bias], lr=lr, weight_decay=0.0)

    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        logits = x.matmul(weights) + bias
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits,
            labels,
            reduction="none",
        )
        loss = (loss * sample_weights).sum() / sample_weights.sum().clamp_min(1.0)
        if l2 > 0:
            loss = loss + float(l2) * weights.pow(2).mean()
        loss.backward()
        optimizer.step()

    with torch.no_grad():
        probs = torch.sigmoid(x.matmul(weights) + bias)
    selector = LinearSelector(
        feature_names=list(feature_names),
        weights=[float(value) for value in weights.detach().tolist()],
        bias=float(bias.detach().item()),
        threshold=0.5,
        feature_mean=[float(value) for value in mean.tolist()],
        feature_std=[float(value) for value in std.tolist()],
    )
    return selector, probs


def selector_prob(selector, values: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor(selector.feature_mean, dtype=torch.float32)
    std = torch.tensor(selector.feature_std, dtype=torch.float32).clamp_min(1.0e-6)
    weights = torch.tensor(selector.weights, dtype=torch.float32)
    bias = torch.tensor(selector.bias, dtype=torch.float32)
    x = (values - mean) / std
    return torch.sigmoid(x.matmul(weights) + bias)


def apply_probs(frame: pd.DataFrame, probs: torch.Tensor, threshold: float) -> pd.DataFrame:
    result = frame.copy()
    result["selector_prob"] = probs.detach().cpu().numpy()
    result["selector_use_adapter"] = (result["selector_prob"] >= float(threshold)).astype("int64")
    use_adapter = result["selector_use_adapter"].astype(bool)
    result["selector_time"] = np.where(use_adapter, result["adapter_time"], result["base_time"])
    result["selector_solved"] = np.where(use_adapter, result["adapter_solved"], result["base_solved"])
    result["selector_lost_solution"] = (
        result["base_solved"] & use_adapter & ~result["adapter_solved"]
    )
    result["selector_recovered_timeout"] = (
        ~result["base_solved"] & use_adapter & result["adapter_solved"]
    )
    return result


def choose_risk_threshold(frame: pd.DataFrame, probs: torch.Tensor) -> tuple[float, dict[str, float]]:
    candidates = sorted(set(float(value) for value in probs.detach().cpu().tolist()) | {0.0, 0.5, 1.0, 1.000001})
    best_threshold = 1.000001
    best_tuple = None
    best_metrics = {}
    for threshold in candidates:
        selected = apply_probs(frame, probs, threshold)
        solved = int(selected["selector_solved"].sum())
        lost = int(selected["selector_lost_solution"].sum())
        recovered = int(selected["selector_recovered_timeout"].sum())
        mean_time = float(selected["selector_time"].mean())
        selected_fraction = float(selected["selector_use_adapter"].mean())
        score = (solved, -lost, -mean_time)
        if best_tuple is None or score > best_tuple:
            best_tuple = score
            best_threshold = threshold
            best_metrics = {
                "train_selected_solved": float(solved),
                "train_lost_solution": float(lost),
                "train_recovered_timeout": float(recovered),
                "train_mean_time": mean_time,
                "train_selected_fraction": selected_fraction,
            }
    return best_threshold, best_metrics


def summarize_policy(
    seed: int,
    feature_set: str,
    policy_name: str,
    threshold: float,
    train_metrics: dict[str, float],
    heldout: pd.DataFrame,
    probs: torch.Tensor,
) -> list[dict[str, object]]:
    selected = apply_probs(heldout, probs, threshold)
    rows = []
    for heldout_name, subset in [("300+350", selected)] + [
        (str(size), selected[selected["size"] == size]) for size in SIZES
    ]:
        base_solved = int(subset["base_solved"].sum())
        adapter_solved = int(subset["adapter_solved"].sum())
        selector_solved = int(subset["selector_solved"].sum())
        base_mean = float(subset["base_time"].mean())
        adapter_mean = float(subset["adapter_time"].mean())
        selector_mean = float(subset["selector_time"].mean())
        rows.append(
            {
                "seed": seed,
                "feature_set": feature_set,
                "policy": policy_name,
                "heldout": heldout_name,
                "n": int(len(subset)),
                "threshold": float(threshold),
                "selected_fraction": float(subset["selector_use_adapter"].mean()),
                "base_solved": base_solved,
                "fixed_rho_solved": adapter_solved,
                "selector_solved": selector_solved,
                "selector_delta_solved_vs_base": selector_solved - base_solved,
                "selector_delta_solved_vs_fixed_rho": selector_solved - adapter_solved,
                "lost_solution": int(subset["selector_lost_solution"].sum()),
                "recovered_timeout": int(subset["selector_recovered_timeout"].sum()),
                "base_mean": base_mean,
                "fixed_rho_mean": adapter_mean,
                "selector_mean": selector_mean,
                "selector_delta_vs_base": selector_mean - base_mean,
                "selector_delta_vs_fixed_rho": selector_mean - adapter_mean,
                **train_metrics,
            }
        )
    return rows


def split_rows(frame: pd.DataFrame, feature_names: list[str], seeds: list[int]) -> list[dict[str, object]]:
    rows = []
    feature_set = "+".join(feature_names)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        train_indices = []
        heldout_indices = []
        for size in SIZES:
            size_indices = frame.index[frame["size"] == size].to_numpy()
            chosen = rng.choice(size_indices, size=100, replace=False)
            train_indices.extend(chosen.tolist())
            heldout_indices.extend(sorted(set(size_indices.tolist()).difference(chosen.tolist())))

        train = frame.loc[train_indices].copy()
        heldout = frame.loc[heldout_indices].copy()
        train_features = torch.tensor(train[feature_names].to_numpy(), dtype=torch.float32)
        heldout_features = torch.tensor(heldout[feature_names].to_numpy(), dtype=torch.float32)

        time_selector, train_time_probs = fit_linear_selector(
            train_features,
            torch.tensor(train["time_label"].to_numpy(), dtype=torch.float32),
            feature_names=feature_names,
            epochs=1000,
            lr=0.05,
            l2=1.0e-3,
        )
        train_base = torch.tensor(train["base_time"].to_numpy(), dtype=torch.float32)
        train_adapter = torch.tensor(train["adapter_time"].to_numpy(), dtype=torch.float32)
        time_threshold, train_time = choose_threshold_for_time(
            train_base,
            train_adapter,
            train_time_probs,
        )
        time_probs = selector_prob(time_selector, heldout_features)
        rows.extend(
            summarize_policy(
                seed=seed,
                feature_set=feature_set,
                policy_name="time_selector",
                threshold=time_threshold,
                train_metrics={"train_mean_time": float(train_time)},
                heldout=heldout,
                probs=time_probs,
            )
        )

        risk_selector, train_risk_probs = fit_weighted_linear_selector(
            train_features,
            torch.tensor(train["risk_label"].to_numpy(), dtype=torch.float32),
            torch.tensor(train["risk_weight"].to_numpy(), dtype=torch.float32),
            feature_names=feature_names,
            epochs=1000,
            lr=0.05,
            l2=1.0e-3,
        )
        risk_threshold, train_metrics = choose_risk_threshold(train, train_risk_probs)
        risk_probs = selector_prob(risk_selector, heldout_features)
        rows.extend(
            summarize_policy(
                seed=seed,
                feature_set=feature_set,
                policy_name="risk_controller",
                threshold=risk_threshold,
                train_metrics=train_metrics,
                heldout=heldout,
                probs=risk_probs,
            )
        )
    return rows


def aggregate(result: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["feature_set", "policy", "heldout"]
    for keys, group in result.groupby(group_cols, sort=False):
        row = dict(zip(group_cols, keys))
        for column in [
            "selected_fraction",
            "selector_delta_solved_vs_base",
            "selector_delta_solved_vs_fixed_rho",
            "lost_solution",
            "recovered_timeout",
            "selector_delta_vs_base",
            "selector_delta_vs_fixed_rho",
        ]:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_ci_low"] = float(group[column].quantile(0.025))
            row[f"{column}_ci_high"] = float(group[column].quantile(0.975))
        row["beats_base_solved_rate"] = float((group["selector_delta_solved_vs_base"] > 0).mean())
        row["beats_fixed_rho_solved_rate"] = float(
            (group["selector_delta_solved_vs_fixed_rho"] > 0).mean()
        )
        row["beats_base_time_rate"] = float((group["selector_delta_vs_base"] < 0.0).mean())
        row["beats_fixed_rho_time_rate"] = float(
            (group["selector_delta_vs_fixed_rho"] < 0.0).mean()
        )
        rows.append(row)
    return pd.DataFrame(rows)


def fmt(value: object) -> str:
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.4f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(fmt(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def write_doc(summary: pd.DataFrame) -> None:
    columns = [
        "feature_set",
        "policy",
        "heldout",
        "selected_fraction_mean",
        "selector_delta_solved_vs_base_mean",
        "selector_delta_solved_vs_fixed_rho_mean",
        "lost_solution_mean",
        "recovered_timeout_mean",
        "selector_delta_vs_base_mean",
        "selector_delta_vs_fixed_rho_mean",
        "beats_fixed_rho_time_rate",
    ]
    doc = [
        "# Risk-Controller Selector Results",
        "",
        "This is an offline repeated-split check for a risk-controller selector.",
        "It trains on 100 instances from each of 3SAT-300 and 3SAT-350, then",
        "evaluates on the held-out halves. The script extracts one conflict-budgeted",
        "warmup trace feature cache, then reuses clean one-shot/fixed-rho CSVs for",
        "offline repeated-split evaluation.",
        "",
        "Micro trace features:",
        "",
        "- `event_entropy_norm`",
        "- `event_top05_mass`",
        "- `event_top10_mass`",
        "- `rho_event_corr`",
        "- `rho_event_top10_overlap`",
        "",
        "Policies:",
        "",
        "- `time_selector`: previous target, choose adapter when it predicts lower runtime.",
        "- `risk_controller`: weighted labels plus a threshold that maximizes solved",
        "  count first, minimizes lost solved instances second, and mean time third.",
        "",
        "## Summary",
        "",
        markdown_table(summary[columns], columns),
        "",
        "## Reading",
        "",
        "- Adding the five micro trace features does not improve the repeated-split",
        "  selector. The best safety/time tradeoff still comes from the simpler",
        "  `base_rho_mean` risk controller.",
        "- The micro-feature risk controller becomes too conservative: it reduces",
        "  selection rate but also suppresses timeout recovery, so solved-count",
        "  protection gets worse instead of better.",
        "- The risk-controller target should be judged by solved-count protection",
        "  first, then runtime. A lower selected fraction is acceptable only if it",
        "  reduces lost solved instances without wiping out timeout recovery.",
        "- If the micro trace features do not improve held-out stability, the",
        "  bottleneck is likely warmup evidence quality or trace-label design rather",
        "  than the selector objective itself.",
    ]
    DOC_PATH.write_text("\n".join(doc) + "\n")


def main() -> None:
    frame = load_frame()
    rows = []
    for feature_names in [
        ["base_rho_mean"],
        ["base_rho_mean", "num_vars_log"],
        ["base_rho_mean", *MICRO_FEATURES],
        ["base_rho_mean", "num_vars_log", *MICRO_FEATURES],
    ]:
        rows.extend(split_rows(frame, feature_names, SEEDS))
    result = pd.DataFrame(rows)
    summary = aggregate(result)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_DIR / "risk_controller_selector_repeated_splits.csv", index=False)
    summary.to_csv(OUT_DIR / "risk_controller_selector_summary.csv", index=False)
    write_doc(summary)
    print(f"wrote {OUT_DIR / 'risk_controller_selector_repeated_splits.csv'}")
    print(f"wrote {OUT_DIR / 'risk_controller_selector_summary.csv'}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
