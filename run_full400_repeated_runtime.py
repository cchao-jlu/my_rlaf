from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = Path("/home/sunshixin/anaconda3/envs/rlaf/bin/python")
FULL400_GLOB = "data/test/3sat/400/*.cnf"
WORK_DIR = ROOT / "runs/analysis/full400_repeated_runtime"
RAW_DIR = WORK_DIR / "raw"
COMBINED_CSV = WORK_DIR / "combined.csv"
REPEAT_SUMMARY_CSV = WORK_DIR / "repeat_summary.csv"
SUMMARY_CSV = WORK_DIR / "summary.csv"
PER_INSTANCE_SUMMARY_CSV = WORK_DIR / "per_instance_summary.csv"
PAIR_SUMMARY_CSV = WORK_DIR / "pair_summary.csv"
DOC_PATH = ROOT / "docs/full400_repeated_runtime.md"
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


def raw_csv_path(spec: MethodSpec, repeat: int) -> Path:
    return (RAW_DIR / spec.method / f"repeat{repeat}.csv").resolve()


def build_command(spec: MethodSpec, repeat: int, workers: int) -> list[str]:
    raw_csv = raw_csv_path(spec, repeat)
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
        *spec.extra_overrides,
    ]


def run_eval(spec: MethodSpec, repeat: int, workers: int, dry_run: bool, skip_existing: bool) -> Path:
    raw_csv = raw_csv_path(spec, repeat)
    if skip_existing and raw_csv.exists():
        print(f"skip existing {raw_csv.relative_to(ROOT)}", flush=True)
        return raw_csv
    command = build_command(spec, repeat=repeat, workers=workers)
    print(" ".join(command), flush=True)
    if dry_run:
        return raw_csv
    subprocess.run(command, cwd=ROOT, check=True)
    if not raw_csv.exists():
        raise FileNotFoundError(raw_csv)
    return raw_csv


def is_solved(value: object) -> bool:
    return str(value) in SOLVED_RESULTS


def load_raw(spec: MethodSpec, repeat: int, raw_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_csv).copy()
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["method"] = spec.method
    frame["paper_name"] = spec.paper_name
    frame["repeat"] = repeat
    frame["solved"] = frame["Result"].map(is_solved)
    frame["timeout"] = ~frame["solved"]
    frame["raw_csv"] = str(raw_csv.relative_to(ROOT))
    for column in ["time", "CPU time", "GPU time", "conflicts", "decisions", "propagations"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def repeat_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, paper_name, repeat), group in combined.groupby(["method", "paper_name", "repeat"], sort=False):
        rows.append(
            {
                "method": method,
                "paper_name": paper_name,
                "repeat": int(repeat),
                "n": int(len(group)),
                "solved": int(group["solved"].sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
                "total_time": float(group["time"].sum()),
                "mean_cpu_time": float(group["CPU time"].mean()) if "CPU time" in group else float("nan"),
                "mean_gpu_time": float(group["GPU time"].mean()) if "GPU time" in group else float("nan"),
                "raw_csv": str(group["raw_csv"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def method_summary(repeats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, paper_name), group in repeats.groupby(["method", "paper_name"], sort=False):
        rows.append(
            {
                "method": method,
                "paper_name": paper_name,
                "repeats": int(len(group)),
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
        rows.append(
            {
                "file_key": file_key,
                "method": method,
                "paper_name": paper_name,
                "repeats": int(len(group)),
                "solved_repeats": int(group["solved"].sum()),
                "timeout_repeats": int(group["timeout"].sum()),
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
    rows = []
    pairs = [
        ("one_shot", "online_consistent_boundary400", "One-shot vs Online-Consistent Selector"),
        ("one_shot", "old_compact", "One-shot vs Old Compact"),
        ("old_compact", "online_consistent_boundary400", "Old Compact vs Online-Consistent Selector"),
        ("online_consistent_boundary400", "local_reopen_guarded", "Online-Consistent Selector vs + Local Boundary Correction"),
        ("old_compact", "local_reopen_guarded", "Old Compact vs + Local Boundary Correction"),
        ("one_shot", "local_reopen_guarded", "One-shot vs + Local Boundary Correction"),
    ]
    for left, right, label in pairs:
        if left not in pivot["solved_repeats"].columns or right not in pivot["solved_repeats"].columns:
            continue
        left_solved = pivot["solved_repeats"][left]
        right_solved = pivot["solved_repeats"][right]
        left_repeats = pivot["repeats"][left]
        right_repeats = pivot["repeats"][right]
        left_fraction = left_solved / left_repeats
        right_fraction = right_solved / right_repeats
        left_time = pivot["time_mean"][left]
        right_time = pivot["time_mean"][right]
        delta_time = right_time - left_time
        rows.append(
            {
                "comparison": label,
                "n": int(len(pivot)),
                "left_solved_count_mean": float(left_fraction.sum()),
                "right_solved_count_mean": float(right_fraction.sum()),
                "delta_solved_count_mean": float(right_fraction.sum() - left_fraction.sum()),
                "instances_recovered_all_repeats": int(((left_solved == 0) & (right_solved == right_repeats)).sum()),
                "instances_lost_all_repeats": int(((left_solved == left_repeats) & (right_solved == 0)).sum()),
                "instances_recovered_majority": int(((left_fraction < 0.5) & (right_fraction > 0.5)).sum()),
                "instances_lost_majority": int(((left_fraction > 0.5) & (right_fraction < 0.5)).sum()),
                "mean_delta_time": float(delta_time.mean()),
                "median_delta_time": float(delta_time.median()),
                "faster_instances_gt_0p1s": int((delta_time < -0.1).sum()),
                "slower_instances_gt_0p1s": int((delta_time > 0.1).sum()),
            }
        )
    return pd.DataFrame(rows)


def write_doc(summary: pd.DataFrame, repeat_rows: pd.DataFrame, pairs: pd.DataFrame) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Full400 Repeated Runtime Evaluation",
        "",
        "This is a full-test same-seed repeated runtime evaluation for the paper's wall-clock stability claim.",
        "It does not change the model, thresholds, configs, or solver seed.",
        "",
        "Important interpretation: the absolute solved counts differ from the frozen single-run paper table,",
        "which is expected wall-clock drift. The evidence here is repeat-level stability of solved counts",
        "and matched deltas across methods under the same full400 evaluation protocol.",
        "",
        "Scope:",
        "",
        "- One-shot x 3 repeats",
        "- Old Compact x 3 repeats",
        "- Online-Consistent Selector x 3 repeats",
        "- + Local Boundary Correction x 3 repeats",
        "",
        "Outputs:",
        "",
        f"- `{COMBINED_CSV.relative_to(ROOT)}`",
        f"- `{REPEAT_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{PER_INSTANCE_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{PAIR_SUMMARY_CSV.relative_to(ROOT)}`",
        "",
        "## Method Summary",
        "",
        "| method | repeats | solved mean | solved range | mean time mean | mean time std |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            "| {paper_name} | {repeats} | {solved_mean:.3f} | {solved_min}-{solved_max} | {mean_time_mean:.4f} | {mean_time_std:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Per-Repeat Summary",
            "",
            "| method | repeat | solved | mean time | median time |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in repeat_rows.iterrows():
        lines.append(
            "| {paper_name} | {repeat} | {solved} | {mean_time:.4f} | {median_time:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "## Pair Summary",
            "",
            "| comparison | delta solved mean | recovered all repeats | lost all repeats | mean delta time | faster instances | slower instances |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in pairs.iterrows():
        lines.append(
            "| {comparison} | {delta_solved_count_mean:.3f} | {instances_recovered_all_repeats} | {instances_lost_all_repeats} | {mean_delta_time:.4f} | {faster_instances_gt_0p1s} | {slower_instances_gt_0p1s} |".format(
                **row
            )
        )
    DOC_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full400 repeated runtime evaluation.")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    for repeat in range(args.repeats):
        for spec in METHODS:
            raw_csv = run_eval(
                spec,
                repeat=repeat,
                workers=args.workers,
                dry_run=args.dry_run,
                skip_existing=args.skip_existing,
            )
            if not args.dry_run:
                frames.append(load_raw(spec, repeat=repeat, raw_csv=raw_csv))

    if args.dry_run:
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(COMBINED_CSV, index=False)
    repeat_rows = repeat_summary(combined)
    repeat_rows.to_csv(REPEAT_SUMMARY_CSV, index=False)
    summary = method_summary(repeat_rows)
    summary.to_csv(SUMMARY_CSV, index=False)
    per_instance = per_instance_summary(combined)
    per_instance.to_csv(PER_INSTANCE_SUMMARY_CSV, index=False)
    pairs = pair_summary(per_instance)
    pairs.to_csv(PAIR_SUMMARY_CSV, index=False)
    write_doc(summary, repeat_rows, pairs)
    print(f"wrote {COMBINED_CSV.relative_to(ROOT)}")
    print(f"wrote {REPEAT_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {PER_INSTANCE_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {PAIR_SUMMARY_CSV.relative_to(ROOT)}")
    print(f"wrote {DOC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
