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
from src.policy.evaluate import compute_solver_stats, sample_var_params


ROOT = Path(__file__).resolve().parent
BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band/both_unknown_subset.csv"
SOURCE_ROOT = ROOT / "data/benchmark_transition_band"
SUBSET_ROOT = ROOT / "data/benchmark_march_sample_portfolio_triage"
WORK_DIR = ROOT / "runs/analysis/benchmark_march_sample_portfolio_triage"
SUBSET_CSV = WORK_DIR / "both_unknown_subset.csv"
RAW_CSV = WORK_DIR / "raw_samples.csv"
INSTANCE_CSV = WORK_DIR / "instance_summary.csv"
SIZE_CSV = WORK_DIR / "size_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_sample_portfolio_triage.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def prepare_subset(clean: bool = False) -> pd.DataFrame:
    frame = pd.read_csv(BOTH_UNKNOWN_CSV)
    if frame.empty:
        raise ValueError(f"No both-unknown rows in {BOTH_UNKNOWN_CSV}")
    if clean and SUBSET_ROOT.exists():
        shutil.rmtree(SUBSET_ROOT)
    for row in frame.itertuples(index=False):
        family = str(row.family)
        size = int(row.size)
        file_key = str(row.file_key)
        source = SOURCE_ROOT / family / str(size) / file_key
        target_dir = SUBSET_ROOT / family / str(size)
        target = target_dir / file_key
        target_dir.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)
    return frame


def run_size(size: int, num_samples: int, workers: int, seed: int, device: str) -> pd.DataFrame:
    pattern = str((SUBSET_ROOT / "3sat" / str(size) / "*.cnf").relative_to(ROOT))
    dataset = DimacsCNFDataset(pattern, transform=TRANSFORM, lazy=True)
    loader = DataLoader(dataset=dataset, batch_size=10, num_workers=0, shuffle=False)
    data_list = sample_var_params(
        model=MODEL,
        loader=loader,
        device=device,
        use_mode=False,
        num_samples=num_samples,
        scale_sigma=float(MODEL_CFG.scale_sigma),
        add_timing=True,
    )
    stats = compute_solver_stats(
        dataset=dataset,
        data_list=data_list,
        num_workers=workers,
        solver="march",
        **{"cpu-lim": 60, "seed": seed},
    )
    stats["family"] = "3sat"
    stats["size"] = size
    stats["file_key"] = stats["file"].astype(str).map(lambda value: Path(value).name)
    stats["solved"] = stats["Result"].astype(str).isin(SOLVED)
    return stats


def solver_time_column(frame: pd.DataFrame) -> str:
    if "time" in frame.columns:
        return "time"
    if "CPU time" in frame.columns:
        return "CPU time"
    raise KeyError("Expected either 'time' or 'CPU time' in solver output.")


def summarize(raw: pd.DataFrame, num_samples: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    time_col = solver_time_column(raw)
    if "solved" not in raw.columns:
        raw = raw.copy()
        raw["solved"] = raw["Result"].astype(str).isin(SOLVED)
    instance_rows = []
    for (family, size, file_key), group in raw.groupby(["family", "size", "file_key"], sort=True):
        solved_samples = int(group["solved"].sum())
        solved = group[group["solved"]].copy()
        best_time = float(solved[time_col].min()) if not solved.empty else float(group[time_col].min())
        best_sample = int(solved.sort_values(time_col).iloc[0]["sample_id"]) if not solved.empty else -1
        instance_rows.append(
            {
                "family": family,
                "size": int(size),
                "file_key": file_key,
                "samples": int(len(group)),
                "solved_samples": solved_samples,
                "solved_any": solved_samples > 0,
                "best_time": best_time,
                "best_sample_id": best_sample,
                "result_values": ",".join(sorted(map(str, group["Result"].unique()))),
            }
        )
    instance = pd.DataFrame(instance_rows)
    size_rows = []
    for (family, size), group in instance.groupby(["family", "size"], sort=True):
        size_rows.append(
            {
                "family": family,
                "size": int(size),
                "instances": int(len(group)),
                "num_samples": int(num_samples),
                "solved_any": int(group["solved_any"].sum()),
                "mean_solved_samples": float(group["solved_samples"].mean()),
                "max_solved_samples": int(group["solved_samples"].max()),
            }
        )
    return instance, pd.DataFrame(size_rows)


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


def write_doc(subset: pd.DataFrame, instance: pd.DataFrame, size_summary: pd.DataFrame, num_samples: int, seed: int) -> None:
    solved = instance[instance["solved_any"]]
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# March Sample-Portfolio Triage",
        "",
        "Scope: stochastic sampling diagnostic for the existing March-trained",
        "policy. It samples multiple weighted-March guidances per transition-band",
        "strong-union both-unknown instance. This does not train or tune models.",
        "",
        f"Samples per instance: {num_samples}; sampling seed: {seed}.",
        "",
        "## Input Subset",
        "",
        *markdown_table(subset, ["family", "size", "file_key"]),
        "",
        "## Size Summary",
        "",
        *markdown_table(size_summary, ["family", "size", "instances", "num_samples", "solved_any", "mean_solved_samples", "max_solved_samples"]),
        "",
        "## Instance Summary",
        "",
        *markdown_table(instance, ["family", "size", "file_key", "samples", "solved_samples", "solved_any", "best_time", "best_sample_id", "result_values"]),
        "",
        "## Decision",
        "",
    ]
    if not solved.empty:
        lines.extend(
            [
                "- Sampled March guidance has nonzero solves on the strong-union",
                "  both-unknown transition subset.",
                "- This is a concrete model-side signal for a neural portfolio / sample",
                "  selection route. The next step is to repeat the sample seed and train",
                "  a selector for these sampled guidances.",
            ]
        )
    else:
        lines.extend(
            [
                "- Sampled March guidance still solves no strong-union both-unknown",
                "  transition instance.",
                "- This weakens the neural portfolio route for the current checkpoint;",
                "  new training objectives are required.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(RAW_CSV.relative_to(ROOT)),
            str(INSTANCE_CSV.relative_to(ROOT)),
            str(SIZE_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run sampled March-guidance portfolio triage.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--num-samples", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="Reuse raw_samples.csv and regenerate summaries/doc without rerunning solvers.",
    )
    args = parser.parse_args()

    global MODEL, TRANSFORM, MODEL_CFG
    set_seed(args.seed)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    if args.summarize_only:
        if not RAW_CSV.exists():
            raise FileNotFoundError(RAW_CSV)
        subset = pd.read_csv(SUBSET_CSV) if SUBSET_CSV.exists() else pd.read_csv(BOTH_UNKNOWN_CSV)
        raw = pd.read_csv(RAW_CSV)
    else:
        subset = prepare_subset(clean=args.clean)
        subset.to_csv(SUBSET_CSV, index=False)
        MODEL, TRANSFORM, MODEL_CFG = load_checkpoint(args.checkpoint, var_output=True)

        frames = []
        for size in sorted(subset["size"].astype(int).unique()):
            frames.append(run_size(size=size, num_samples=args.num_samples, workers=args.workers, seed=args.seed, device=args.device))
        raw = pd.concat(frames, ignore_index=True)
        raw.to_csv(RAW_CSV, index=False)
    instance, size_summary = summarize(raw, num_samples=args.num_samples)
    instance.to_csv(INSTANCE_CSV, index=False)
    size_summary.to_csv(SIZE_CSV, index=False)
    write_doc(subset, instance, size_summary, num_samples=args.num_samples, seed=args.seed)
    print(size_summary.to_string(index=False))
    print(instance.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
