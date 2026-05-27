from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = Path("/home/sunshixin/anaconda3/envs/rlaf/bin/python")
FULL400_GLOB = "data/test/3sat/400/*.cnf"
WORK_DIR = ROOT / "runs/analysis/full400_seed_robustness"
RAW_DIR = WORK_DIR / "raw"
REPEATED_RAW_DIR = ROOT / "runs/analysis/full400_repeated_runtime/raw"
COMBINED_CSV = WORK_DIR / "combined.csv"
SEED_SUMMARY_CSV = WORK_DIR / "seed_summary.csv"
METHOD_SUMMARY_CSV = WORK_DIR / "method_summary.csv"
PER_INSTANCE_CSV = WORK_DIR / "per_instance_summary.csv"
PAIR_SUMMARY_CSV = WORK_DIR / "pair_summary.csv"
OVERLAP_CSV = WORK_DIR / "solved_pattern_overlap.csv"
LOCAL_OLD_HARM_CSV = WORK_DIR / "local_vs_old_harm_audit.csv"
DOC_PATH = ROOT / "docs/full400_seed_robustness.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


@dataclass(frozen=True)
class MethodSpec:
    method: str
    paper_name: str
    config_name: str
    extra_overrides: tuple[str, ...] = ()


METHODS = [
    MethodSpec(
        method="one_shot",
        paper_name="One-shot",
        config_name="config_eval_guided_solver",
        extra_overrides=(
            "checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt",
            "feedback_refinement.enabled=False",
            "dataset.lazy=True",
            "loader.batch_size=10",
        ),
    ),
    MethodSpec(
        method="online_consistent_boundary400",
        paper_name="Online-Consistent Selector",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        extra_overrides=(
            "dataset.eval_path=data/test/3sat/400/*.cnf",
            "feedback_refinement.local_reopen_candidate_manifest=null",
        ),
    ),
    MethodSpec(
        method="old_compact",
        paper_name="Old Compact",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        extra_overrides=(
            "checkpoint=runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt",
            "dataset.eval_path=data/test/3sat/400/*.cnf",
            "feedback_refinement.local_reopen_candidate_manifest=null",
        ),
    ),
    MethodSpec(
        method="local_reopen_guarded",
        paper_name="+ Local Boundary Correction",
        config_name="config_eval_guided_solver_local_reopen_guarded_full400",
        extra_overrides=(),
    ),
]


def raw_csv_path(spec: MethodSpec, seed: int) -> Path:
    return (RAW_DIR / spec.method / f"seed{seed}.csv").resolve()


def repeated_seed1_source(spec: MethodSpec) -> Path:
    return REPEATED_RAW_DIR / spec.method / "repeat0.csv"


def import_seed1_raw(spec: MethodSpec, target: Path) -> bool:
    source = repeated_seed1_source(spec)
    if not source.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    print(f"import seed1 {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}", flush=True)
    return True


def build_command(spec: MethodSpec, seed: int, workers: int) -> list[str]:
    raw_csv = raw_csv_path(spec, seed)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    return [
        str(PYTHON),
        "evaluate_guided_solver.py",
        "--config-name",
        spec.config_name,
        f"dataset.eval_path={FULL400_GLOB}",
        f"save_file={raw_csv}",
        f"solver.num_workers={workers}",
        "solver.params.cpu-lim=60",
        "solver.params.rnd-freq=0.0",
        "solver.params.K=0.1",
        f"+solver.params.seed={seed}",
        *spec.extra_overrides,
    ]


def run_eval(
    spec: MethodSpec,
    seed: int,
    workers: int,
    dry_run: bool,
    skip_existing: bool,
    import_seed1: bool,
) -> Path:
    raw_csv = raw_csv_path(spec, seed)
    if skip_existing and raw_csv.exists():
        print(f"skip existing {raw_csv.relative_to(ROOT)}", flush=True)
        return raw_csv
    if seed == 1 and import_seed1:
        if dry_run:
            source = repeated_seed1_source(spec)
            print(f"would import seed1 {source.relative_to(ROOT)} -> {raw_csv.relative_to(ROOT)}", flush=True)
            return raw_csv
        if import_seed1_raw(spec, raw_csv):
            return raw_csv
    command = build_command(spec, seed=seed, workers=workers)
    print(" ".join(command), flush=True)
    if dry_run:
        return raw_csv
    subprocess.run(command, cwd=ROOT, check=True)
    if not raw_csv.exists():
        raise FileNotFoundError(raw_csv)
    return raw_csv


def is_solved(value: object) -> bool:
    return str(value) in SOLVED_RESULTS


def load_raw(spec: MethodSpec, seed: int, raw_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_csv).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["method"] = spec.method
    frame["paper_name"] = spec.paper_name
    frame["seed"] = seed
    frame["solved"] = frame["Result"].map(is_solved)
    frame["timeout"] = ~frame["solved"]
    frame["raw_csv"] = str(raw_csv.relative_to(ROOT))
    for column in ["time", "CPU time", "GPU time", "conflicts", "decisions", "propagations"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def seed_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, paper_name, seed), group in combined.groupby(["method", "paper_name", "seed"], sort=False):
        rows.append(
            {
                "method": method,
                "paper_name": paper_name,
                "seed": int(seed),
                "n": int(len(group)),
                "solved": int(group["solved"].sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
                "total_time": float(group["time"].sum()),
                "raw_csv": str(group["raw_csv"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def method_summary(seed_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, paper_name), group in seed_rows.groupby(["method", "paper_name"], sort=False):
        rows.append(
            {
                "method": method,
                "paper_name": paper_name,
                "seeds": int(len(group)),
                "solved_mean": float(group["solved"].mean()),
                "solved_std": float(group["solved"].std(ddof=0)),
                "solved_min": int(group["solved"].min()),
                "solved_max": int(group["solved"].max()),
                "mean_time_mean": float(group["mean_time"].mean()),
                "mean_time_std": float(group["mean_time"].std(ddof=0)),
                "mean_time_min": float(group["mean_time"].min()),
                "mean_time_max": float(group["mean_time"].max()),
                "median_time_mean": float(group["median_time"].mean()),
                "median_time_std": float(group["median_time"].std(ddof=0)),
            }
        )
    return pd.DataFrame(rows)


def per_instance_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (file_key, method, paper_name), group in combined.groupby(["file_key", "method", "paper_name"], sort=True):
        solved_seeds = int(group["solved"].sum())
        rows.append(
            {
                "file_key": file_key,
                "method": method,
                "paper_name": paper_name,
                "seeds": int(len(group)),
                "solved_seeds": solved_seeds,
                "timeout_seeds": int((~group["solved"]).sum()),
                "stable_across_seeds": solved_seeds in {0, len(group)},
                "time_mean": float(group["time"].mean()),
                "time_std": float(group["time"].std(ddof=0)),
                "time_min": float(group["time"].min()),
                "time_max": float(group["time"].max()),
                "result_values": ",".join(sorted(map(str, group["Result"].unique()))),
            }
        )
    return pd.DataFrame(rows)


def pair_summary(per_instance: pd.DataFrame) -> pd.DataFrame:
    pivot = per_instance.pivot(index="file_key", columns="method")
    pairs = [
        ("one_shot", "online_consistent_boundary400", "One-shot vs Online-Consistent Selector"),
        ("one_shot", "old_compact", "One-shot vs Old Compact"),
        ("online_consistent_boundary400", "old_compact", "Online-Consistent Selector vs Old Compact"),
        ("online_consistent_boundary400", "local_reopen_guarded", "Online-Consistent Selector vs + Local Boundary Correction"),
        ("old_compact", "local_reopen_guarded", "Old Compact vs + Local Boundary Correction"),
        ("one_shot", "local_reopen_guarded", "One-shot vs + Local Boundary Correction"),
    ]
    rows = []
    for left, right, label in pairs:
        left_solved = pivot["solved_seeds"][left]
        right_solved = pivot["solved_seeds"][right]
        left_seeds = pivot["seeds"][left]
        right_seeds = pivot["seeds"][right]
        left_fraction = left_solved / left_seeds
        right_fraction = right_solved / right_seeds
        delta_time = pivot["time_mean"][right] - pivot["time_mean"][left]
        rows.append(
            {
                "comparison": label,
                "n": int(len(pivot)),
                "left_solved_seed_sum": int(left_solved.sum()),
                "right_solved_seed_sum": int(right_solved.sum()),
                "left_solved_count_mean": float(left_fraction.sum()),
                "right_solved_count_mean": float(right_fraction.sum()),
                "delta_solved_count_mean": float(right_fraction.sum() - left_fraction.sum()),
                "instances_recovered_all_seeds": int(((left_solved == 0) & (right_solved == right_seeds)).sum()),
                "instances_lost_all_seeds": int(((left_solved == left_seeds) & (right_solved == 0)).sum()),
                "instances_recovered_majority": int(((left_fraction < 0.5) & (right_fraction > 0.5)).sum()),
                "instances_lost_majority": int(((left_fraction > 0.5) & (right_fraction < 0.5)).sum()),
                "mean_delta_time": float(delta_time.mean()),
                "median_delta_time": float(delta_time.median()),
                "max_slowdown_time": float(delta_time.max()),
                "max_speedup_time": float(delta_time.min()),
            }
        )
    return pd.DataFrame(rows)


def solved_pattern_overlap(per_instance: pd.DataFrame) -> pd.DataFrame:
    pivot = per_instance.pivot(index="file_key", columns="method")
    method_order = [
        ("one_shot", "one_shot"),
        ("online_consistent_boundary400", "online"),
        ("old_compact", "old_compact"),
        ("local_reopen_guarded", "local_correction"),
    ]
    rows = []
    for file_key in pivot.index:
        row: dict[str, object] = {"file_key": file_key}
        pattern_bits = []
        stable = True
        for method, prefix in method_order:
            seeds = int(pivot[("seeds", method)].loc[file_key])
            solved_seeds = int(pivot[("solved_seeds", method)].loc[file_key])
            solved = solved_seeds == seeds
            stable = stable and solved_seeds in {0, seeds}
            pattern_bits.append("1" if solved else "0")
            row[f"{prefix}_solved_seeds"] = solved_seeds
            row[f"{prefix}_solved"] = solved
            row[f"{prefix}_time_mean"] = float(pivot[("time_mean", method)].loc[file_key])
            row[f"{prefix}_time_std"] = float(pivot[("time_std", method)].loc[file_key])
            row[f"{prefix}_result_values"] = pivot[("result_values", method)].loc[file_key]
        row["pattern"] = "".join(pattern_bits)
        row["pattern_label"] = "p" + row["pattern"]
        row["stable_across_seeds_all_methods"] = stable
        row["old_minus_online_time_mean"] = row["old_compact_time_mean"] - row["online_time_mean"]
        row["local_minus_online_time_mean"] = row["local_correction_time_mean"] - row["online_time_mean"]
        row["local_minus_old_time_mean"] = row["local_correction_time_mean"] - row["old_compact_time_mean"]
        rows.append(row)
    return pd.DataFrame(rows).sort_values("file_key")


def local_old_harm_audit(overlap: pd.DataFrame) -> pd.DataFrame:
    frame = overlap.copy()
    frame["old_local_same_solved"] = frame["old_compact_solved"] == frame["local_correction_solved"]
    frame["local_loses_solved_to_old"] = frame["old_compact_solved"] & ~frame["local_correction_solved"]
    frame["local_slower_gt_0p1s"] = frame["old_local_same_solved"] & (frame["local_minus_old_time_mean"] > 0.1)
    frame["local_slower_gt_0p5s"] = frame["old_local_same_solved"] & (frame["local_minus_old_time_mean"] > 0.5)
    frame["local_slower_gt_1p0s"] = frame["old_local_same_solved"] & (frame["local_minus_old_time_mean"] > 1.0)
    return frame.sort_values("local_minus_old_time_mean", ascending=False)


def write_doc(
    seed_rows: pd.DataFrame,
    method_rows: pd.DataFrame,
    per_instance: pd.DataFrame,
    pairs: pd.DataFrame,
    overlap: pd.DataFrame,
    local_old: pd.DataFrame,
    import_seed1: bool,
) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    instability_count = int((~per_instance["stable_across_seeds"]).sum())
    pattern_summary = overlap["pattern"].value_counts().sort_index()
    old_over_online = overlap[(~overlap["online_solved"]) & (overlap["old_compact_solved"])]
    local_over_online = overlap[(~overlap["online_solved"]) & (overlap["local_correction_solved"])]
    local_old_mismatch = overlap[overlap["old_compact_solved"] != overlap["local_correction_solved"]]
    local_old_same = local_old[local_old["old_local_same_solved"]]
    slower_0p1 = int(local_old["local_slower_gt_0p1s"].sum())
    slower_0p5 = int(local_old["local_slower_gt_0p5s"].sum())
    slower_1p0 = int(local_old["local_slower_gt_1p0s"].sum())
    max_slowdown = local_old_same.head(1)

    lines = [
        "# Full400 Solver-Seed Robustness",
        "",
        "This is a full400 solver-seed robustness evaluation for the paper's main result table.",
        "It changes only the Glucose `-rnd-seed` value via `+solver.params.seed=<seed>`.",
        "The model, thresholds, `rnd-freq=0.0`, and Local Boundary Correction candidate manifest are unchanged.",
        "",
        "Scope:",
        "",
        "- seeds 1, 2, 3",
        "- One-shot",
        "- Online-Consistent Selector",
        "- Old Compact",
        "- + Local Boundary Correction",
        "",
    ]
    if import_seed1:
        lines.extend(
            [
                "Seed 1 raw CSVs are imported from `runs/analysis/full400_repeated_runtime/raw/*/repeat0.csv`.",
                "Those runs used the default `solve_cnf(seed=1)` and are equivalent to explicit `+solver.params.seed=1` under this evaluation path.",
                "",
            ]
        )
    lines.extend(
        [
            "Outputs:",
            "",
            f"- `{COMBINED_CSV.relative_to(ROOT)}`",
            f"- `{SEED_SUMMARY_CSV.relative_to(ROOT)}`",
            f"- `{METHOD_SUMMARY_CSV.relative_to(ROOT)}`",
            f"- `{PER_INSTANCE_CSV.relative_to(ROOT)}`",
            f"- `{PAIR_SUMMARY_CSV.relative_to(ROOT)}`",
            f"- `{OVERLAP_CSV.relative_to(ROOT)}`",
            f"- `{LOCAL_OLD_HARM_CSV.relative_to(ROOT)}`",
            "",
            "## Method Summary",
            "",
            "| method | seeds | solved mean | solved std | solved range | mean time mean | mean time std |",
            "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for _, row in method_rows.iterrows():
        lines.append(
            "| {paper_name} | {seeds} | {solved_mean:.3f} | {solved_std:.3f} | {solved_min}-{solved_max} | {mean_time_mean:.4f} | {mean_time_std:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Per-Seed Summary",
            "",
            "| method | seed | solved | mean time | median time |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in seed_rows.iterrows():
        lines.append(
            "| {paper_name} | {seed} | {solved} | {mean_time:.4f} | {median_time:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Robustness Diagnostics",
            "",
            f"- Method-instance solved-pattern instability count: {instability_count}.",
            f"- Old Compact over Online all-seed solved instances: {', '.join(old_over_online['file_key']) if not old_over_online.empty else 'none'}.",
            f"- Local Correction over Online all-seed solved instances: {', '.join(local_over_online['file_key']) if not local_over_online.empty else 'none'}.",
            f"- Local-vs-Old solved mismatch count: {len(local_old_mismatch)}.",
            f"- Local-vs-Old same-solved slowdown count >0.1s: {slower_0p1}.",
            f"- Local-vs-Old same-solved slowdown count >0.5s: {slower_0p5}.",
            f"- Local-vs-Old same-solved slowdown count >1.0s: {slower_1p0}.",
        ]
    )
    if not max_slowdown.empty:
        row = max_slowdown.iloc[0]
        lines.append(
            "- Maximum Local-vs-Old same-solved slowdown is {delta:.4f}s on `{file_key}`.".format(
                delta=row["local_minus_old_time_mean"],
                file_key=row["file_key"],
            )
        )
    lines.extend(
        [
            "",
            "Solved pattern order: `One-shot / Online-Consistent / Old Compact / + Local Boundary Correction`.",
            "",
            "| pattern | count |",
            "| --- | ---: |",
        ]
    )
    for pattern, count in pattern_summary.items():
        lines.append(f"| {pattern} | {count} |")

    lines.extend(
        [
            "",
            "## Pair Summary",
            "",
            "| comparison | delta solved mean | recovered all seeds | lost all seeds | mean delta time |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in pairs.iterrows():
        lines.append(
            "| {comparison} | {delta_solved_count_mean:.3f} | {instances_recovered_all_seeds} | {instances_lost_all_seeds} | {mean_delta_time:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Paper-Facing Reading",
            "",
            "Use this table as solver-seed robustness evidence, not as a new model result.",
            "The intended claim is whether the repeated full400 conclusions remain stable under seeds 1/2/3.",
            "Do not tune thresholds or alter model branches based on this table.",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full400 solver-seed robustness evaluation.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--no-import-seed1", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    import_seed1 = not args.no_import_seed1

    frames = []
    for seed in args.seeds:
        for spec in METHODS:
            raw_csv = run_eval(
                spec,
                seed=seed,
                workers=args.workers,
                dry_run=args.dry_run,
                skip_existing=args.skip_existing,
                import_seed1=import_seed1,
            )
            if not args.dry_run:
                frames.append(load_raw(spec, seed=seed, raw_csv=raw_csv))

    if args.dry_run:
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(COMBINED_CSV, index=False)
    seed_rows = seed_summary(combined)
    seed_rows.to_csv(SEED_SUMMARY_CSV, index=False)
    method_rows = method_summary(seed_rows)
    method_rows.to_csv(METHOD_SUMMARY_CSV, index=False)
    per_instance = per_instance_summary(combined)
    per_instance.to_csv(PER_INSTANCE_CSV, index=False)
    pairs = pair_summary(per_instance)
    pairs.to_csv(PAIR_SUMMARY_CSV, index=False)
    overlap = solved_pattern_overlap(per_instance)
    overlap.to_csv(OVERLAP_CSV, index=False)
    local_old = local_old_harm_audit(overlap)
    local_old.to_csv(LOCAL_OLD_HARM_CSV, index=False)
    write_doc(seed_rows, method_rows, per_instance, pairs, overlap, local_old, import_seed1=import_seed1)
    print(f"wrote {COMBINED_CSV.relative_to(ROOT)}")
    print(f"wrote {SEED_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {METHOD_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {PER_INSTANCE_CSV.relative_to(ROOT)}")
    print(f"wrote {PAIR_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {OVERLAP_CSV.relative_to(ROOT)}")
    print(f"wrote {LOCAL_OLD_HARM_CSV.relative_to(ROOT)}")
    print(f"wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
