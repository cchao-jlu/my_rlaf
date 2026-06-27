from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PYTHON = Path("/home/sunshixin/anaconda3/envs/rlaf/bin/python")
SOURCE_ROOT = ROOT / "data/benchmark_transition_band"
SUBSET_ROOT = ROOT / "data/benchmark_transition_band_neural_triage"
BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band/both_unknown_subset.csv"
WORK_DIR = ROOT / "runs/analysis/benchmark_transition_band_neural_triage"
RAW_DIR = WORK_DIR / "raw"
SUBSET_CSV = WORK_DIR / "both_unknown_subset.csv"
COMBINED_CSV = WORK_DIR / "combined.csv"
SUMMARY_CSV = WORK_DIR / "summary.csv"
OVERLAP_CSV = WORK_DIR / "overlap.csv"
DOC_PATH = ROOT / "docs/benchmark_transition_band_neural_triage.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


@dataclass(frozen=True)
class SubsetSpec:
    family: str
    size: int
    file_keys: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{self.family}_{self.size}"

    @property
    def source_dir(self) -> Path:
        return SOURCE_ROOT / self.family / str(self.size)

    @property
    def target_dir(self) -> Path:
        return SUBSET_ROOT / self.family / str(self.size)

    @property
    def eval_glob(self) -> str:
        return f"data/benchmark_transition_band_neural_triage/{self.family}/{self.size}/*.cnf"


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
        extra_overrides=("feedback_refinement.local_reopen_candidate_manifest=null",),
    ),
]


def load_subsets() -> list[SubsetSpec]:
    frame = pd.read_csv(BOTH_UNKNOWN_CSV)
    if frame.empty:
        raise ValueError(f"No both-unknown rows in {BOTH_UNKNOWN_CSV}")
    subsets = []
    for (family, size), group in frame.groupby(["family", "size"], sort=True):
        subsets.append(
            SubsetSpec(
                family=str(family),
                size=int(size),
                file_keys=tuple(group["file_key"].astype(str)),
            )
        )
    return subsets


def prepare_subset(subset: SubsetSpec, clean: bool = False) -> None:
    if clean and subset.target_dir.exists():
        shutil.rmtree(subset.target_dir)
    subset.target_dir.mkdir(parents=True, exist_ok=True)
    for file_key in subset.file_keys:
        source = subset.source_dir / file_key
        target = subset.target_dir / file_key
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)


def raw_csv_path(subset: SubsetSpec, method: MethodSpec, seed: int) -> Path:
    return (RAW_DIR / subset.label / method.method / f"seed{seed}.csv").resolve()


def build_command(subset: SubsetSpec, method: MethodSpec, seed: int, workers: int) -> list[str]:
    raw_csv = raw_csv_path(subset, method, seed)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    return [
        str(PYTHON),
        "evaluate_guided_solver.py",
        "--config-name",
        method.config_name,
        f"dataset.eval_path={subset.eval_glob}",
        f"save_file={raw_csv}",
        f"solver.num_workers={workers}",
        "solver.params.cpu-lim=60",
        "solver.params.rnd-freq=0.0",
        "solver.params.K=0.1",
        f"+solver.params.seed={seed}",
        *method.extra_overrides,
    ]


def run_eval(subset: SubsetSpec, method: MethodSpec, seed: int, workers: int, dry_run: bool, skip_existing: bool) -> Path:
    raw_csv = raw_csv_path(subset, method, seed)
    if skip_existing and raw_csv.exists():
        print(f"skip existing {raw_csv.relative_to(ROOT)}", flush=True)
        return raw_csv
    command = build_command(subset, method, seed=seed, workers=workers)
    print(" ".join(command), flush=True)
    if dry_run:
        return raw_csv
    subprocess.run(command, cwd=ROOT, check=True)
    if not raw_csv.exists():
        raise FileNotFoundError(raw_csv)
    return raw_csv


def load_raw(subset: SubsetSpec, method: MethodSpec, seed: int, raw_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_csv).copy()
    frame["family"] = subset.family
    frame["size"] = subset.size
    frame["subset_label"] = subset.label
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["method"] = method.method
    frame["paper_name"] = method.paper_name
    frame["seed"] = seed
    frame["solved"] = frame["Result"].astype(str).isin(SOLVED_RESULTS)
    frame["raw_csv"] = str(raw_csv.relative_to(ROOT))
    for column in ["time", "CPU time", "GPU time", "conflicts", "decisions", "propagations"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def summarize(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for (family, size, method, paper_name, seed), group in combined.groupby(
        ["family", "size", "method", "paper_name", "seed"],
        sort=True,
    ):
        summary_rows.append(
            {
                "family": family,
                "size": int(size),
                "method": method,
                "paper_name": paper_name,
                "seed": int(seed),
                "n": int(len(group)),
                "solved": int(group["solved"].sum()),
                "unknown": int((~group["solved"]).sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
            }
        )
    summary = pd.DataFrame(summary_rows)

    overlap_rows = []
    for (family, size, file_key), group in combined.groupby(["family", "size", "file_key"], sort=True):
        row: dict[str, object] = {"family": family, "size": int(size), "file_key": file_key}
        pattern = []
        for method in METHODS:
            method_group = group[group["method"] == method.method]
            seeds = int(method_group["seed"].nunique())
            solved_seeds = int(method_group["solved"].sum())
            solved_all = solved_seeds == seeds
            row[f"{method.method}_solved_seeds"] = solved_seeds
            row[f"{method.method}_solved_all"] = solved_all
            row[f"{method.method}_time_mean"] = float(method_group["time"].mean())
            row[f"{method.method}_result_values"] = ",".join(sorted(map(str, method_group["Result"].unique())))
            pattern.append("1" if solved_all else "0")
        row["pattern"] = "".join(pattern)
        overlap_rows.append(row)
    return summary, pd.DataFrame(overlap_rows)


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


def write_doc(subset_rows: pd.DataFrame, summary: pd.DataFrame, overlap: pd.DataFrame) -> None:
    aggregate = (
        summary.groupby(["family", "size", "paper_name"], sort=True)
        .agg(
            seeds=("seed", "nunique"),
            solved_mean=("solved", "mean"),
            solved_min=("solved", "min"),
            solved_max=("solved", "max"),
            mean_time_mean=("mean_time", "mean"),
        )
        .reset_index()
    )
    strict = (
        overlap.groupby(["family", "size"], sort=True)
        .agg(
            n=("file_key", "count"),
            one_shot_strict=("one_shot_solved_all", "sum"),
            online_strict=("online_consistent_boundary400_solved_all", "sum"),
        )
        .reset_index()
    )
    online_only = (
        overlap.groupby(["family", "size"], sort=True)
        .apply(
            lambda group: int(((~group["one_shot_solved_all"]) & group["online_consistent_boundary400_solved_all"]).sum()),
            include_groups=False,
        )
        .reset_index(name="online_only_strict")
    )
    strict = strict.merge(online_only, on=["family", "size"], how="left")
    pattern_counts = overlap.groupby(["family", "size", "pattern"], sort=True).size().reset_index(name="count")

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Transition-Band Frozen-Neural Triage",
        "",
        "Scope: frozen neural triage on random 3SAT transition-band instances",
        "that March and CaDiCaL both left unsolved in the first strong-solver",
        "gate. This does not train models, tune thresholds, or migrate Local",
        "Boundary Correction.",
        "",
        "## Both-Unknown Input Subset",
        "",
        *markdown_table(subset_rows, ["family", "size", "file_key"]),
        "",
        "## Method Summary",
        "",
        *markdown_table(aggregate, ["family", "size", "paper_name", "seeds", "solved_mean", "solved_min", "solved_max", "mean_time_mean"]),
        "",
        "## Strict Complement Summary",
        "",
        "Solved means solved in all requested neural seeds. Pattern order is `One-shot / Online-Consistent Selector`.",
        "",
        *markdown_table(strict, ["family", "size", "n", "one_shot_strict", "online_strict", "online_only_strict"]),
        "",
        "## Pattern Counts",
        "",
        *markdown_table(pattern_counts, ["family", "size", "pattern", "count"]),
        "",
        "## Decision",
        "",
    ]
    if int(strict["online_strict"].sum()) > 0:
        solved_keys = overlap[overlap["online_consistent_boundary400_solved_all"]]
        lines.extend(
            [
                "- Frozen Online-Consistent guidance has nonzero solves on the",
                "  transition-band strong-solver both-unknown subset.",
                "- This is only a triage signal. It requires repeated March/CaDiCaL",
                "  confirmation and a larger generated benchmark before any performance",
                "  claim.",
                "- Online strict solved keys: "
                + ", ".join(f"`{row.family}-{row.size}/{row.file_key}`" for row in solved_keys.itertuples())
                + ".",
            ]
        )
    else:
        lines.extend(
            [
                "- Frozen Online-Consistent guidance solves no transition-band instance",
                "  that March and CaDiCaL both left unsolved.",
                "- This further weakens the current frozen-workflow performance route.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(SUBSET_CSV.relative_to(ROOT)),
            str(COMBINED_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            str(OVERLAP_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen neural triage on transition-band strong-solver both-unknown instances.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    subsets = load_subsets()
    subset_rows = pd.DataFrame(
        [{"family": subset.family, "size": subset.size, "file_key": file_key} for subset in subsets for file_key in subset.file_keys]
    )
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    subset_rows.to_csv(SUBSET_CSV, index=False)

    frames = []
    for subset in subsets:
        prepare_subset(subset, clean=args.clean)
        for seed in args.seeds:
            for method in METHODS:
                raw_csv = run_eval(subset, method, seed=seed, workers=args.workers, dry_run=args.dry_run, skip_existing=args.skip_existing)
                if not args.dry_run:
                    frames.append(load_raw(subset, method, seed=seed, raw_csv=raw_csv))
    if args.dry_run:
        print(subset_rows.to_string(index=False))
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(COMBINED_CSV, index=False)
    summary, overlap = summarize(combined)
    summary.to_csv(SUMMARY_CSV, index=False)
    overlap.to_csv(OVERLAP_CSV, index=False)
    write_doc(subset_rows, summary, overlap)
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
