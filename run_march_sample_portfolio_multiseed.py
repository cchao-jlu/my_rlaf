from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import random
import shutil
import time
from pathlib import Path
from typing import Iterator

import fcntl

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
SUBSET_ROOT = ROOT / "data/benchmark_march_sample_portfolio_multiseed"
WORK_DIR = ROOT / "runs/analysis/benchmark_march_sample_portfolio_multiseed"
RAW_DIR = WORK_DIR / "raw"
INSTANCE_DIR = WORK_DIR / "instances"
RAW_ALL_CSV = WORK_DIR / "raw_samples_all.csv"
INSTANCE_SEED_CSV = WORK_DIR / "instance_seed_summary.csv"
INSTANCE_ORACLE_CSV = WORK_DIR / "instance_oracle_summary.csv"
SIZE_SEED_CSV = WORK_DIR / "size_seed_summary.csv"
SIZE_ORACLE_CSV = WORK_DIR / "size_oracle_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_sample_portfolio_multiseed.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


@contextlib.contextmanager
def work_dir_lock(work_dir: Path) -> Iterator[None]:
    lock_path = work_dir / ".run_march_sample_portfolio_multiseed.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                f"Another sample-portfolio runner is already using {work_dir}. "
                "Wait for it to finish, or use a separate --out-dir namespace."
            ) from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def configure_scope(scope: str) -> None:
    global BOTH_UNKNOWN_CSV
    global SOURCE_ROOT
    global SUBSET_ROOT
    global WORK_DIR
    global RAW_DIR
    global INSTANCE_DIR
    global RAW_ALL_CSV
    global INSTANCE_SEED_CSV
    global INSTANCE_ORACLE_CSV
    global SIZE_SEED_CSV
    global SIZE_ORACLE_CSV
    global DOC_PATH

    if scope == "transition":
        BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band/both_unknown_subset.csv"
        SOURCE_ROOT = ROOT / "data/benchmark_transition_band"
        SUBSET_ROOT = ROOT / "data/benchmark_march_sample_portfolio_multiseed"
        WORK_DIR = ROOT / "runs/analysis/benchmark_march_sample_portfolio_multiseed"
        DOC_PATH = ROOT / "docs/benchmark_march_sample_portfolio_multiseed.md"
    elif scope == "expanded":
        BOTH_UNKNOWN_CSV = ROOT / "runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv"
        SOURCE_ROOT = ROOT / "data/benchmark_transition_band_expanded"
        SUBSET_ROOT = ROOT / "data/benchmark_march_expanded_sample_portfolio_oracle"
        WORK_DIR = ROOT / "runs/analysis/benchmark_march_expanded_sample_portfolio_oracle"
        DOC_PATH = ROOT / "docs/benchmark_march_expanded_sample_portfolio_oracle.md"
    else:
        raise ValueError(f"Unknown scope: {scope}")

    RAW_DIR = WORK_DIR / "raw"
    INSTANCE_DIR = WORK_DIR / "instances"
    RAW_ALL_CSV = WORK_DIR / "raw_samples_all.csv"
    INSTANCE_SEED_CSV = WORK_DIR / "instance_seed_summary.csv"
    INSTANCE_ORACLE_CSV = WORK_DIR / "instance_oracle_summary.csv"
    SIZE_SEED_CSV = WORK_DIR / "size_seed_summary.csv"
    SIZE_ORACLE_CSV = WORK_DIR / "size_oracle_summary.csv"


def configure_custom_paths(
    input_csv: Path | None = None,
    source_root: Path | None = None,
    subset_root: Path | None = None,
    out_dir: Path | None = None,
    doc_path: Path | None = None,
) -> None:
    global BOTH_UNKNOWN_CSV
    global SOURCE_ROOT
    global SUBSET_ROOT
    global WORK_DIR
    global RAW_DIR
    global INSTANCE_DIR
    global RAW_ALL_CSV
    global INSTANCE_SEED_CSV
    global INSTANCE_ORACLE_CSV
    global SIZE_SEED_CSV
    global SIZE_ORACLE_CSV
    global DOC_PATH

    if input_csv is not None:
        BOTH_UNKNOWN_CSV = input_csv
    if source_root is not None:
        SOURCE_ROOT = source_root
    if subset_root is not None:
        SUBSET_ROOT = subset_root
    if out_dir is not None:
        WORK_DIR = out_dir
    if doc_path is not None:
        DOC_PATH = doc_path

    RAW_DIR = WORK_DIR / "raw"
    INSTANCE_DIR = WORK_DIR / "instances"
    RAW_ALL_CSV = WORK_DIR / "raw_samples_all.csv"
    INSTANCE_SEED_CSV = WORK_DIR / "instance_seed_summary.csv"
    INSTANCE_ORACLE_CSV = WORK_DIR / "instance_oracle_summary.csv"
    SIZE_SEED_CSV = WORK_DIR / "size_seed_summary.csv"
    SIZE_ORACLE_CSV = WORK_DIR / "size_oracle_summary.csv"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def prepare_subset(clean: bool = False, limit_instances: int = 0) -> pd.DataFrame:
    frame = pd.read_csv(BOTH_UNKNOWN_CSV)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input CSV is missing columns: {sorted(missing)}")
    if limit_instances > 0:
        frame = frame.head(limit_instances).copy()
    if frame.empty:
        raise ValueError(f"No both-unknown rows in {BOTH_UNKNOWN_CSV}")
    if clean and SUBSET_ROOT.exists():
        shutil.rmtree(SUBSET_ROOT)
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


def solver_time_column(frame: pd.DataFrame) -> str:
    if "time" in frame.columns:
        return "time"
    if "CPU time" in frame.columns:
        return "CPU time"
    raise KeyError("Expected either 'time' or 'CPU time' in solver output.")


def capped_cpu_series(frame: pd.DataFrame, full_cpu_lim: float) -> pd.Series:
    time_col = solver_time_column(frame)
    values = pd.to_numeric(frame[time_col], errors="coerce").fillna(full_cpu_lim)
    capped = values.clip(upper=full_cpu_lim)
    solved = frame["Result"].astype(str).isin(SOLVED)
    return capped.where(solved, full_cpu_lim)


def run_size(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    num_samples: int,
    workers: int,
    sample_seed: int,
    solver_seed: int,
    device: str,
    full_cpu_lim: float,
    file_keys: set[str] | None = None,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str = "",
) -> pd.DataFrame:
    set_seed(sample_seed)
    if file_keys:
        size_dir = SUBSET_ROOT / "3sat" / str(size)
        files = sorted(size_dir / key for key in file_keys if (size_dir / key).exists())
        if not files:
            raise FileNotFoundError(f"No requested file keys found under {size_dir}: {sorted(file_keys)}")
        if len(files) != 1:
            raise ValueError("Focused runs currently support exactly one file key.")
        pattern = str(files[0].relative_to(ROOT))
    else:
        pattern = str((SUBSET_ROOT / "3sat" / str(size) / "*.cnf").relative_to(ROOT))
    dataset = DimacsCNFDataset(pattern, transform=transform, lazy=True)
    loader = DataLoader(dataset=dataset, batch_size=10, num_workers=0, shuffle=False)
    sample_start = time.time()
    data_list = sample_var_params(
        model=model,
        loader=loader,
        device=device,
        use_mode=False,
        num_samples=num_samples,
        scale_sigma=float(model_cfg.scale_sigma),
        add_timing=True,
    )
    sample_wall_time = time.time() - sample_start
    stats = compute_solver_stats(
        dataset=dataset,
        data_list=data_list,
        num_workers=workers,
        solver="march",
        **{"cpu-lim": full_cpu_lim, "seed": solver_seed},
    )
    stats["family"] = "3sat"
    stats["size"] = size
    stats["file_key"] = stats["file"].astype(str).map(lambda value: Path(value).name)
    stats["sample_seed"] = sample_seed
    stats["solver_seed"] = solver_seed
    stats["num_samples_generated"] = num_samples
    stats["full_cpu_lim"] = float(full_cpu_lim)
    stats["source_checkpoint"] = str(checkpoint_path) if checkpoint_path is not None else ""
    stats["source_checkpoint_sha256"] = str(checkpoint_sha256)
    stats["neural_generation_wall_time"] = float(sample_wall_time)
    stats["solved"] = stats["Result"].astype(str).isin(SOLVED)
    stats["capped_solver_cpu"] = capped_cpu_series(stats, full_cpu_lim=full_cpu_lim)
    return stats


def run_seed_size(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    sample_seed: int,
    solver_seed: int,
    num_samples: int,
    workers: int,
    device: str,
    full_cpu_lim: float,
    file_keys: set[str] | None = None,
    force: bool = False,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str = "",
) -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    key_suffix = ""
    if file_keys:
        stable_keys = "-".join(Path(key).stem for key in sorted(file_keys))
        key_suffix = f"_{stable_keys}"
    raw_path = RAW_DIR / f"seed{sample_seed}_size{size}{key_suffix}_samples{num_samples}.csv"
    if raw_path.exists() and not force:
        return pd.read_csv(raw_path)

    raw = run_size(
        model=model,
        transform=transform,
        model_cfg=model_cfg,
        size=size,
        num_samples=num_samples,
        workers=workers,
        sample_seed=sample_seed,
        solver_seed=solver_seed,
        device=device,
        full_cpu_lim=full_cpu_lim,
        file_keys=file_keys,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
    )
    raw.to_csv(raw_path, index=False)
    return raw


def instance_stem(size: int, file_key: str, sample_seed: int, num_samples: int) -> str:
    return f"size{size}_{Path(file_key).stem}_seed{sample_seed}_samples{num_samples}"


def instance_paths(size: int, file_key: str, sample_seed: int, num_samples: int) -> tuple[Path, Path]:
    stem = instance_stem(size=size, file_key=file_key, sample_seed=sample_seed, num_samples=num_samples)
    return INSTANCE_DIR / f"{stem}_raw.csv", INSTANCE_DIR / f"{stem}_summary.csv"


def summarize_instance_seed(raw: pd.DataFrame, num_samples: int, full_cpu_lim: float) -> dict:
    if raw.empty:
        raise ValueError("Cannot summarize an empty raw frame.")
    time_col = solver_time_column(raw)
    frame = raw.copy()
    if "solved" not in frame.columns:
        frame["solved"] = frame["Result"].astype(str).isin(SOLVED)
    if "capped_solver_cpu" not in frame.columns:
        frame["capped_solver_cpu"] = capped_cpu_series(frame, full_cpu_lim=full_cpu_lim)
    solved = frame[frame["solved"]]
    first = frame.iloc[0]
    return {
        "family": str(first["family"]),
        "size": int(first["size"]),
        "file_key": str(first["file_key"]),
        "sample_seed": int(first["sample_seed"]),
        "solver_seed": int(first["solver_seed"]),
        "samples": int(len(frame)),
        "samples_per_seed": int(num_samples),
        "solved_samples": int(frame["solved"].sum()),
        "solved_any": bool(frame["solved"].any()),
        "best_time": float(solved[time_col].min()) if not solved.empty else float(frame[time_col].min()),
        "best_sample_id": int(solved.sort_values(time_col).iloc[0]["sample_id"]) if not solved.empty else -1,
        "full_cpu_lim": float(full_cpu_lim),
        "capped_solver_cpu_total": float(frame["capped_solver_cpu"].sum()),
        "neural_generation_wall_time": float(frame["neural_generation_wall_time"].max())
        if "neural_generation_wall_time" in frame.columns
        else float("nan"),
    }


def run_seed_instance(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    file_key: str,
    sample_seed: int,
    solver_seed: int,
    num_samples: int,
    workers: int,
    device: str,
    full_cpu_lim: float,
    force: bool = False,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str = "",
) -> pd.DataFrame:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    raw_path, summary_path = instance_paths(
        size=size,
        file_key=file_key,
        sample_seed=sample_seed,
        num_samples=num_samples,
    )
    if raw_path.exists() and summary_path.exists() and not force:
        return pd.read_csv(raw_path)
    raw = run_size(
        model=model,
        transform=transform,
        model_cfg=model_cfg,
        size=size,
        num_samples=num_samples,
        workers=workers,
        sample_seed=sample_seed,
        solver_seed=solver_seed,
        device=device,
        full_cpu_lim=full_cpu_lim,
        file_keys={file_key},
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
    )
    summary = summarize_instance_seed(raw, num_samples=num_samples, full_cpu_lim=full_cpu_lim)
    raw.to_csv(raw_path, index=False)
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    return raw


def migrate_size_raw_to_instances(sample_seeds: list[int], num_samples: int, full_cpu_lim: float) -> int:
    migrated = 0
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    for sample_seed in sample_seeds:
        for raw_path in sorted(RAW_DIR.glob(f"seed{sample_seed}_size*_samples{num_samples}.csv")):
            raw = pd.read_csv(raw_path)
            if raw.empty:
                continue
            if "solved" not in raw.columns:
                raw["solved"] = raw["Result"].astype(str).isin(SOLVED)
            if "capped_solver_cpu" not in raw.columns:
                raw["capped_solver_cpu"] = capped_cpu_series(raw, full_cpu_lim=full_cpu_lim)
            for (size, file_key), group in raw.groupby(["size", "file_key"], sort=True):
                instance_raw_path, instance_summary_path = instance_paths(
                    size=int(size),
                    file_key=str(file_key),
                    sample_seed=sample_seed,
                    num_samples=num_samples,
                )
                if instance_raw_path.exists() and instance_summary_path.exists():
                    continue
                instance_raw = group.copy()
                summary = summarize_instance_seed(
                    instance_raw,
                    num_samples=num_samples,
                    full_cpu_lim=full_cpu_lim,
                )
                instance_raw.to_csv(instance_raw_path, index=False)
                pd.DataFrame([summary]).to_csv(instance_summary_path, index=False)
                migrated += 1
    return migrated


def summarize(raw: pd.DataFrame, num_samples: int, full_cpu_lim: float = 60.0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    time_col = solver_time_column(raw)
    raw = raw.copy()
    if "solved" not in raw.columns:
        raw["solved"] = raw["Result"].astype(str).isin(SOLVED)
    if "capped_solver_cpu" not in raw.columns:
        raw["capped_solver_cpu"] = capped_cpu_series(raw, full_cpu_lim=full_cpu_lim)

    checkpoint_columns: dict[str, str] = {}
    for column in ["source_checkpoint", "source_checkpoint_sha256"]:
        if column in raw.columns:
            values = sorted(set(str(value) for value in raw[column].dropna() if str(value)))
            checkpoint_columns[column] = values[0] if len(values) == 1 else ""

    instance_seed_rows = []
    for (family, size, file_key, sample_seed), group in raw.groupby(["family", "size", "file_key", "sample_seed"], sort=True):
        solved = group[group["solved"]]
        instance_seed_rows.append(
            {
                "family": family,
                "size": int(size),
                "file_key": file_key,
                "sample_seed": int(sample_seed),
                "samples": int(len(group)),
                "solved_samples": int(group["solved"].sum()),
                "solved_any": bool(group["solved"].any()),
                "best_time": float(solved[time_col].min()) if not solved.empty else float(group[time_col].min()),
                "best_sample_id": int(solved.sort_values(time_col).iloc[0]["sample_id"]) if not solved.empty else -1,
                "capped_solver_cpu_total": float(group["capped_solver_cpu"].sum()),
                "neural_generation_wall_time": float(group["neural_generation_wall_time"].max())
                if "neural_generation_wall_time" in group.columns
                else float("nan"),
                **checkpoint_columns,
            }
        )
    instance_seed = pd.DataFrame(instance_seed_rows)

    oracle_rows = []
    for (family, size, file_key), group in raw.groupby(["family", "size", "file_key"], sort=True):
        solved = group[group["solved"]]
        solved_seeds = int(instance_seed[
            (instance_seed["family"].eq(family))
            & (instance_seed["size"].eq(int(size)))
            & (instance_seed["file_key"].eq(file_key))
            & (instance_seed["solved_any"])
        ]["sample_seed"].nunique())
        oracle_rows.append(
            {
                "family": family,
                "size": int(size),
                "file_key": file_key,
                "sample_seeds": int(group["sample_seed"].nunique()),
                "samples_per_seed": int(num_samples),
                "total_samples": int(len(group)),
                "solved_samples": int(group["solved"].sum()),
                "solved_seeds": solved_seeds,
                "solved_any": bool(group["solved"].any()),
                "best_time": float(solved[time_col].min()) if not solved.empty else float(group[time_col].min()),
                "best_sample_seed": int(solved.sort_values(time_col).iloc[0]["sample_seed"]) if not solved.empty else -1,
                "best_sample_id": int(solved.sort_values(time_col).iloc[0]["sample_id"]) if not solved.empty else -1,
                "capped_solver_cpu_total": float(group["capped_solver_cpu"].sum()),
                "neural_generation_wall_time": float(group["neural_generation_wall_time"].sum())
                if "neural_generation_wall_time" in group.columns
                else float("nan"),
                **checkpoint_columns,
            }
        )
    instance_oracle = pd.DataFrame(oracle_rows)

    size_seed_rows = []
    for (family, size, sample_seed), group in instance_seed.groupby(["family", "size", "sample_seed"], sort=True):
        size_seed_rows.append(
            {
                "family": family,
                "size": int(size),
                "sample_seed": int(sample_seed),
                "instances": int(len(group)),
                "num_samples": int(num_samples),
                "solved_any": int(group["solved_any"].sum()),
                "mean_solved_samples": float(group["solved_samples"].mean()),
                "max_solved_samples": int(group["solved_samples"].max()),
                "capped_solver_cpu_total": float(group["capped_solver_cpu_total"].sum()),
                "neural_generation_wall_time": float(group["neural_generation_wall_time"].sum()),
                **checkpoint_columns,
            }
        )
    size_seed = pd.DataFrame(size_seed_rows)

    size_oracle_rows = []
    for (family, size), group in instance_oracle.groupby(["family", "size"], sort=True):
        size_oracle_rows.append(
            {
                "family": family,
                "size": int(size),
                "instances": int(len(group)),
                "sample_seeds": int(group["sample_seeds"].max()),
                "samples_per_seed": int(num_samples),
                "total_samples_per_instance": int(group["total_samples"].max()),
                "oracle_solved_any": int(group["solved_any"].sum()),
                "mean_solved_samples": float(group["solved_samples"].mean()),
                "max_solved_samples": int(group["solved_samples"].max()),
                "max_solved_seeds": int(group["solved_seeds"].max()),
                "capped_solver_cpu_total": float(group["capped_solver_cpu_total"].sum()),
                "neural_generation_wall_time": float(group["neural_generation_wall_time"].sum()),
                **checkpoint_columns,
            }
        )
    size_oracle = pd.DataFrame(size_oracle_rows)
    return instance_seed, instance_oracle, size_seed, size_oracle


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
    subset: pd.DataFrame,
    instance_oracle: pd.DataFrame,
    size_seed: pd.DataFrame,
    size_oracle: pd.DataFrame,
    sample_seeds: list[int],
    solver_seed: int,
    num_samples: int,
    partial_summary: bool = False,
) -> None:
    solved = instance_oracle[instance_oracle["solved_any"]]
    solved_count = len(solved)
    total_count = len(instance_oracle)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# March Sample-Portfolio Multiseed Gate",
        "",
        "Scope: expanded stochastic-sampling gate for the existing March-trained",
        "policy on transition-band instances unsolved by the March/CaDiCaL union.",
        "This is an oracle-sample diagnostic, not a trained selector.",
        "",
        f"Sample seeds: {sample_seeds}; solver seed: {solver_seed}; samples per seed: {num_samples}.",
        "",
        f"Partial summary: {partial_summary}.",
        "",
        "## Input Subset",
        "",
        *markdown_table(subset, ["family", "size", "file_key"]),
        "",
        "## Per-Seed Size Summary",
        "",
        *markdown_table(size_seed, ["family", "size", "sample_seed", "instances", "num_samples", "solved_any", "mean_solved_samples", "max_solved_samples"]),
        "",
        "## Oracle Size Summary",
        "",
        *markdown_table(size_oracle, ["family", "size", "instances", "sample_seeds", "samples_per_seed", "total_samples_per_instance", "oracle_solved_any", "mean_solved_samples", "max_solved_samples", "max_solved_seeds"]),
        "",
        "## Oracle Instance Summary",
        "",
        *markdown_table(instance_oracle, ["family", "size", "file_key", "sample_seeds", "samples_per_seed", "total_samples", "solved_samples", "solved_seeds", "solved_any", "best_time", "best_sample_seed", "best_sample_id"]),
        "",
        "## Budget Summary",
        "",
        *markdown_table(size_oracle, ["family", "size", "instances", "capped_solver_cpu_total", "neural_generation_wall_time"]),
        "",
        "## Decision",
        "",
    ]
    if partial_summary:
        lines.extend(
            [
                f"- Current partial oracle coverage is {solved_count}/{total_count}.",
                "- This is a monitoring summary only. Do not use it as the",
                "  pre-registered all-49 gate decision.",
            ]
        )
    elif total_count == 49 and solved_count <= 2:
        lines.extend(
            [
                f"- Oracle sampled March guidance solves {solved_count}/{total_count}",
                "  strong-union both-unknown transition instances.",
                "- This fails the pre-registered all-49 pilot gate (`<=2/49`).",
                "- Do not tune the selector on this checkpoint. The next route is",
                "  residual-targeted model training, then rerun the same oracle gate.",
            ]
        )
    elif total_count == 49 and solved_count >= 5:
        lines.extend(
            [
                f"- Oracle sampled March guidance solves {solved_count}/{total_count}",
                "  strong-union both-unknown transition instances.",
                "- This passes the pre-registered all-49 pilot gate (`>=5/49`).",
                "- Continue to a larger residual pool, lock dev/held-out splits,",
                "  and tune fixed selectors only on dev before one-shot held-out",
                "  evaluation.",
            ]
        )
    elif not solved.empty:
        lines.extend(
            [
                f"- Oracle sampled March guidance solves {solved_count}/{total_count}",
                "  strong-union both-unknown transition instances.",
                "- This is diagnostic coverage only. For the all-49 pilot, apply",
                "  the pre-registered thresholds: `<=2/49` fails, `>=5/49` passes.",
            ]
        )
    else:
        lines.extend(
            [
                "- Oracle sampled March guidance still solves no strong-union both-unknown",
                "  transition instance.",
                "- The current checkpoint is not enough; the next route should change the",
                "  training objective rather than add selector complexity.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            display_path(RAW_DIR) + "/",
            display_path(INSTANCE_DIR) + "/",
            display_path(RAW_ALL_CSV),
            display_path(INSTANCE_SEED_CSV),
            display_path(INSTANCE_ORACLE_CSV),
            display_path(SIZE_SEED_CSV),
            display_path(SIZE_ORACLE_CSV),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not seeds:
        raise ValueError("At least one sample seed is required.")
    return seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-seed sampled March-guidance portfolio gate.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--input", type=Path, default=None, help="Residual CSV with family,size,file_key columns.")
    parser.add_argument("--source-root", type=Path, default=None, help="Root containing family/size/file_key CNFs.")
    parser.add_argument("--subset-root", type=Path, default=None, help="Working CNF subset root for symlinks/copies.")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--doc", type=Path, default=None)
    parser.add_argument("--num-samples", type=int, default=16)
    parser.add_argument("--sample-seeds", default="1729,1730,1731")
    parser.add_argument("--sizes", default="", help="Optional comma-separated size filter, e.g. 410,425.")
    parser.add_argument("--file-keys", default="", help="Optional comma-separated basename filter, e.g. 3sat_8.cnf.")
    parser.add_argument("--scope", choices=["transition", "expanded"], default="transition")
    parser.add_argument("--limit-instances", type=int, default=0)
    parser.add_argument("--solver-seed", type=int, default=1729)
    parser.add_argument("--full-cpu-lim", type=float, default=60.0)
    parser.add_argument("--artifact-mode", choices=["instance", "size"], default="instance")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Compatibility no-op. Existing per-instance artifacts are reused by default; "
            "use --force to recompute them or --clean to rebuild the subset directory."
        ),
    )
    parser.add_argument("--migrate-size-raw", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument("--allow-partial-summary", action="store_true")
    args = parser.parse_args()

    configure_scope(args.scope)
    configure_custom_paths(
        input_csv=args.input.resolve() if args.input else None,
        source_root=args.source_root.resolve() if args.source_root else None,
        subset_root=args.subset_root.resolve() if args.subset_root else None,
        out_dir=args.out_dir.resolve() if args.out_dir else None,
        doc_path=args.doc.resolve() if args.doc else None,
    )
    sample_seeds = parse_seeds(args.sample_seeds)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    with work_dir_lock(WORK_DIR):
        subset = prepare_subset(clean=args.clean, limit_instances=args.limit_instances)
        sizes = parse_seeds(args.sizes) if args.sizes else sorted(subset["size"].astype(int).unique())
        missing_sizes = sorted(set(sizes) - set(subset["size"].astype(int).unique()))
        if missing_sizes:
            raise ValueError(f"Requested sizes are absent from the subset: {missing_sizes}")
        subset = subset[subset["size"].astype(int).isin(sizes)].copy()
        file_keys = {part.strip() for part in args.file_keys.split(",") if part.strip()}
        if file_keys:
            subset = subset[subset["file_key"].astype(str).isin(file_keys)].copy()
            if subset.empty:
                raise ValueError(f"Requested file keys are absent from the subset: {sorted(file_keys)}")
        subset.to_csv(WORK_DIR / "both_unknown_subset.csv", index=False)
        if args.migrate_size_raw:
            migrated = migrate_size_raw_to_instances(
                sample_seeds=sample_seeds,
                num_samples=args.num_samples,
                full_cpu_lim=args.full_cpu_lim,
            )
            print(f"migrated_size_raw_instances={migrated}", flush=True)

        frames = []
        if args.summarize_only:
            if args.artifact_mode == "instance":
                for row in subset.itertuples(index=False):
                    size = int(row.size)
                    file_key = str(row.file_key)
                    for sample_seed in sample_seeds:
                        raw_path, _ = instance_paths(
                            size=size,
                            file_key=file_key,
                            sample_seed=sample_seed,
                            num_samples=args.num_samples,
                        )
                        if not raw_path.exists():
                            if args.allow_partial_summary:
                                continue
                            raise FileNotFoundError(raw_path)
                        frames.append(pd.read_csv(raw_path))
            else:
                for sample_seed in sample_seeds:
                    for size in sizes:
                        key_suffix = ""
                        if file_keys:
                            stable_keys = "-".join(Path(key).stem for key in sorted(file_keys))
                            key_suffix = f"_{stable_keys}"
                        raw_path = RAW_DIR / f"seed{sample_seed}_size{size}{key_suffix}_samples{args.num_samples}.csv"
                        if not raw_path.exists():
                            if args.allow_partial_summary:
                                continue
                            raise FileNotFoundError(raw_path)
                        frames.append(pd.read_csv(raw_path))
        else:
            checkpoint_path = Path(args.checkpoint).resolve()
            if not checkpoint_path.exists():
                raise FileNotFoundError(checkpoint_path)
            checkpoint_sha256 = file_sha256(checkpoint_path)
            model, transform, model_cfg = load_checkpoint(str(checkpoint_path), var_output=True)
            if args.artifact_mode == "instance":
                for row in subset.itertuples(index=False):
                    size = int(row.size)
                    file_key = str(row.file_key)
                    for sample_seed in sample_seeds:
                        frames.append(
                            run_seed_instance(
                                model=model,
                                transform=transform,
                                model_cfg=model_cfg,
                                size=size,
                                file_key=file_key,
                                sample_seed=sample_seed,
                                solver_seed=args.solver_seed,
                                num_samples=args.num_samples,
                                workers=args.workers,
                                device=args.device,
                                full_cpu_lim=args.full_cpu_lim,
                                force=args.force,
                                checkpoint_path=checkpoint_path,
                                checkpoint_sha256=checkpoint_sha256,
                            )
                        )
            else:
                for sample_seed in sample_seeds:
                    for size in sizes:
                        frames.append(
                            run_seed_size(
                                model=model,
                                transform=transform,
                                model_cfg=model_cfg,
                                size=size,
                                sample_seed=sample_seed,
                                solver_seed=args.solver_seed,
                                num_samples=args.num_samples,
                                workers=args.workers,
                                device=args.device,
                                full_cpu_lim=args.full_cpu_lim,
                                file_keys=file_keys if file_keys else None,
                                force=args.force,
                                checkpoint_path=checkpoint_path,
                                checkpoint_sha256=checkpoint_sha256,
                            )
                        )

        if not frames:
            raise FileNotFoundError("No raw artifacts found to summarize.")
        raw = pd.concat(frames, ignore_index=True)
        raw.to_csv(RAW_ALL_CSV, index=False)
        instance_seed, instance_oracle, size_seed, size_oracle = summarize(
            raw,
            num_samples=args.num_samples,
            full_cpu_lim=args.full_cpu_lim,
        )
        instance_seed.to_csv(INSTANCE_SEED_CSV, index=False)
        instance_oracle.to_csv(INSTANCE_ORACLE_CSV, index=False)
        size_seed.to_csv(SIZE_SEED_CSV, index=False)
        size_oracle.to_csv(SIZE_ORACLE_CSV, index=False)
        partial_summary = bool(args.summarize_only and args.allow_partial_summary and len(instance_oracle) < len(subset))
        write_doc(
            subset,
            instance_oracle,
            size_seed,
            size_oracle,
            sample_seeds,
            args.solver_seed,
            args.num_samples,
            partial_summary=partial_summary,
        )

        print(size_oracle.to_string(index=False))
        print(instance_oracle.to_string(index=False))
        print(display_path(DOC_PATH))


if __name__ == "__main__":
    main()
