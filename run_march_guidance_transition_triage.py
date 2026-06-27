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
SUBSET_ROOT = ROOT / "data/benchmark_march_guidance_transition_triage"
BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band/both_unknown_subset.csv"
DEFAULT_WORK_DIR = ROOT / "runs/analysis/benchmark_march_guidance_transition_triage"
DEFAULT_SUBSET_ROOT = ROOT / "data/benchmark_march_guidance_transition_triage"
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
    def source_glob(self) -> str:
        return f"data/benchmark_transition_band/{self.family}/{self.size}/*.cnf"


@dataclass(frozen=True)
class MethodSpec:
    method: str
    paper_name: str
    checkpoint: str


METHOD = MethodSpec(
    method="march_guided_one_shot",
    paper_name="March-Guided One-shot",
    checkpoint="runs/GNN_March_3SAT/best.pt",
)


def load_subsets(scope: str, sizes: list[int]) -> list[SubsetSpec]:
    if scope == "full":
        subsets = []
        for size in sizes:
            source_dir = SOURCE_ROOT / "3sat" / str(size)
            files = tuple(path.name for path in sorted(source_dir.glob("*.cnf")))
            if not files:
                raise FileNotFoundError(source_dir)
            subsets.append(SubsetSpec(family="3sat", size=size, file_keys=files))
        return subsets

    frame = pd.read_csv(BOTH_UNKNOWN_CSV)
    if frame.empty:
        raise ValueError(f"No both-unknown rows in {BOTH_UNKNOWN_CSV}")
    frame = frame[frame["size"].astype(int).isin(sizes)].copy()
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


def subset_target_dir(subset_root: Path, subset: SubsetSpec) -> Path:
    return subset_root / subset.family / str(subset.size)


def subset_eval_glob(subset_root: Path, subset: SubsetSpec) -> str:
    return str(subset_target_dir(subset_root, subset).relative_to(ROOT) / "*.cnf")


def prepare_subset(subset_root: Path, subset: SubsetSpec, clean: bool = False) -> None:
    target_dir = subset_target_dir(subset_root, subset)
    if clean and target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for file_key in subset.file_keys:
        source = subset.source_dir / file_key
        target = target_dir / file_key
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)


def raw_csv_path(raw_dir: Path, subset: SubsetSpec, seed: int) -> Path:
    return (raw_dir / subset.label / METHOD.method / f"seed{seed}.csv").resolve()


def build_command(raw_dir: Path, subset_root: Path, subset: SubsetSpec, seed: int, workers: int) -> list[str]:
    raw_csv = raw_csv_path(raw_dir, subset, seed)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    return [
        str(PYTHON),
        "evaluate_guided_solver.py",
        "--config-name",
        "config_eval_guided_solver",
        f"dataset.eval_path={subset_eval_glob(subset_root, subset)}",
        f"save_file={raw_csv}",
        f"solver.num_workers={workers}",
        "solver.solver=march",
        "solver.params.cpu-lim=60",
        f"+solver.params.seed={seed}",
        f"checkpoint={METHOD.checkpoint}",
        "feedback_refinement.enabled=False",
        "dataset.lazy=True",
        "loader.batch_size=10",
    ]


def run_eval(raw_dir: Path, subset_root: Path, subset: SubsetSpec, seed: int, workers: int, dry_run: bool, skip_existing: bool) -> Path:
    raw_csv = raw_csv_path(raw_dir, subset, seed)
    if skip_existing and raw_csv.exists():
        print(f"skip existing {raw_csv.relative_to(ROOT)}", flush=True)
        return raw_csv
    command = build_command(raw_dir, subset_root, subset, seed=seed, workers=workers)
    print(" ".join(command), flush=True)
    if dry_run:
        return raw_csv
    subprocess.run(command, cwd=ROOT, check=True)
    if not raw_csv.exists():
        raise FileNotFoundError(raw_csv)
    return raw_csv


def load_raw(subset: SubsetSpec, seed: int, raw_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(raw_csv).copy()
    frame["family"] = subset.family
    frame["size"] = subset.size
    frame["subset_label"] = subset.label
    frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
    frame["method"] = METHOD.method
    frame["paper_name"] = METHOD.paper_name
    frame["seed"] = seed
    frame["solved"] = frame["Result"].astype(str).isin(SOLVED_RESULTS)
    frame["raw_csv"] = str(raw_csv.relative_to(ROOT))
    for column in ["time", "CPU time", "GPU time", "conflicts", "decisions", "propagations"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def summarize(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for (family, size, seed), group in combined.groupby(["family", "size", "seed"], sort=True):
        summary_rows.append(
            {
                "family": family,
                "size": int(size),
                "method": METHOD.method,
                "paper_name": METHOD.paper_name,
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
        seeds = int(group["seed"].nunique())
        solved_seeds = int(group["solved"].sum())
        overlap_rows.append(
            {
                "family": family,
                "size": int(size),
                "file_key": file_key,
                "seeds": seeds,
                "solved_seeds": solved_seeds,
                "solved_all": solved_seeds == seeds,
                "time_mean": float(group["time"].mean()),
                "result_values": ",".join(sorted(map(str, group["Result"].unique()))),
            }
        )
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


def write_doc(
    doc_path: Path,
    subset_csv: Path,
    combined_csv: Path,
    summary_csv: Path,
    overlap_csv: Path,
    scope: str,
    subset_rows: pd.DataFrame,
    summary: pd.DataFrame,
    overlap: pd.DataFrame,
) -> None:
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
        .agg(n=("file_key", "count"), strict_solved=("solved_all", "sum"))
        .reset_index()
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# March-Guided Transition-Band Triage",
        "",
        "Scope: frozen March-trained one-shot guidance on transition-band",
        f"`{scope}` instances. This",
        "uses the existing `runs/GNN_March_3SAT/best.pt` checkpoint and",
        "`solvers/march_weighted/march_nh`; it does not train or tune models.",
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
        "Solved means solved in all requested seeds.",
        "",
        *markdown_table(strict, ["family", "size", "n", "strict_solved"]),
        "",
        "## Decision",
        "",
    ]
    if int(strict["strict_solved"].sum()) > 0:
        solved = overlap[overlap["solved_all"]]
        lines.extend(
            [
                "- Frozen March-guided one-shot has nonzero solves on the transition-band",
                "  March/CaDiCaL both-unknown subset.",
                "- This is the first low-cost performance signal in the current gate",
                "  family. It requires repeated strong-solver confirmation and a larger",
                "  benchmark before becoming a top-conference claim.",
                "- Strict solved keys: "
                + ", ".join(f"`{row.family}-{row.size}/{row.file_key}`" for row in solved.itertuples())
                + ".",
            ]
        )
    else:
        lines.extend(
            [
                "- Frozen March-guided one-shot solves no transition-band instance that",
                "  unguided March and CaDiCaL both left unsolved.",
                "- Existing March-guided artifacts therefore do not rescue the current",
                "  performance/complementarity route.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(subset_csv.relative_to(ROOT)),
            str(combined_csv.relative_to(ROOT)),
            str(summary_csv.relative_to(ROOT)),
            str(overlap_csv.relative_to(ROOT)),
            "```",
        ]
    )
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen March-guided one-shot triage on transition-band both-unknown instances.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    parser.add_argument("--scope", choices=["both_unknown", "full"], default="both_unknown")
    parser.add_argument("--sizes", type=int, nargs="+", default=[410, 425, 440])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    work_dir = DEFAULT_WORK_DIR if args.scope == "both_unknown" else ROOT / "runs/analysis/benchmark_march_guidance_transition_full"
    subset_root = DEFAULT_SUBSET_ROOT if args.scope == "both_unknown" else ROOT / "data/benchmark_march_guidance_transition_full"
    raw_dir = work_dir / "raw"
    subset_csv = work_dir / ("both_unknown_subset.csv" if args.scope == "both_unknown" else "full_subset.csv")
    combined_csv = work_dir / "combined.csv"
    summary_csv = work_dir / "summary.csv"
    overlap_csv = work_dir / "overlap.csv"
    doc_path = ROOT / ("docs/benchmark_march_guidance_transition_triage.md" if args.scope == "both_unknown" else "docs/benchmark_march_guidance_transition_full.md")

    if args.clean and work_dir.exists():
        shutil.rmtree(work_dir)
    subsets = load_subsets(scope=args.scope, sizes=args.sizes)
    subset_rows = pd.DataFrame(
        [{"family": subset.family, "size": subset.size, "file_key": file_key} for subset in subsets for file_key in subset.file_keys]
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    subset_rows.to_csv(subset_csv, index=False)

    frames = []
    for subset in subsets:
        prepare_subset(subset_root, subset, clean=args.clean)
        for seed in args.seeds:
            raw_csv = run_eval(raw_dir, subset_root, subset, seed=seed, workers=args.workers, dry_run=args.dry_run, skip_existing=args.skip_existing)
            if not args.dry_run:
                frames.append(load_raw(subset, seed=seed, raw_csv=raw_csv))
    if args.dry_run:
        print(subset_rows.to_string(index=False))
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(combined_csv, index=False)
    summary, overlap = summarize(combined)
    summary.to_csv(summary_csv, index=False)
    overlap.to_csv(overlap_csv, index=False)
    write_doc(doc_path, subset_csv, combined_csv, summary_csv, overlap_csv, args.scope, subset_rows, summary, overlap)
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    print(doc_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
