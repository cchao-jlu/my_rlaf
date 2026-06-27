from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from run_march_budgeted_sample_selector import (
    ROOT,
    SOLVED,
    markdown_table,
    parse_instances,
    parse_seeds,
    sample_feature_frame,
    sample_one,
)
from src.model.model import load_checkpoint
from src.solving.solver import solve_cnf


WORK_DIR = ROOT / "runs/analysis/benchmark_march_early_trace_selector"
PROBE_CSV = WORK_DIR / "early_trace_probe_raw.csv"
RAW_CSV = WORK_DIR / "early_trace_selector_raw.csv"
CANDIDATE_CSV = WORK_DIR / "early_trace_selector_candidates.csv"
SUMMARY_CSV = WORK_DIR / "early_trace_selector_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_early_trace_selector.md"
GROUP_DIR = WORK_DIR / "groups"


POLICIES = {
    "probe_solved_then_high_decisions": ["probe_solved_strict", "probe_decisions", "probe_lookAheadCount"],
    "probe_solved_then_high_lookahead": ["probe_solved_strict", "probe_lookAheadCount", "probe_decisions"],
    "probe_solved_then_high_unitresolve": ["probe_solved_strict", "probe_unitResolveCount", "probe_dead_ends_in_main"],
    "probe_solved_then_high_deadends": ["probe_solved_strict", "probe_dead_ends_in_main", "probe_unitResolveCount"],
    "probe_solved_then_low_decisions": ["probe_solved_strict", "probe_decisions_low", "probe_lookAheadCount"],
}


def _num(stats: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(stats.get(key, default))
    except (TypeError, ValueError):
        return default


def probe_candidates(cnf, var_params_all: np.ndarray, features: pd.DataFrame, solver_seed: int, probe_cpu_lim: float) -> pd.DataFrame:
    rows = []
    for row in features.sort_values("sample_id").itertuples(index=False):
        sample_id = int(row.sample_id)
        start = time.monotonic()
        stats = solve_cnf(
            cnf.clauses,
            var_params_all[:, sample_id, :],
            seed=solver_seed,
            solver="march",
            **{"cpu-lim": probe_cpu_lim},
        )
        wall_time = time.monotonic() - start
        result = str(stats.get("Result", "UNKNOWN"))
        cpu_time = _num(stats, "CPU time", probe_cpu_lim)
        rows.append(
            {
                "sample_id": sample_id,
                "probe_Result": result,
                "probe_CPU_time": cpu_time,
                "probe_wall_time": wall_time,
                "probe_solved_returned": result in SOLVED,
                "probe_solved_strict": bool(result in SOLVED and cpu_time <= probe_cpu_lim),
                "probe_decisions": _num(stats, "decisions"),
                "probe_lookAheadCount": _num(stats, "lookAheadCount"),
                "probe_unitResolveCount": _num(stats, "unitResolveCount"),
                "probe_necessary_assignments": _num(stats, "necessary_assignments"),
                "probe_dead_ends_in_main": _num(stats, "dead_ends_in_main"),
            }
        )
    return pd.DataFrame(rows)


def rank_by_policy(candidates: pd.DataFrame, policy: str) -> pd.DataFrame:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}; expected one of {sorted(POLICIES)}")
    ranked = candidates.copy()
    ranked["probe_decisions_low"] = -ranked["probe_decisions"]
    sort_cols = POLICIES[policy]
    ranked = ranked.sort_values(sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)
    ranked["selector_policy"] = policy
    ranked["selector_rank"] = np.arange(1, len(ranked) + 1)
    return ranked.drop(columns=["probe_decisions_low"])


def choose_effective_top_k(
    ranked: pd.DataFrame,
    default_top_k: int,
    adaptive_threshold_a: float | None,
    adaptive_threshold_b: float | None,
    adaptive_top_k_a: int,
    adaptive_top_k_b: int,
    probe_solved_cap: int,
) -> tuple[str, int, float]:
    if probe_solved_cap <= 0:
        raise ValueError("probe_solved_cap must be positive.")
    max_deadends = float(pd.to_numeric(ranked["probe_dead_ends_in_main"], errors="coerce").fillna(0.0).max())
    if adaptive_threshold_a is None or adaptive_threshold_b is None:
        return "fixed_top_k", int(default_top_k), max_deadends
    if adaptive_threshold_a < adaptive_threshold_b:
        raise ValueError("adaptive_threshold_a must be >= adaptive_threshold_b.")
    if int(ranked["probe_solved_strict"].sum()) > 0:
        return "probe_solved_first", 0, max_deadends
    if max_deadends >= adaptive_threshold_a:
        return "adaptive_top_k_a", int(adaptive_top_k_a), max_deadends
    if max_deadends >= adaptive_threshold_b:
        return "adaptive_top_k_b", int(adaptive_top_k_b), max_deadends
    return "adaptive_default_top_k", int(default_top_k), max_deadends


def run_group(
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
    probe_cpu_lim: float,
    full_cpu_lim: float,
    adaptive_threshold_a: float | None = None,
    adaptive_threshold_b: float | None = None,
    adaptive_top_k_a: int = 8,
    adaptive_top_k_b: int = 4,
    probe_solved_cap: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    sample_start = time.monotonic()
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
    neural_generation_wall_time = time.monotonic() - sample_start
    features = sample_feature_frame(data, size=size, file_key=file_key, sample_seed=sample_seed)
    cnf = dataset.get_cnf(int(data.cnf_id.item()))
    var_params_all = data["var"].var_params.numpy()
    probe = probe_candidates(cnf, var_params_all, features, solver_seed=solver_seed, probe_cpu_lim=probe_cpu_lim)
    candidates = features.merge(probe, on="sample_id", how="left", validate="one_to_one")
    ranked = rank_by_policy(candidates, policy=policy)
    selector_rule, effective_top_k, max_probe_deadends = choose_effective_top_k(
        ranked=ranked,
        default_top_k=top_k,
        adaptive_threshold_a=adaptive_threshold_a,
        adaptive_threshold_b=adaptive_threshold_b,
        adaptive_top_k_a=adaptive_top_k_a,
        adaptive_top_k_b=adaptive_top_k_b,
        probe_solved_cap=probe_solved_cap,
    )
    ranked["top_k"] = int(top_k)
    ranked["selector_rule"] = selector_rule
    ranked["effective_top_k"] = int(effective_top_k)
    ranked["max_probe_deadends"] = float(max_probe_deadends)
    ranked["adaptive_threshold_a"] = adaptive_threshold_a
    ranked["adaptive_threshold_b"] = adaptive_threshold_b
    ranked["adaptive_top_k_a"] = int(adaptive_top_k_a)
    ranked["adaptive_top_k_b"] = int(adaptive_top_k_b)
    ranked["probe_solved_cap"] = int(probe_solved_cap)
    ranked["selected"] = ranked["selector_rank"] <= int(effective_top_k)

    probe_solved = ranked[ranked["probe_solved_strict"]].head(int(probe_solved_cap))
    raw_rows = []
    full_cpu = 0.0
    solved_any = False
    solved_stage = "none"
    first_solved_rank = -1
    if not probe_solved.empty:
        solved_any = True
        solved_stage = "probe"
        first_solved_rank = int(probe_solved.iloc[0]["selector_rank"])

    if not solved_any:
        for row in ranked[ranked["selected"]].itertuples(index=False):
            sample_id = int(row.sample_id)
            full_start = time.monotonic()
            stats = solve_cnf(
                cnf.clauses,
                var_params_all[:, sample_id, :],
                seed=solver_seed,
                solver="march",
                **{"cpu-lim": full_cpu_lim},
            )
            wall_time = time.monotonic() - full_start
            cpu_time = _num(stats, "CPU time", full_cpu_lim)
            result = str(stats.get("Result", "UNKNOWN"))
            solved_returned = result in SOLVED
            solved_strict_limit = bool(solved_returned and cpu_time <= full_cpu_lim)
            full_cpu += min(cpu_time, full_cpu_lim)
            raw_rows.append(
                {
                    "size": int(size),
                    "file_key": file_key,
                    "sample_seed": int(sample_seed),
                    "solver_seed": int(solver_seed),
                    "selector_policy": policy,
                    "selector_rule": selector_rule,
                    "top_k": int(top_k),
                    "effective_top_k": int(effective_top_k),
                    "num_samples_generated": int(num_samples),
                    "probe_cpu_lim": float(probe_cpu_lim),
                    "adaptive_threshold_a": adaptive_threshold_a,
                    "adaptive_threshold_b": adaptive_threshold_b,
                    "adaptive_top_k_a": int(adaptive_top_k_a),
                    "adaptive_top_k_b": int(adaptive_top_k_b),
                    "probe_solved_cap": int(probe_solved_cap),
                    "sample_id": sample_id,
                    "selector_rank": int(row.selector_rank),
                    "Result": result,
                    "CPU time": cpu_time,
                    "wall_time": wall_time,
                    "decisions": _num(stats, "decisions", np.nan),
                    "lookAheadCount": _num(stats, "lookAheadCount", np.nan),
                    "external_timeout": bool(stats.get("external_timeout", False)),
                    "solved_returned": solved_returned,
                    "solved_strict60": solved_strict_limit,
                    "solved_strict_limit": solved_strict_limit,
                    "full_cpu_lim": float(full_cpu_lim),
                    "full_cpu_capped_after_attempt": float(full_cpu),
                }
            )
            if solved_strict_limit:
                solved_any = True
                solved_stage = "full"
                first_solved_rank = int(row.selector_rank)
                break

    probe_cpu_total = float(num_samples) * float(probe_cpu_lim)
    probe_wall_time_total = float(pd.to_numeric(probe["probe_wall_time"], errors="coerce").fillna(0.0).sum())
    full_cpu_allocated = float(effective_top_k) * float(full_cpu_lim)
    full_wall_time_total = (
        float(pd.to_numeric(pd.DataFrame(raw_rows)["wall_time"], errors="coerce").fillna(0.0).sum())
        if raw_rows
        else 0.0
    )
    summary = {
        "size": int(size),
        "file_key": file_key,
        "sample_seed": int(sample_seed),
        "solver_seed": int(solver_seed),
        "selector_policy": policy,
        "selector_rule": selector_rule,
        "top_k": int(top_k),
        "effective_top_k": int(effective_top_k),
        "num_samples_generated": int(num_samples),
        "probe_cpu_lim": float(probe_cpu_lim),
        "full_cpu_lim": float(full_cpu_lim),
        "adaptive_threshold_a": adaptive_threshold_a,
        "adaptive_threshold_b": adaptive_threshold_b,
        "adaptive_top_k_a": int(adaptive_top_k_a),
        "adaptive_top_k_b": int(adaptive_top_k_b),
        "probe_solved_cap": int(probe_solved_cap),
        "max_probe_deadends": float(max_probe_deadends),
        "probe_solved_samples": int(ranked["probe_solved_strict"].sum()),
        "attempts_used": int(len(raw_rows)),
        "solved_any_strict60": bool(solved_any),
        "solved_stage": solved_stage,
        "first_solved_rank": int(first_solved_rank),
        "probe_cpu_total": probe_cpu_total,
        "neural_generation_wall_time": float(neural_generation_wall_time),
        "probe_wall_time_total": probe_wall_time_total,
        "full_cpu_allocated": full_cpu_allocated,
        "full_cpu_capped": float(full_cpu),
        "full_wall_time_total": full_wall_time_total,
        "total_cpu_allocated": float(probe_cpu_total + full_cpu_allocated),
        "total_cpu_capped": float(probe_cpu_total + full_cpu),
        "total_wall_time": float(neural_generation_wall_time + probe_wall_time_total + full_wall_time_total),
    }
    if "solver_seed" not in ranked.columns:
        ranked.insert(0, "solver_seed", int(solver_seed))
    if "sample_seed" not in ranked.columns:
        ranked.insert(0, "sample_seed", int(sample_seed))
    if "file_key" not in ranked.columns:
        ranked.insert(0, "file_key", file_key)
    if "size" not in ranked.columns:
        ranked.insert(0, "size", int(size))
    probe.insert(0, "solver_seed", int(solver_seed))
    probe.insert(0, "sample_seed", int(sample_seed))
    probe.insert(0, "file_key", file_key)
    probe.insert(0, "size", int(size))
    return pd.DataFrame(raw_rows), ranked, probe, summary


def aggregate_summary(groups: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (policy, top_k, probe_cpu_lim, rule), group in groups.groupby(
        ["selector_policy", "top_k", "probe_cpu_lim", "selector_rule"], sort=True
    ):
        rows.append(
            {
                "selector_policy": policy,
                "top_k": int(top_k),
                "probe_cpu_lim": float(probe_cpu_lim),
                "selector_rule": rule,
                "groups": int(len(group)),
                "instances": int(group[["size", "file_key"]].drop_duplicates().shape[0]),
                "sample_seeds": int(group["sample_seed"].nunique()),
                "solved_groups": int(group["solved_any_strict60"].sum()),
                "solved_instances_any_seed": int(group.groupby(["size", "file_key"])["solved_any_strict60"].any().sum()),
                "probe_stage_solves": int(group["solved_stage"].eq("probe").sum()),
                "full_stage_solves": int(group["solved_stage"].eq("full").sum()),
                "mean_attempts_used": float(group["attempts_used"].mean()),
                "mean_effective_top_k": float(group["effective_top_k"].mean()),
                "mean_total_cpu_allocated": float(group["total_cpu_allocated"].mean()),
                "mean_total_cpu_capped": float(group["total_cpu_capped"].mean()),
                "mean_total_wall_time": float(group["total_wall_time"].mean()) if "total_wall_time" in group else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def write_doc(aggregate: pd.DataFrame, group_summary: pd.DataFrame, instances: list[tuple[int, str]], sample_seeds: list[int]) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    instance_frame = pd.DataFrame([{"size": size, "file_key": file_key} for size, file_key in instances])
    lines = [
        "# March Early-Trace Selector Gate",
        "",
        "Scope: non-oracle selector gate for sampled March guidance. Each sampled",
        "guidance first runs under a short internal March CPU budget to collect",
        "progress counters; the selector ranks candidates by those counters and",
        "only reruns fixed top-k candidates under the nominal 60s budget.",
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
            aggregate,
            [
                "selector_policy",
                "top_k",
                "probe_cpu_lim",
                "selector_rule",
                "groups",
                "instances",
                "sample_seeds",
                "solved_groups",
                "solved_instances_any_seed",
                "probe_stage_solves",
                "full_stage_solves",
                "mean_attempts_used",
                "mean_effective_top_k",
                "mean_total_cpu_allocated",
                "mean_total_cpu_capped",
                "mean_total_wall_time",
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
                "selector_rule",
                "top_k",
                "effective_top_k",
                "probe_solved_cap",
                "probe_solved_samples",
                "attempts_used",
                "solved_any_strict60",
                "solved_stage",
                "first_solved_rank",
                "total_cpu_allocated",
                "total_cpu_capped",
                "total_wall_time",
            ],
        ),
        "",
        "Artifacts:",
        "",
        "```text",
        str(PROBE_CSV.relative_to(ROOT)),
        str(RAW_CSV.relative_to(ROOT)),
        str(CANDIDATE_CSV.relative_to(ROOT)),
        str(SUMMARY_CSV.relative_to(ROOT)),
        str(GROUP_DIR.relative_to(ROOT)) + "/",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def group_stem(
    size: int,
    file_key: str,
    sample_seed: int,
    policy: str,
    top_k: int,
    probe_cpu_lim: float,
    adaptive_threshold_a: float | None = None,
    adaptive_threshold_b: float | None = None,
    probe_solved_cap: int = 1,
) -> str:
    file_stem = Path(file_key).stem
    probe_tag = str(probe_cpu_lim).replace(".", "p")
    stem = f"size{size}_{file_stem}_seed{sample_seed}_{policy}_top{top_k}_probe{probe_tag}"
    if adaptive_threshold_a is not None or adaptive_threshold_b is not None:
        threshold_a_tag = str(adaptive_threshold_a).replace(".", "p")
        threshold_b_tag = str(adaptive_threshold_b).replace(".", "p")
        stem += f"_adapA{threshold_a_tag}_B{threshold_b_tag}"
    if int(probe_solved_cap) != 1:
        stem += f"_probeSolvedCap{int(probe_solved_cap)}"
    return stem


def group_paths(stem: str) -> tuple[Path, Path, Path, Path]:
    return (
        GROUP_DIR / f"{stem}_raw.csv",
        GROUP_DIR / f"{stem}_candidates.csv",
        GROUP_DIR / f"{stem}_probe.csv",
        GROUP_DIR / f"{stem}_summary.csv",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an early-trace selector for sampled March guidance.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--instances", default="410:3sat_2.cnf,440:3sat_8.cnf")
    parser.add_argument("--sample-seeds", default="1729,1730,1731")
    parser.add_argument("--solver-seed", type=int, default=1729)
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--policy", default="probe_solved_then_high_decisions", choices=sorted(POLICIES))
    parser.add_argument("--probe-cpu-lim", type=float, default=1.0)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--adaptive-threshold-a", type=float, default=None)
    parser.add_argument("--adaptive-threshold-b", type=float, default=None)
    parser.add_argument("--adaptive-top-k-a", type=int, default=8)
    parser.add_argument("--adaptive-top-k-b", type=int, default=4)
    parser.add_argument("--probe-solved-cap", type=int, default=1)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--resume", action="store_true", help="Reuse per-group CSV artifacts when present.")
    args = parser.parse_args()

    instances = parse_instances(args.instances)
    sample_seeds = parse_seeds(args.sample_seeds)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)

    raw_frames = []
    candidate_frames = []
    probe_frames = []
    group_rows = []
    for size, file_key in instances:
        for sample_seed in sample_seeds:
            stem = group_stem(
                size,
                file_key,
                sample_seed,
                args.policy,
                args.top_k,
                args.probe_cpu_lim,
                args.adaptive_threshold_a,
                args.adaptive_threshold_b,
                args.probe_solved_cap,
            )
            raw_path, candidates_path, probe_path, summary_path = group_paths(stem)
            if args.resume and all(path.exists() for path in [raw_path, candidates_path, probe_path, summary_path]):
                raw = pd.read_csv(raw_path)
                candidates = pd.read_csv(candidates_path)
                probe = pd.read_csv(probe_path)
                group = pd.read_csv(summary_path).iloc[0].to_dict()
            else:
                raw, candidates, probe, group = run_group(
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
                    probe_cpu_lim=args.probe_cpu_lim,
                    full_cpu_lim=args.full_cpu_lim,
                    adaptive_threshold_a=args.adaptive_threshold_a,
                    adaptive_threshold_b=args.adaptive_threshold_b,
                    adaptive_top_k_a=args.adaptive_top_k_a,
                    adaptive_top_k_b=args.adaptive_top_k_b,
                    probe_solved_cap=args.probe_solved_cap,
                )
                raw.to_csv(raw_path, index=False)
                candidates.to_csv(candidates_path, index=False)
                probe.to_csv(probe_path, index=False)
                pd.DataFrame([group]).to_csv(summary_path, index=False)
            raw_frames.append(raw)
            candidate_frames.append(candidates)
            probe_frames.append(probe)
            group_rows.append(group)

    raw_all = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    candidates_all = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()
    probe_all = pd.concat(probe_frames, ignore_index=True) if probe_frames else pd.DataFrame()
    group_summary = pd.DataFrame(group_rows)
    aggregate = aggregate_summary(group_summary)

    probe_all.to_csv(PROBE_CSV, index=False)
    raw_all.to_csv(RAW_CSV, index=False)
    candidates_all.to_csv(CANDIDATE_CSV, index=False)
    group_summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(aggregate, group_summary, instances, sample_seeds)

    print(aggregate.to_string(index=False))
    print(group_summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
