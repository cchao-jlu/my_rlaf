from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pandas as pd

from src.datasets.generate_ksat import Random3SATGenerator


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data/benchmark_transition_band/3sat"
OUT_DIR = ROOT / "runs/analysis/benchmark_transition_band"
RAW_DIR = OUT_DIR / "raw"
COMBINED_CSV = OUT_DIR / "combined.csv"
SUMMARY_CSV = OUT_DIR / "summary.csv"
OVERLAP_CSV = OUT_DIR / "solver_overlap.csv"
BOTH_UNKNOWN_CSV = OUT_DIR / "both_unknown_subset.csv"
DOC_PATH = ROOT / "docs/benchmark_transition_band_gate.md"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}

SOLVERS = {
    "march": {
        "path": ROOT / "solvers/march/march_nh",
        "cmd_template": "{solver} {file}",
    },
    "cadical": {
        "path": ROOT / "solvers/cadical/cadical",
        "cmd_template": "{solver} -q -t {limit} {file}",
    },
}


def generate_size(size: int, instances: int, seed: int) -> Path:
    data_dir = DATA_ROOT / str(size)
    if len(sorted(data_dir.glob("*.cnf"))) >= instances:
        return data_dir
    generator = Random3SATGenerator(
        data_dir=str(data_dir),
        target_num=instances,
        num_var=(size, size),
        seed=seed + size,
    )
    generator.generate_all()
    return data_dir


def run_solver(
    solver_name: str,
    size: int,
    data_dir: Path,
    instances: int,
    limit: float,
    timeout: float,
    workers: int,
    repeat: int,
) -> Path:
    solver = SOLVERS[solver_name]
    solver_path = solver["path"]
    if not solver_path.exists():
        raise FileNotFoundError(solver_path)
    output = RAW_DIR / f"{solver_name}_3sat_{size}_repeat{repeat}.csv"
    command = [
        "python",
        str(ROOT / "run_external_solver_baseline.py"),
        "--solver",
        str(solver_path),
        "--solver-name",
        solver_name,
        "--input",
        str(data_dir / "*.cnf"),
        "--output",
        str(output),
        "--limit",
        f"{limit:g}",
        "--timeout",
        f"{timeout:g}",
        "--workers",
        str(workers),
        "--repeat",
        str(repeat),
        "--n",
        str(instances),
        "--cmd-template",
        solver["cmd_template"],
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    return output


def load_raw() -> pd.DataFrame:
    frames = []
    for path in sorted(RAW_DIR.glob("*_3sat_*_repeat*.csv")):
        frame = pd.read_csv(path)
        parts = path.stem.split("_")
        size = int(parts[2])
        frame["family"] = "3sat"
        frame["size"] = size
        frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
        frame["solved"] = frame["Result"].astype(str).isin(SOLVED_RESULTS)
        frame["source_csv"] = str(path.relative_to(ROOT))
        for column in ["time", "wall_time"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No raw CSVs found in {RAW_DIR}")
    return pd.concat(frames, ignore_index=True)


def summarize(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    for (size, solver_name), group in combined.groupby(["size", "solver_name"], sort=True):
        summary_rows.append(
            {
                "family": "3sat",
                "size": int(size),
                "solver": solver_name,
                "total": int(len(group)),
                "solved": int(group["solved"].sum()),
                "unknown": int((~group["solved"]).sum()),
                "mean_time": float(group["time"].mean()),
                "median_time": float(group["time"].median()),
                "max_time": float(group["time"].max()),
            }
        )
    summary = pd.DataFrame(summary_rows)

    overlap_rows = []
    both_unknown_rows = []
    for size, group in combined.groupby("size", sort=True):
        pivot = group.pivot_table(index="file_key", columns="solver_name", values="solved", aggfunc="first")
        if not {"march", "cadical"}.issubset(pivot.columns):
            raise ValueError(f"Expected March and CaDiCaL rows for size {size}")
        march = pivot["march"].astype(bool)
        cadical = pivot["cadical"].astype(bool)
        both_unknown = pivot.loc[~march & ~cadical].reset_index()
        for file_key in both_unknown["file_key"].astype(str):
            both_unknown_rows.append({"family": "3sat", "size": int(size), "file_key": file_key})
        overlap_rows.append(
            {
                "family": "3sat",
                "size": int(size),
                "total": int(len(pivot)),
                "both_solved": int((march & cadical).sum()),
                "march_only": int((march & ~cadical).sum()),
                "cadical_only": int((~march & cadical).sum()),
                "both_unknown": int((~march & ~cadical).sum()),
                "union_solved": int((march | cadical).sum()),
            }
        )
    overlap = pd.DataFrame(overlap_rows)
    both_unknown_frame = pd.DataFrame(both_unknown_rows)
    return summary, overlap, both_unknown_frame


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


def write_doc(summary: pd.DataFrame, overlap: pd.DataFrame, both_unknown: pd.DataFrame, sizes: list[int], instances: int) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    best_rows = overlap[(overlap["both_unknown"] > 0) & (overlap["union_solved"] > 0)].copy()
    lines = [
        "# Transition-Band Strong-Solver Gate",
        "",
        "Scope: random 3SAT transition-band gate for benchmark triage. This",
        "generates small fixed sets around the 400-to-450 region and runs March",
        "and CaDiCaL under the nominal 60s / external 65s protocol. It does not",
        "train or tune neural models.",
        "",
        f"Sizes: {', '.join(map(str, sizes))}; instances per size: {instances}.",
        "",
        "## Solver Summary",
        "",
        *markdown_table(summary, ["family", "size", "solver", "total", "solved", "unknown", "mean_time", "median_time", "max_time"]),
        "",
        "## March / CaDiCaL Overlap",
        "",
        *markdown_table(overlap, ["family", "size", "total", "both_solved", "march_only", "cadical_only", "both_unknown", "union_solved"]),
        "",
        "## Both-Unknown Subset",
        "",
        *markdown_table(both_unknown, ["family", "size", "file_key"]),
        "",
        "## Decision",
        "",
    ]
    if best_rows.empty:
        lines.extend(
            [
                "- This transition-band smoke did not find a useful mixed regime with",
                "  both strong-solver solves and both-unknown instances.",
                "- Do not spend neural evaluation budget here unless a larger gate changes",
                "  the overlap shape.",
            ]
        )
    else:
        lines.extend(
            [
                "- This gate found transition-band both-unknown instances while retaining",
                "  nonzero strong-solver solves. The next low-cost check is frozen neural",
                "  triage only on the both-unknown subset.",
            ]
        )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(COMBINED_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            str(OVERLAP_CSV.relative_to(ROOT)),
            str(BOTH_UNKNOWN_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a random 3SAT transition-band strong-solver gate.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[410, 425, 440])
    parser.add_argument("--instances", type=int, default=12)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--skip-solvers", action="store_true")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for size in args.sizes:
        data_dir = generate_size(size=size, instances=args.instances, seed=args.seed)
        print(f"size={size} data_dir={data_dir.relative_to(ROOT)} instances={args.instances}", flush=True)
        if args.generate_only or args.skip_solvers:
            continue
        for solver_name in ["march", "cadical"]:
            run_solver(
                solver_name=solver_name,
                size=size,
                data_dir=data_dir,
                instances=args.instances,
                limit=args.limit,
                timeout=args.timeout,
                workers=args.workers,
                repeat=args.repeat,
            )

    if args.generate_only:
        return

    combined = load_raw()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(COMBINED_CSV, index=False)
    summary, overlap, both_unknown = summarize(combined)
    summary.to_csv(SUMMARY_CSV, index=False)
    overlap.to_csv(OVERLAP_CSV, index=False)
    both_unknown.to_csv(BOTH_UNKNOWN_CSV, index=False)
    write_doc(summary, overlap, both_unknown, sizes=args.sizes, instances=args.instances)
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
