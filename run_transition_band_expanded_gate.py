from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

from src.datasets.generate_ksat import Random3SATGenerator


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data/benchmark_transition_band_expanded/3sat"
OUT_DIR = ROOT / "runs/analysis/benchmark_transition_band_expanded"
RAW_DIR = OUT_DIR / "raw"
COMBINED_CSV = OUT_DIR / "combined.csv"
SUMMARY_CSV = OUT_DIR / "summary.csv"
OVERLAP_CSV = OUT_DIR / "solver_overlap.csv"
BOTH_UNKNOWN_CSV = OUT_DIR / "both_unknown_subset.csv"
DOC_PATH = ROOT / "docs/benchmark_transition_band_expanded_gate.md"
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


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def configure_paths(data_root: Path, out_dir: Path, doc_path: Path, raw_dir: Path | None = None) -> None:
    global DATA_ROOT, OUT_DIR, RAW_DIR, COMBINED_CSV, SUMMARY_CSV, OVERLAP_CSV, BOTH_UNKNOWN_CSV, DOC_PATH
    DATA_ROOT = data_root
    OUT_DIR = out_dir
    RAW_DIR = raw_dir if raw_dir is not None else OUT_DIR / "raw"
    COMBINED_CSV = OUT_DIR / "combined.csv"
    SUMMARY_CSV = OUT_DIR / "summary.csv"
    OVERLAP_CSV = OUT_DIR / "solver_overlap.csv"
    BOTH_UNKNOWN_CSV = OUT_DIR / "both_unknown_subset.csv"
    DOC_PATH = doc_path


def generate_size(size: int, instances: int, seed: int) -> Path:
    data_dir = DATA_ROOT / str(size)
    existing = sorted(data_dir.glob("*.cnf"))
    if len(existing) >= instances:
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
    output = RAW_DIR / f"{solver_name}_3sat_{size}_n{instances}_repeat{repeat}.csv"
    command = [
        sys.executable,
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


def load_raw(instances: int, repeat: int, limit: float) -> pd.DataFrame:
    frames = []
    for path in sorted(RAW_DIR.glob(f"*_3sat_*_n{instances}_repeat{repeat}.csv")):
        frame = pd.read_csv(path)
        parts = path.stem.split("_")
        solver_name = parts[0]
        size = int(parts[2])
        frame["family"] = "3sat"
        frame["size"] = size
        frame["solver_name"] = solver_name
        frame["file_key"] = frame["file"].astype(str).map(lambda value: Path(value).name)
        frame["source_csv"] = display_path(path)
        for column in ["time", "wall_time"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["nominal_limit"] = float(limit)
        frame["solved_returned"] = frame["Result"].astype(str).isin(SOLVED_RESULTS)
        # Strong-baseline residual filtering must use the declared cap exactly.
        # March has no internal limit in this binary, so a solution returned
        # after the nominal cap but before the external timeout is not counted
        # as a solved baseline instance for denominator construction.
        frame["solved"] = frame["solved_returned"] & frame["time"].le(float(limit))
        frame["solved_after_nominal_limit"] = frame["solved_returned"] & ~frame["solved"]
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No raw CSVs found in {RAW_DIR}")
    return pd.concat(frames, ignore_index=True)


def audit_raw_completeness(combined: pd.DataFrame, sizes: list[int], instances: int) -> list[str]:
    errors = []
    expected_solvers = {"march", "cadical"}
    if combined.empty:
        return ["combined raw frame is empty"]
    for size in sizes:
        size_frame = combined[combined["size"].astype(int) == int(size)]
        present = set(size_frame["solver_name"].astype(str).unique())
        missing_solvers = expected_solvers - present
        if missing_solvers:
            errors.append(f"size={size} missing solvers={sorted(missing_solvers)}")
        for solver_name in sorted(expected_solvers & present):
            group = size_frame[size_frame["solver_name"].astype(str) == solver_name]
            rows = int(len(group))
            unique_files = int(group["file_key"].nunique()) if "file_key" in group.columns else 0
            if rows != instances or unique_files != instances:
                errors.append(
                    f"size={size} solver={solver_name} rows={rows} unique_files={unique_files} expected={instances}"
                )
    return errors


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
                "solved_after_nominal_limit": int(group["solved_after_nominal_limit"].sum())
                if "solved_after_nominal_limit" in group.columns
                else 0,
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
    return summary, pd.DataFrame(overlap_rows), pd.DataFrame(both_unknown_rows)


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
    lines = [
        "# Expanded Transition-Band Strong-Solver Gate",
        "",
        "Scope: larger strong-solver gate for finding March/CaDiCaL union-unsolved",
        "random 3SAT instances. This is the candidate source for expanded sampled",
        "March guidance experiments.",
        "",
        f"Sizes: {', '.join(map(str, sizes))}; instances per size: {instances}.",
        f"Data root: `{display_path(DATA_ROOT)}`.",
        f"Output dir: `{display_path(OUT_DIR)}`.",
        "",
        "## Solver Summary",
        "",
        *markdown_table(summary, ["family", "size", "solver", "total", "solved", "solved_after_nominal_limit", "unknown", "mean_time", "median_time", "max_time"]),
        "",
        "## March / CaDiCaL Overlap",
        "",
        *markdown_table(overlap, ["family", "size", "total", "both_solved", "march_only", "cadical_only", "both_unknown", "union_solved"]),
        "",
        "## Both-Unknown Count",
        "",
        f"Total both-unknown instances: {len(both_unknown)}",
        "",
        "Artifacts:",
        "",
        "```text",
        display_path(COMBINED_CSV),
        display_path(SUMMARY_CSV),
        display_path(OVERLAP_CSV),
        display_path(BOTH_UNKNOWN_CSV),
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run expanded transition-band March/CaDiCaL gate.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[410, 425, 440])
    parser.add_argument("--instances", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1041)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--raw-dir", type=Path, default=None, help="Optional existing raw CSV directory for summarize-only reruns.")
    parser.add_argument("--doc-path", type=Path, default=DOC_PATH)
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--skip-solvers", action="store_true")
    parser.add_argument(
        "--allow-partial-summary",
        action="store_true",
        help="Allow summarizing incomplete raw CSVs. Never use this for final residual denominators.",
    )
    args = parser.parse_args()

    configure_paths(
        data_root=args.data_root.resolve(),
        out_dir=args.out_dir.resolve(),
        raw_dir=args.raw_dir.resolve() if args.raw_dir else None,
        doc_path=args.doc_path.resolve(),
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for size in args.sizes:
        if args.skip_solvers and args.raw_dir is not None:
            data_dir = DATA_ROOT / str(size)
        else:
            data_dir = generate_size(size=size, instances=args.instances, seed=args.seed)
        print(f"size={size} data_dir={display_path(data_dir)} instances={args.instances}", flush=True)
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

    combined = load_raw(instances=args.instances, repeat=args.repeat, limit=args.limit)
    completeness_errors = audit_raw_completeness(combined, sizes=args.sizes, instances=args.instances)
    if completeness_errors and not args.allow_partial_summary:
        message = "\n".join(completeness_errors)
        raise RuntimeError(f"Raw solver artifacts are incomplete; refusing to write final summary:\n{message}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(COMBINED_CSV, index=False)
    summary, overlap, both_unknown = summarize(combined)
    summary.to_csv(SUMMARY_CSV, index=False)
    overlap.to_csv(OVERLAP_CSV, index=False)
    both_unknown.to_csv(BOTH_UNKNOWN_CSV, index=False)
    write_doc(summary, overlap, both_unknown, sizes=args.sizes, instances=args.instances)
    print(summary.to_string(index=False))
    print(overlap.to_string(index=False))
    print(f"both_unknown={len(both_unknown)}")
    print(display_path(DOC_PATH))


if __name__ == "__main__":
    main()
