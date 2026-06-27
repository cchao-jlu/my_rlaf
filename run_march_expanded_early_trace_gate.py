from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import torch

import run_march_budgeted_sample_selector as budgeted_runner
from run_march_early_trace_selector import (
    ROOT,
    aggregate_summary,
    group_paths,
    group_stem,
    run_group,
    write_doc,
)
from src.model.model import load_checkpoint


SOURCE_ROOT = ROOT / "data/benchmark_transition_band_expanded"
SUBSET_ROOT = ROOT / "data/benchmark_march_expanded_early_trace_gate"
WORK_DIR = ROOT / "runs/analysis/benchmark_march_expanded_early_trace_gate"
GROUP_DIR = WORK_DIR / "groups"
BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv"
RAW_CSV = WORK_DIR / "expanded_early_trace_raw.csv"
CANDIDATE_CSV = WORK_DIR / "expanded_early_trace_candidates.csv"
PROBE_CSV = WORK_DIR / "expanded_early_trace_probe_raw.csv"
SUMMARY_CSV = WORK_DIR / "expanded_early_trace_summary.csv"
AGGREGATE_CSV = WORK_DIR / "expanded_early_trace_aggregate.csv"
SELECTOR_SPEC_JSON = WORK_DIR / "selector_spec.json"
DOC_PATH = ROOT / "docs/benchmark_march_expanded_early_trace_gate.md"
REQUIRED_GROUP_SUMMARY_COLUMNS = {
    "neural_generation_wall_time",
    "probe_wall_time_total",
    "full_wall_time_total",
    "total_wall_time",
}


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not seeds:
        raise ValueError("At least one sample seed is required.")
    return seeds


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_subset(input_csv: Path, source_root: Path, subset_root: Path, limit_instances: int = 0) -> pd.DataFrame:
    frame = pd.read_csv(input_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {sorted(missing)}")
    if limit_instances > 0:
        frame = frame.head(limit_instances).copy()
    if frame.empty:
        raise ValueError(f"No residual rows in {input_csv}")
    for row in frame.itertuples(index=False):
        family = str(row.family)
        size = int(row.size)
        file_key = str(row.file_key)
        cnf_path_value = getattr(row, "cnf_path", None)
        if cnf_path_value and str(cnf_path_value) != "nan":
            source = Path(cnf_path_value)
            if not source.is_absolute():
                source = ROOT / source
        else:
            source = source_root / family / str(size) / file_key
        if not source.exists():
            raise FileNotFoundError(source)
        target_dir = subset_root / family / str(size)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / file_key
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)
    return frame


def write_expanded_doc(
    aggregate: pd.DataFrame,
    group_summary: pd.DataFrame,
    subset: pd.DataFrame,
    sample_seeds: list[int],
    input_csv: Path,
    checkpoint: str,
    out_dir: Path,
) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Expanded March Early-Trace Gate",
        "",
        "Scope: recoverable early-trace selector gate on the expanded",
        "March/CaDiCaL both-unknown transition-band subset. This is still a",
        "model/experiment gate, not a paper claim.",
        "",
        f"Input CSV: `{display_path(input_csv)}`.",
        f"Checkpoint: `{checkpoint}`.",
        f"Output dir: `{display_path(out_dir)}`.",
        f"Input instances: {len(subset)}; sample seeds: {sample_seeds}.",
        "",
        "## Aggregate",
        "",
        *markdown_table(
            aggregate,
            [
                "selector_policy",
                "top_k",
                "probe_cpu_lim",
                "groups",
                "instances",
                "sample_seeds",
                "solved_groups",
                "solved_instances_any_seed",
                "probe_stage_solves",
                "full_stage_solves",
                "mean_attempts_used",
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
                "top_k",
                "probe_solved_samples",
                "attempts_used",
                "solved_any_strict60",
                "solved_stage",
                "first_solved_rank",
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
        str(AGGREGATE_CSV.relative_to(ROOT)),
        str(GROUP_DIR.relative_to(ROOT)) + "/",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def write_selector_spec(args: argparse.Namespace, sample_seeds: list[int], path: Path) -> None:
    checkpoint_path = Path(str(args.checkpoint))
    if not checkpoint_path.is_absolute():
        checkpoint_path = ROOT / checkpoint_path
    spec = {
        "kind": "fixed_early_trace_neural_selector",
        "selector_spec_source": display_path(args.selector_spec_in.resolve()) if args.selector_spec_in else "",
        "selector_spec_source_sha256": file_sha256(args.selector_spec_in.resolve()) if args.selector_spec_in else "",
        "selector_spec_source_split": "dev" if args.selector_spec_in else "",
        "checkpoint": args.checkpoint,
        "checkpoint_sha256": file_sha256(checkpoint_path) if checkpoint_path.exists() else "",
        "input_csv": display_path(args.input.resolve()),
        "source_root": display_path(args.source_root.resolve()),
        "subset_root": display_path(args.subset_root.resolve()),
        "sample_seeds": sample_seeds,
        "solver_seed": int(args.solver_seed),
        "num_samples": int(args.num_samples),
        "policy": args.policy,
        "top_k": int(args.top_k),
        "probe_cpu_lim": float(args.probe_cpu_lim),
        "full_cpu_lim": float(args.full_cpu_lim),
        "adaptive_threshold_a": args.adaptive_threshold_a,
        "adaptive_threshold_b": args.adaptive_threshold_b,
        "adaptive_top_k_a": int(args.adaptive_top_k_a),
        "adaptive_top_k_b": int(args.adaptive_top_k_b),
        "probe_solved_cap": int(args.probe_solved_cap),
        "budget_accounting": {
            "neural_generation_wall_time": "wall-clock time for model-guided sample generation",
            "probe_cpu_total": "num_samples * probe_cpu_lim",
            "probe_wall_time_total": "sum wall-clock time for probe attempts",
            "full_cpu_capped": "sum(min(reported_cpu_time, full_cpu_lim)) for selected full attempts",
            "full_wall_time_total": "sum wall-clock time for selected full attempts",
            "total_cpu_capped": "probe_cpu_total + full_cpu_capped",
            "total_wall_time": "neural_generation_wall_time + probe_wall_time_total + full_wall_time_total",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def group_artifacts_complete(paths: list[Path]) -> bool:
    if not all(path.exists() for path in paths):
        return False
    summary_path = paths[-1]
    try:
        summary = pd.read_csv(summary_path, nrows=1)
    except Exception:
        return False
    return REQUIRED_GROUP_SUMMARY_COLUMNS.issubset(summary.columns)


def apply_selector_spec(args: argparse.Namespace) -> None:
    if args.selector_spec_in is None:
        return
    with args.selector_spec_in.open(encoding="utf-8") as handle:
        spec = json.load(handle)
    required = {"checkpoint", "sample_seeds", "solver_seed", "num_samples", "policy", "top_k", "probe_cpu_lim", "full_cpu_lim"}
    missing = required - set(spec)
    if missing:
        raise ValueError(f"Selector spec is missing required fields: {sorted(missing)}")
    args.checkpoint = str(spec["checkpoint"])
    args.sample_seeds = ",".join(str(seed) for seed in spec["sample_seeds"])
    args.solver_seed = int(spec["solver_seed"])
    args.num_samples = int(spec["num_samples"])
    args.policy = str(spec["policy"])
    args.top_k = int(spec["top_k"])
    args.probe_cpu_lim = float(spec["probe_cpu_lim"])
    args.full_cpu_lim = float(spec["full_cpu_lim"])
    args.adaptive_threshold_a = spec.get("adaptive_threshold_a")
    args.adaptive_threshold_b = spec.get("adaptive_threshold_b")
    args.adaptive_top_k_a = int(spec.get("adaptive_top_k_a", 8))
    args.adaptive_top_k_b = int(spec.get("adaptive_top_k_b", 4))
    args.probe_solved_cap = int(spec.get("probe_solved_cap", 1))


def main() -> None:
    global SOURCE_ROOT
    global SUBSET_ROOT
    global WORK_DIR
    global GROUP_DIR
    global BOTH_UNKNOWN_CSV
    global RAW_CSV
    global CANDIDATE_CSV
    global PROBE_CSV
    global SUMMARY_CSV
    global AGGREGATE_CSV
    global SELECTOR_SPEC_JSON
    global DOC_PATH

    parser = argparse.ArgumentParser(description="Run expanded early-trace gate on March/CaDiCaL both-unknown instances.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--input", type=Path, default=BOTH_UNKNOWN_CSV, help="Residual CSV with family,size,file_key columns.")
    parser.add_argument("--source-root", type=Path, default=SOURCE_ROOT, help="Root containing family/size/file_key CNFs.")
    parser.add_argument("--subset-root", type=Path, default=SUBSET_ROOT, help="Working CNF subset root for symlinks/copies.")
    parser.add_argument("--out-dir", type=Path, default=WORK_DIR)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    parser.add_argument(
        "--selector-spec-in",
        type=Path,
        default=None,
        help="Frozen selector spec from dev. Overrides checkpoint, seeds, policy, top-k, thresholds, and budgets only.",
    )
    parser.add_argument("--sample-seeds", default="1729")
    parser.add_argument("--solver-seed", type=int, default=1729)
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--policy", default="probe_solved_then_high_deadends")
    parser.add_argument("--probe-cpu-lim", type=float, default=1.0)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--adaptive-threshold-a", type=float, default=None)
    parser.add_argument("--adaptive-threshold-b", type=float, default=None)
    parser.add_argument("--adaptive-top-k-a", type=int, default=8)
    parser.add_argument("--adaptive-top-k-b", type=int, default=4)
    parser.add_argument("--probe-solved-cap", type=int, default=1)
    parser.add_argument("--limit-instances", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    apply_selector_spec(args)

    SOURCE_ROOT = args.source_root.resolve()
    SUBSET_ROOT = args.subset_root.resolve()
    WORK_DIR = args.out_dir.resolve()
    GROUP_DIR = WORK_DIR / "groups"
    BOTH_UNKNOWN_CSV = args.input.resolve()
    RAW_CSV = WORK_DIR / "expanded_early_trace_raw.csv"
    CANDIDATE_CSV = WORK_DIR / "expanded_early_trace_candidates.csv"
    PROBE_CSV = WORK_DIR / "expanded_early_trace_probe_raw.csv"
    SUMMARY_CSV = WORK_DIR / "expanded_early_trace_summary.csv"
    AGGREGATE_CSV = WORK_DIR / "expanded_early_trace_aggregate.csv"
    SELECTOR_SPEC_JSON = WORK_DIR / "selector_spec.json"
    DOC_PATH = args.doc.resolve()

    sample_seeds = parse_seeds(args.sample_seeds)
    write_selector_spec(args=args, sample_seeds=sample_seeds, path=SELECTOR_SPEC_JSON)
    subset = prepare_subset(
        input_csv=BOTH_UNKNOWN_CSV,
        source_root=SOURCE_ROOT,
        subset_root=SUBSET_ROOT,
        limit_instances=args.limit_instances,
    )
    budgeted_runner.SOURCE_ROOT = SOURCE_ROOT
    budgeted_runner.SUBSET_ROOT = SUBSET_ROOT
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)

    raw_frames = []
    candidate_frames = []
    probe_frames = []
    group_rows = []
    for row in subset.itertuples(index=False):
        size = int(row.size)
        file_key = str(row.file_key)
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
            raw_path = GROUP_DIR / raw_path.name
            candidates_path = GROUP_DIR / candidates_path.name
            probe_path = GROUP_DIR / probe_path.name
            summary_path = GROUP_DIR / summary_path.name
            if args.resume and group_artifacts_complete([raw_path, candidates_path, probe_path, summary_path]):
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

    raw_all.to_csv(RAW_CSV, index=False)
    candidates_all.to_csv(CANDIDATE_CSV, index=False)
    probe_all.to_csv(PROBE_CSV, index=False)
    group_summary.to_csv(SUMMARY_CSV, index=False)
    aggregate.to_csv(AGGREGATE_CSV, index=False)
    write_expanded_doc(
        aggregate=aggregate,
        group_summary=group_summary,
        subset=subset,
        sample_seeds=sample_seeds,
        input_csv=BOTH_UNKNOWN_CSV,
        checkpoint=args.checkpoint,
        out_dir=WORK_DIR,
    )

    print(aggregate.to_string(index=False))
    print(group_summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
