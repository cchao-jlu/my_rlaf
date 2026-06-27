from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = Path("/home/sunshixin/anaconda3/envs/rlaf/bin/python")
SOURCE_DIR = ROOT / "data/benchmark_3sat450_gate/3sat/450"
HARD_CSV = ROOT / "runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv"
HARD_DIR = ROOT / "data/benchmark_3sat450_gate/strong_hard/3sat/450"
HARD_GLOB = "data/benchmark_3sat450_gate/strong_hard/3sat/450/*.cnf"
WORK_DIR = ROOT / "runs/analysis/benchmark_3sat450_neural_gate"
RAW_DIR = WORK_DIR / "raw"
COMBINED_CSV = WORK_DIR / "combined.csv"
SEED_SUMMARY_CSV = WORK_DIR / "seed_summary.csv"
METHOD_SUMMARY_CSV = WORK_DIR / "method_summary.csv"
OVERLAP_CSV = WORK_DIR / "strong_hard_neural_overlap.csv"
DOC_PATH = ROOT / "docs/benchmark_3sat450_neural_gate.md"
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
            "feedback_refinement.local_reopen_candidate_manifest=null",
        ),
    ),
]


def prepare_hard_subset(clean: bool = False) -> list[str]:
    if clean and HARD_DIR.exists():
        shutil.rmtree(HARD_DIR)
    HARD_DIR.mkdir(parents=True, exist_ok=True)
    hard = pd.read_csv(HARD_CSV)
    file_keys = hard["file_key"].astype(str).tolist()
    for file_key in file_keys:
        source = SOURCE_DIR / file_key
        target = HARD_DIR / file_key
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)
    return file_keys


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
        f"dataset.eval_path={HARD_GLOB}",
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
                "unknown": int((~group["solved"]).sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
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
            }
        )
    return pd.DataFrame(rows)


def overlap_summary(combined: pd.DataFrame, file_keys: list[str]) -> pd.DataFrame:
    rows = []
    for file_key in sorted(file_keys):
        row: dict[str, object] = {"file_key": file_key}
        pattern = []
        for spec in METHODS:
            group = combined[(combined["file_key"] == file_key) & (combined["method"] == spec.method)]
            seeds = int(group["seed"].nunique())
            solved_seeds = int(group["solved"].sum())
            solved_all = solved_seeds == seeds
            row[f"{spec.method}_solved_seeds"] = solved_seeds
            row[f"{spec.method}_solved_all"] = solved_all
            row[f"{spec.method}_time_mean"] = float(group["time"].mean())
            row[f"{spec.method}_result_values"] = ",".join(sorted(map(str, group["Result"].unique())))
            pattern.append("1" if solved_all else "0")
        row["pattern"] = "".join(pattern)
        rows.append(row)
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


def write_doc(seed_rows: pd.DataFrame, method_rows: pd.DataFrame, overlap: pd.DataFrame, file_keys: list[str]) -> None:
    online_strict = overlap[overlap["online_consistent_boundary400_solved_all"]]
    one_shot_strict = overlap[overlap["one_shot_solved_all"]]
    online_only = overlap[
        (~overlap["one_shot_solved_all"]) & overlap["online_consistent_boundary400_solved_all"]
    ]
    pattern_counts = overlap["pattern"].value_counts().sort_index().reset_index()
    pattern_counts.columns = ["pattern", "count"]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 3SAT-450 Neural Gate on Strong-Solver-Hard Subset",
        "",
        "Scope: frozen neural workflow gate only. This evaluates One-shot and",
        "Online-Consistent Selector on the 13 instances that repeated March and",
        "CaDiCaL both failed to solve in `docs/benchmark_3sat450_gate.md`.",
        "It does not train models, tune thresholds, or migrate Local Boundary",
        "Correction to 450.",
        "",
        "Inputs:",
        "",
        "```text",
        str(HARD_CSV.relative_to(ROOT)),
        str(HARD_DIR.relative_to(ROOT)) + "/*.cnf",
        "```",
        "",
        "## Method Summary",
        "",
        *markdown_table(
            method_rows,
            ["paper_name", "seeds", "solved_mean", "solved_std", "solved_min", "solved_max", "mean_time_mean", "mean_time_std"],
        ),
        "",
        "## Per-Seed Summary",
        "",
        *markdown_table(seed_rows, ["paper_name", "seed", "n", "solved", "unknown", "mean_time", "median_time"]),
        "",
        "## Solved Pattern Summary",
        "",
        "Pattern order: `One-shot / Online-Consistent Selector`; solved means solved in all requested seeds.",
        "",
        *markdown_table(pattern_counts, ["pattern", "count"]),
        "",
        "## Strict Neural Complement on March+CaDiCaL-Hard Instances",
        "",
        f"- Strong-solver-hard subset size: {len(file_keys)}.",
        f"- One-shot solved in all seeds: {len(one_shot_strict)}.",
        f"- Online-Consistent solved in all seeds: {len(online_strict)}.",
        f"- Online-only over One-shot in all seeds: {len(online_only)}.",
    ]
    if not online_strict.empty:
        lines.append(
            "- Online strict solved keys: "
            + ", ".join(f"`{value}`" for value in online_strict["file_key"].tolist())
            + "."
        )
    if not online_only.empty:
        lines.append(
            "- Online-only strict keys: "
            + ", ".join(f"`{value}`" for value in online_only["file_key"].tolist())
            + "."
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ]
    )
    if len(online_strict) > 0:
        lines.extend(
            [
                "- Frozen Online-Consistent guidance has nonzero complementarity on this",
                "  repeated March+CaDiCaL-hard 3SAT-450 subset.",
                "- This reopens a cautious portfolio/generalization direction, but the",
                "  evidence is still a gate result on 13 selected hard instances rather",
                "  than a full benchmark claim.",
            ]
        )
    else:
        lines.extend(
            [
                "- Frozen Online-Consistent guidance does not solve any repeated",
                "  March+CaDiCaL-hard 3SAT-450 instance in this gate.",
                "- The current frozen workflow should not be positioned as a strong",
                "  performance/complementarity result without new benchmark evidence.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(COMBINED_CSV.relative_to(ROOT)),
            str(SEED_SUMMARY_CSV.relative_to(ROOT)),
            str(METHOD_SUMMARY_CSV.relative_to(ROOT)),
            str(OVERLAP_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen neural gate on repeated strong-solver-hard 3SAT-450 instances.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    file_keys = prepare_hard_subset(clean=args.clean)
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
    seed_rows = seed_summary(combined)
    seed_rows.to_csv(SEED_SUMMARY_CSV, index=False)
    method_rows = method_summary(seed_rows)
    method_rows.to_csv(METHOD_SUMMARY_CSV, index=False)
    overlap = overlap_summary(combined, file_keys=file_keys)
    overlap.to_csv(OVERLAP_CSV, index=False)
    write_doc(seed_rows, method_rows, overlap, file_keys=file_keys)
    print(seed_rows.to_string(index=False))
    print(method_rows.to_string(index=False))
    print(overlap.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
