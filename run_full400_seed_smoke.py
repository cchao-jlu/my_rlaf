from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = Path("/home/sunshixin/anaconda3/envs/rlaf/bin/python")
SOURCE_DIR = ROOT / "data/test/3sat/400"
WORK_DIR = ROOT / "runs/analysis/full400_seed_smoke"
SUBSET_DIR = WORK_DIR / "subset/3sat/400"
RAW_DIR = WORK_DIR / "raw"
COMBINED_CSV = WORK_DIR / "combined.csv"
SUMMARY_CSV = WORK_DIR / "summary.csv"
PER_INSTANCE_CSV = WORK_DIR / "per_instance_summary.csv"
PAIR_CSV = WORK_DIR / "pair_summary.csv"
DOC_PATH = ROOT / "docs/full400_seed_smoke.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}

INSTANCES = [
    # Unique Online/Old/Local solved-count boundary point.
    "3sat_188.cnf",
    # 0111 recovered timeouts, including the max Local-vs-Old slowdown case.
    "3sat_163.cnf",
    "3sat_189.cnf",
    "3sat_85.cnf",
    "3sat_89.cnf",
    "3sat_97.cnf",
    # 0000 hard timeout controls.
    "3sat_0.cnf",
    "3sat_8.cnf",
    "3sat_192.cnf",
    "3sat_195.cnf",
    # 1111 solved controls, including local slowdown/speedup examples.
    "3sat_1.cnf",
    "3sat_86.cnf",
    "3sat_140.cnf",
    "3sat_190.cnf",
]


@dataclass(frozen=True)
class MethodSpec:
    method: str
    paper_name: str
    config_name: str
    extra_overrides: tuple[str, ...] = ()


METHODS = [
    MethodSpec(
        method="online_consistent_boundary400",
        paper_name="Online-Consistent Selector",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        extra_overrides=(
            "feedback_refinement.local_reopen_candidate_manifest=null",
        ),
    ),
    MethodSpec(
        method="old_compact",
        paper_name="Old Compact",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        extra_overrides=(
            "checkpoint=runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt",
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


def prepare_subset() -> None:
    SUBSET_DIR.mkdir(parents=True, exist_ok=True)
    for name in INSTANCES:
        source = SOURCE_DIR / name
        if not source.exists():
            raise FileNotFoundError(source)
        target = SUBSET_DIR / name
        if target.exists():
            continue
        try:
            target.symlink_to(source)
        except OSError:
            shutil.copy2(source, target)


def raw_csv_path(spec: MethodSpec, seed: int) -> Path:
    return (RAW_DIR / spec.method / f"seed{seed}.csv").resolve()


def build_command(spec: MethodSpec, seed: int, workers: int) -> list[str]:
    raw_csv = raw_csv_path(spec, seed)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    return [
        str(PYTHON),
        "evaluate_guided_solver.py",
        "--config-name",
        spec.config_name,
        f"dataset.eval_path={SUBSET_DIR.relative_to(ROOT)}/*.cnf",
        f"save_file={raw_csv}",
        f"solver.num_workers={workers}",
        "solver.params.cpu-lim=60",
        "solver.params.rnd-freq=0.0",
        "solver.params.K=0.1",
        f"+solver.params.seed={seed}",
        *spec.extra_overrides,
    ]


def run_eval(spec: MethodSpec, seed: int, workers: int, dry_run: bool, skip_existing: bool) -> Path:
    raw_csv = raw_csv_path(spec, seed)
    if skip_existing and raw_csv.exists():
        print(f"skip existing {raw_csv.relative_to(ROOT)}", flush=True)
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


def summary(combined: pd.DataFrame) -> pd.DataFrame:
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
                "raw_csv": str(group["raw_csv"].iloc[0]),
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
        ("online_consistent_boundary400", "old_compact", "Online-Consistent Selector vs Old Compact"),
        ("online_consistent_boundary400", "local_reopen_guarded", "Online-Consistent Selector vs + Local Boundary Correction"),
        ("old_compact", "local_reopen_guarded", "Old Compact vs + Local Boundary Correction"),
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
                "delta_solved_seed_sum": int(right_solved.sum() - left_solved.sum()),
                "instances_recovered_all_seeds": int(((left_solved == 0) & (right_solved == right_seeds)).sum()),
                "instances_lost_all_seeds": int(((left_solved == left_seeds) & (right_solved == 0)).sum()),
                "instances_recovered_majority": int(((left_fraction < 0.5) & (right_fraction > 0.5)).sum()),
                "instances_lost_majority": int(((left_fraction > 0.5) & (right_fraction < 0.5)).sum()),
                "mean_delta_time": float(delta_time.mean()),
                "max_slowdown_time": float(delta_time.max()),
                "max_speedup_time": float(delta_time.min()),
            }
        )
    return pd.DataFrame(rows)


def write_doc(summary_rows: pd.DataFrame, per_instance: pd.DataFrame, pairs: pd.DataFrame) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    unstable = per_instance[~per_instance["stable_across_seeds"]]
    boundary = per_instance[per_instance["file_key"].eq("3sat_188.cnf")]
    lines = [
        "# Full400 Seed Smoke",
        "",
        "This is a small seed-sensitivity smoke test on selected full400 instances.",
        "It changes only the Glucose `-rnd-seed` value through `+solver.params.seed=<seed>`.",
        "The model, thresholds, `rnd-freq=0.0`, and candidate manifest policy are unchanged.",
        "",
        "Important scope: this is not a full400 multi-seed evaluation.",
        "It is a decision check for whether full400 multi-seed robustness is worth running.",
        "",
        "Seeds: 1, 2, 3.",
        "Methods: Online-Consistent Selector, Old Compact, + Local Boundary Correction.",
        "",
        "Selected instances:",
        "",
    ]
    for name in INSTANCES:
        lines.append(f"- `{name}`")
    lines.extend(
        [
            "",
            "Outputs:",
            "",
            f"- `{COMBINED_CSV.relative_to(ROOT)}`",
            f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
            f"- `{PER_INSTANCE_CSV.relative_to(ROOT)}`",
            f"- `{PAIR_CSV.relative_to(ROOT)}`",
            "",
            "## Per-Seed Summary",
            "",
            "| method | seed | solved | mean time | median time |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in summary_rows.iterrows():
        lines.append(
            "| {paper_name} | {seed} | {solved} | {mean_time:.4f} | {median_time:.4f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Pair Summary",
            "",
            "| comparison | delta solved seed sum | recovered all seeds | lost all seeds | mean delta time | max slowdown | max speedup |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in pairs.iterrows():
        lines.append(
            "| {comparison} | {delta_solved_seed_sum} | {instances_recovered_all_seeds} | {instances_lost_all_seeds} | {mean_delta_time:.4f} | {max_slowdown_time:.4f} | {max_speedup_time:.4f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Seed Stability",
            "",
            f"Unstable method-instance outcomes across seeds: {len(unstable)}.",
        ]
    )
    if not unstable.empty:
        lines.extend(
            [
                "",
                "| instance | method | solved seeds | result values | time min | time max |",
                "| --- | --- | ---: | --- | ---: | ---: |",
            ]
        )
        for _, row in unstable.iterrows():
            lines.append(
                "| {file_key} | {paper_name} | {solved_seeds}/{seeds} | {result_values} | {time_min:.4f} | {time_max:.4f} |".format(
                    **row
                )
            )
    lines.extend(
        [
            "",
            "## Boundary Instance",
            "",
            "| instance | method | solved seeds | mean time | min time | max time |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in boundary.iterrows():
        lines.append(
            "| {file_key} | {paper_name} | {solved_seeds}/{seeds} | {time_mean:.4f} | {time_min:.4f} | {time_max:.4f} |".format(
                **row
            )
        )
    DOC_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run selected full400 seed-sensitivity smoke test.")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    prepare_subset()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    for seed in args.seeds:
        for spec in METHODS:
            raw_csv = run_eval(spec, seed=seed, workers=args.workers, dry_run=args.dry_run, skip_existing=args.skip_existing)
            if not args.dry_run:
                frames.append(load_raw(spec, seed=seed, raw_csv=raw_csv))

    if args.dry_run:
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(COMBINED_CSV, index=False)
    summary_rows = summary(combined)
    summary_rows.to_csv(SUMMARY_CSV, index=False)
    per_instance = per_instance_summary(combined)
    per_instance.to_csv(PER_INSTANCE_CSV, index=False)
    pairs = pair_summary(per_instance)
    pairs.to_csv(PAIR_CSV, index=False)
    write_doc(summary_rows, per_instance, pairs)
    print(f"wrote {COMBINED_CSV.relative_to(ROOT)}")
    print(f"wrote {SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {PER_INSTANCE_CSV.relative_to(ROOT)}")
    print(f"wrote {PAIR_CSV.relative_to(ROOT)}")
    print(f"wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
