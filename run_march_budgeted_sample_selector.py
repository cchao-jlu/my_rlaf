from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch_geometric.loader import DataLoader

from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import sample_var_params
from src.solving.solver import solve_cnf


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "data/benchmark_transition_band"
SUBSET_ROOT = ROOT / "data/benchmark_march_budgeted_sample_selector"
WORK_DIR = ROOT / "runs/analysis/benchmark_march_budgeted_sample_selector"
RAW_CSV = WORK_DIR / "budgeted_selector_raw.csv"
CANDIDATE_CSV = WORK_DIR / "budgeted_selector_candidates.csv"
SUMMARY_CSV = WORK_DIR / "budgeted_selector_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_budgeted_sample_selector.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}

POLICIES: dict[str, tuple[str, bool]] = {
    "low_log_prob": ("log_prob", True),
    "high_weight_std": ("weight_std", False),
    "high_phase_mode_match": ("phase_mode_match", False),
    "high_log_weight_abs_mean": ("log_weight_abs_mean", False),
    "combined_low_logprob_high_weightstd": ("combined_rank_logprob_weightstd", True),
}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_instances(raw: str) -> list[tuple[int, str]]:
    instances = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"Expected size:file_key instance spec, got {part!r}")
        size_raw, file_key = part.split(":", 1)
        instances.append((int(size_raw), file_key.strip()))
    if not instances:
        raise ValueError("At least one instance is required.")
    return instances


def prepare_instance(size: int, file_key: str) -> Path:
    source = SOURCE_ROOT / "3sat" / str(size) / file_key
    if not source.exists():
        raise FileNotFoundError(source)
    target_dir = SUBSET_ROOT / "3sat" / str(size)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file_key
    if target.exists() or target.is_symlink():
        return target
    try:
        target.symlink_to(source.resolve())
    except OSError:
        shutil.copy2(source, target)
    return target


def sample_one(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    file_key: str,
    sample_seed: int,
    num_samples: int,
    device: str,
):
    set_seed(sample_seed)
    path = prepare_instance(size, file_key)
    dataset = DimacsCNFDataset(str(path.relative_to(ROOT)), transform=transform, lazy=True)
    loader = DataLoader(dataset=dataset, batch_size=1, num_workers=0, shuffle=False)
    data = sample_var_params(
        model=model,
        loader=loader,
        device=device,
        use_mode=False,
        num_samples=num_samples,
        scale_sigma=float(model_cfg.scale_sigma),
        add_timing=True,
    )[0]
    return dataset, data


def sample_feature_frame(data, size: int, file_key: str, sample_seed: int) -> pd.DataFrame:
    var_params = data["var"].var_params
    phase = var_params[:, :, 0]
    weight = var_params[:, :, 1]
    log_weight = torch.log(weight.clamp_min(1.0e-12))
    y_var = data["var"].y_var_ref
    y_rho = y_var[:, 0]
    y_mu = y_var[:, 1]
    y_sigma = y_var[:, 2] if y_var.shape[1] > 2 else torch.zeros_like(y_mu)
    p_phase = torch.sigmoid(y_rho)
    phase_mode = (p_phase >= 0.5).float()

    rows = []
    for sample_id in range(phase.shape[1]):
        sample_phase = phase[:, sample_id]
        sample_weight = weight[:, sample_id]
        sample_log_weight = log_weight[:, sample_id]
        phase_mode_match = (sample_phase == phase_mode).float()
        rows.append(
            {
                "size": int(size),
                "file_key": file_key,
                "sample_seed": int(sample_seed),
                "sample_id": int(sample_id),
                "log_prob": float(data.log_prob[sample_id]),
                "phase_mean": float(sample_phase.mean()),
                "phase_mode_match": float(phase_mode_match.mean()),
                "weight_mean": float(sample_weight.mean()),
                "weight_std": float(sample_weight.std(unbiased=False)),
                "weight_min": float(sample_weight.min()),
                "weight_max": float(sample_weight.max()),
                "weight_p10": float(torch.quantile(sample_weight, 0.10)),
                "weight_p50": float(torch.quantile(sample_weight, 0.50)),
                "weight_p90": float(torch.quantile(sample_weight, 0.90)),
                "log_weight_mean": float(sample_log_weight.mean()),
                "log_weight_std": float(sample_log_weight.std(unbiased=False)),
                "log_weight_abs_mean": float(sample_log_weight.abs().mean()),
                "model_rho_abs_mean": float(y_rho.abs().mean()),
                "model_mu_mean": float(y_mu.mean()),
                "model_mu_std": float(y_mu.std(unbiased=False)),
                "model_sigma_mean": float(y_sigma.mean()),
            }
        )
    frame = pd.DataFrame(rows)
    frame["rank_low_log_prob"] = frame["log_prob"].rank(method="first", ascending=True)
    frame["rank_high_weight_std"] = frame["weight_std"].rank(method="first", ascending=False)
    frame["combined_rank_logprob_weightstd"] = frame["rank_low_log_prob"] + frame["rank_high_weight_std"]
    return frame


def rank_candidates(features: pd.DataFrame, policy: str, top_k: int) -> pd.DataFrame:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}; expected one of {sorted(POLICIES)}")
    metric, ascending = POLICIES[policy]
    ranked = features.sort_values(metric, ascending=ascending).reset_index(drop=True)
    ranked["selector_policy"] = policy
    ranked["selector_metric"] = metric
    ranked["selector_ascending"] = bool(ascending)
    ranked["selector_rank"] = np.arange(1, len(ranked) + 1)
    ranked["selected"] = ranked["selector_rank"] <= int(top_k)
    return ranked


def run_budgeted_group(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    file_key: str,
    sample_seed: int,
    solver_seed: int,
    num_samples: int,
    top_k: int,
    policy: str,
    device: str,
    cpu_lim: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    dataset, data = sample_one(
        model=model,
        transform=transform,
        model_cfg=model_cfg,
        size=size,
        file_key=file_key,
        sample_seed=sample_seed,
        num_samples=num_samples,
        device=device,
    )
    features = sample_feature_frame(data, size=size, file_key=file_key, sample_seed=sample_seed)
    ranked = rank_candidates(features, policy=policy, top_k=top_k)

    cnf = dataset.get_cnf(int(data.cnf_id.item()))
    var_params_all = data["var"].var_params.numpy()
    raw_rows = []
    stop_cpu = 0.0
    solved_any = False
    first_solved_rank = -1
    attempts_used = 0
    for row in ranked[ranked["selected"]].itertuples(index=False):
        attempts_used += 1
        sample_id = int(row.sample_id)
        stats = solve_cnf(
            cnf.clauses,
            var_params_all[:, sample_id, :],
            seed=solver_seed,
            solver="march",
            **{"cpu-lim": cpu_lim},
        )
        cpu_time = float(stats.get("CPU time", cpu_lim))
        solved_returned = str(stats.get("Result", "")) in SOLVED
        solved_strict_limit = bool(solved_returned and cpu_time <= cpu_lim)
        stop_cpu += min(cpu_time, cpu_lim)
        raw_row = {
            "size": int(size),
            "file_key": file_key,
            "sample_seed": int(sample_seed),
            "solver_seed": int(solver_seed),
            "selector_policy": policy,
            "top_k": int(top_k),
            "num_samples_generated": int(num_samples),
            "sample_id": sample_id,
            "selector_rank": int(row.selector_rank),
            "Result": stats.get("Result", "UNKNOWN"),
            "CPU time": cpu_time,
            "decisions": stats.get("decisions", np.nan),
            "external_timeout": bool(stats.get("external_timeout", False)),
            "solved_returned": solved_returned,
            "solved_strict60": solved_strict_limit,
            "solved_strict_limit": solved_strict_limit,
            "cpu_lim": float(cpu_lim),
            "stop_cpu_capped_after_attempt": float(stop_cpu),
        }
        raw_rows.append(raw_row)
        if solved_strict_limit:
            solved_any = True
            first_solved_rank = int(row.selector_rank)
            break

    summary = {
        "size": int(size),
        "file_key": file_key,
        "sample_seed": int(sample_seed),
        "solver_seed": int(solver_seed),
        "selector_policy": policy,
        "top_k": int(top_k),
        "num_samples_generated": int(num_samples),
        "attempts_used": int(attempts_used),
        "solved_any_strict60": bool(solved_any),
        "first_solved_rank": int(first_solved_rank),
        "stop_cpu_capped": float(stop_cpu),
    }
    return pd.DataFrame(raw_rows), ranked, summary


def summarize(groups: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (policy, top_k), group in groups.groupby(["selector_policy", "top_k"], sort=True):
        rows.append(
            {
                "selector_policy": policy,
                "top_k": int(top_k),
                "groups": int(len(group)),
                "instances": int(group[["size", "file_key"]].drop_duplicates().shape[0]),
                "sample_seeds": int(group["sample_seed"].nunique()),
                "solved_groups": int(group["solved_any_strict60"].sum()),
                "solved_instances_any_seed": int(group.groupby(["size", "file_key"])["solved_any_strict60"].any().sum()),
                "mean_attempts_used": float(group["attempts_used"].mean()),
                "mean_stop_cpu_capped": float(group["stop_cpu_capped"].mean()),
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(summary: pd.DataFrame, group_summary: pd.DataFrame, instances: list[tuple[int, str]], sample_seeds: list[int]) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    instance_frame = pd.DataFrame([{"size": size, "file_key": file_key} for size, file_key in instances])
    lines = [
        "# March Budgeted Sample Selector Gate",
        "",
        "Scope: real fixed-budget gate for sampled March guidance. The runner",
        "generates stochastic guidances, ranks them using a cheap pre-solver",
        "metric, solves only top-k candidates, and stops after the first strict-60",
        "solve. This is not an oracle sample selection result.",
        "",
        f"Sample seeds: {sample_seeds}.",
        "",
        "## Instances",
        "",
        *markdown_table(instance_frame, ["size", "file_key"]),
        "",
        "## Aggregate",
        "",
        *markdown_table(
            summary,
            [
                "selector_policy",
                "top_k",
                "groups",
                "instances",
                "sample_seeds",
                "solved_groups",
                "solved_instances_any_seed",
                "mean_attempts_used",
                "mean_stop_cpu_capped",
            ],
        ),
        "",
        "## Per Group",
        "",
        *markdown_table(
            group_summary,
            [
                "size",
                "file_key",
                "sample_seed",
                "selector_policy",
                "top_k",
                "attempts_used",
                "solved_any_strict60",
                "first_solved_rank",
                "stop_cpu_capped",
            ],
        ),
        "",
        "Artifacts:",
        "",
        "```text",
        str(RAW_CSV.relative_to(ROOT)),
        str(CANDIDATE_CSV.relative_to(ROOT)),
        str(SUMMARY_CSV.relative_to(ROOT)),
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a real budgeted selector for sampled March guidance.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--instances", default="410:3sat_2.cnf,440:3sat_8.cnf")
    parser.add_argument("--sample-seeds", default="1729,1730,1731")
    parser.add_argument("--solver-seed", type=int, default=1729)
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--policy", default="combined_low_logprob_high_weightstd", choices=sorted(POLICIES))
    parser.add_argument("--cpu-lim", type=float, default=60.0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    instances = parse_instances(args.instances)
    sample_seeds = parse_seeds(args.sample_seeds)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)
    raw_frames = []
    candidate_frames = []
    group_rows = []
    for size, file_key in instances:
        for sample_seed in sample_seeds:
            raw, candidates, group = run_budgeted_group(
                model=model,
                transform=transform,
                model_cfg=model_cfg,
                size=size,
                file_key=file_key,
                sample_seed=sample_seed,
                solver_seed=args.solver_seed,
                num_samples=args.num_samples,
                top_k=args.top_k,
                policy=args.policy,
                device=args.device,
                cpu_lim=args.cpu_lim,
            )
            raw_frames.append(raw)
            candidate_frames.append(candidates)
            group_rows.append(group)

    raw_all = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    candidates_all = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()
    group_summary = pd.DataFrame(group_rows)
    aggregate = summarize(group_summary)

    raw_all.to_csv(RAW_CSV, index=False)
    candidates_all.to_csv(CANDIDATE_CSV, index=False)
    group_summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(aggregate, group_summary, instances, sample_seeds)

    print(aggregate.to_string(index=False))
    print(group_summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
