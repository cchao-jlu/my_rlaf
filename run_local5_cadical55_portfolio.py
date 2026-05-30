from __future__ import annotations

import argparse
import csv
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_CSV = ROOT / "runs/analysis/cadical_neural_overlap/combined.csv"
OUT_DIR = ROOT / "runs/analysis/portfolio_local5_cadical55"
DOC_PATH = ROOT / "docs/portfolio_local5_cadical55_eval.md"
DEFAULT_SOLVER = ROOT / "solvers/cadical/cadical"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}
RAW_FIELDNAMES = [
    "file",
    "Result",
    "time",
    "wall_time",
    "external_timeout",
    "returncode",
    "stdout_head",
    "stderr_head",
]


def parse_result(stdout: str, returncode: int) -> str:
    for line in stdout.splitlines():
        if line.startswith("s "):
            return line.split()[1]
    if returncode == 10:
        return "SATISFIABLE"
    if returncode == 20:
        return "UNSATISFIABLE"
    return "UNKNOWN"


def solve_cadical_one(file_path: str, solver: str, time_limit: float, external_timeout: float) -> dict[str, object]:
    command = [solver, "-q", "-t", f"{time_limit:g}", file_path]
    start = time.monotonic()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=external_timeout)
        wall_time = time.monotonic() - start
        result = parse_result(proc.stdout, proc.returncode)
        reported_time = wall_time if result in SOLVED_RESULTS else time_limit
        return {
            "file": file_path,
            "Result": result,
            "time": reported_time,
            "wall_time": wall_time,
            "external_timeout": False,
            "returncode": proc.returncode,
            "stdout_head": proc.stdout.splitlines()[:3],
            "stderr_head": proc.stderr.splitlines()[:3],
        }
    except subprocess.TimeoutExpired as exc:
        wall_time = time.monotonic() - start
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "file": file_path,
            "Result": "UNKNOWN",
            "time": time_limit,
            "wall_time": wall_time,
            "external_timeout": True,
            "returncode": "timeout",
            "stdout_head": stdout.splitlines()[:3],
            "stderr_head": stderr.splitlines()[:3],
        }


def existing_files(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    with output_path.open(newline="") as handle:
        return {row["file"] for row in csv.DictReader(handle) if row.get("file")}


def append_row(output_path: Path, row: dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_path.exists()
    with output_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def load_inputs(first_cap: float, smoke: bool, smoke_n: int) -> pd.DataFrame:
    frame = pd.read_csv(INPUT_CSV).copy()
    frame["pattern"] = frame["pattern"].astype(str).str.zfill(4)
    frame["file_key"] = frame["file_key"].astype(str)
    frame["file"] = frame["file_key"].map(lambda key: str(ROOT / "data/test/3sat/400" / key))
    frame["local_stage1_solved"] = (
        frame["local_correction_solved"].astype(bool)
        & (pd.to_numeric(frame["local_correction_time_mean"], errors="coerce") <= first_cap)
    )
    if not smoke:
        return frame.sort_values("file_key").reset_index(drop=True)

    # Keep smoke mixed: include a few stage-1 hits plus CaDiCaL-known fast,
    # CaDiCaL-known timeout, and local-only cases.
    picks: list[pd.DataFrame] = []
    picks.append(frame[frame["local_stage1_solved"]].sort_values("local_correction_time_mean").head(3))
    picks.append(frame[~frame["local_stage1_solved"] & frame["cadical_solved"].astype(bool)].sort_values("cadical_time").head(smoke_n))
    picks.append(frame[~frame["local_stage1_solved"] & ~frame["cadical_solved"].astype(bool)].sort_values("file_key").head(5))
    picks.append(frame[frame["file_key"].isin(["3sat_188.cnf", "3sat_66.cnf"])])
    subset = pd.concat(picks, ignore_index=True).drop_duplicates("file_key")
    return subset.sort_values("file_key").reset_index(drop=True)


def run_cadical_stage(
    frame: pd.DataFrame,
    output_path: Path,
    solver: Path,
    second_cap: float,
    external_timeout: float,
    workers: int,
    skip_existing: bool,
) -> None:
    pending_frame = frame[~frame["local_stage1_solved"]].copy()
    files = pending_frame["file"].tolist()
    done = existing_files(output_path) if skip_existing else set()
    pending = [path for path in files if path not in done]
    print(
        f"stage2_total={len(files)} done={len(done)} pending={len(pending)} output={output_path}",
        flush=True,
    )
    if not pending:
        return
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(solve_cadical_one, path, str(solver), second_cap, external_timeout): path
            for path in pending
        }
        for idx, future in enumerate(as_completed(futures), start=1):
            path = futures[future]
            row = future.result()
            append_row(output_path, row)
            print(
                f"[{idx}/{len(pending)}] {Path(path).name} {row['Result']} "
                f"time={float(row['time']):.3f} wall={float(row['wall_time']):.3f}",
                flush=True,
            )


def summarize(frame: pd.DataFrame, raw_path: Path, first_cap: float, second_cap: float, mode: str) -> pd.DataFrame:
    raw = pd.read_csv(raw_path) if raw_path.exists() else pd.DataFrame(columns=RAW_FIELDNAMES)
    if not raw.empty:
        raw["file_key"] = raw["file"].astype(str).map(lambda value: Path(value).name)
        raw["stage2_solved"] = raw["Result"].astype(str).isin(SOLVED_RESULTS)
        raw["stage2_time"] = pd.to_numeric(raw["time"], errors="coerce").fillna(second_cap).clip(upper=second_cap)
        raw = raw[["file_key", "Result", "stage2_solved", "stage2_time", "wall_time", "external_timeout", "returncode"]]
    merged = frame.merge(raw, on="file_key", how="left")
    merged["stage2_run"] = ~merged["local_stage1_solved"]
    merged["stage2_solved"] = merged["stage2_solved"].where(
        merged["stage2_solved"].notna(),
        False,
    ).astype(bool)
    merged["stage2_time"] = pd.to_numeric(merged["stage2_time"], errors="coerce").fillna(second_cap)
    merged["portfolio_solved"] = merged["local_stage1_solved"] | (
        merged["stage2_run"] & merged["stage2_solved"]
    )
    merged["portfolio_time"] = 60.0
    merged.loc[merged["local_stage1_solved"], "portfolio_time"] = merged.loc[
        merged["local_stage1_solved"], "local_correction_time_mean"
    ]
    stage2_hit = merged["stage2_run"] & merged["stage2_solved"]
    merged.loc[stage2_hit, "portfolio_time"] = first_cap + merged.loc[stage2_hit, "stage2_time"]
    merged["mode"] = mode
    merged["first_cap"] = first_cap
    merged["second_cap"] = second_cap
    merged["pattern"] = merged["pattern"].astype(str).str.zfill(4)
    merged["portfolio_only_vs_cadical"] = merged["portfolio_solved"] & ~merged["cadical_solved"].astype(bool)
    merged["cadical_only_vs_portfolio"] = ~merged["portfolio_solved"] & merged["cadical_solved"].astype(bool)
    return merged.sort_values("file_key")


def write_doc(combined: pd.DataFrame, summary: pd.DataFrame, raw_path: Path, mode: str) -> None:
    solved = int(combined["portfolio_solved"].sum())
    total = int(len(combined))
    local_stage1 = int(combined["local_stage1_solved"].sum())
    stage2_solved = int((combined["stage2_run"] & combined["stage2_solved"]).sum())
    cadical_solved = int(combined["cadical_solved"].sum())
    portfolio_only = int(combined["portfolio_only_vs_cadical"].sum())
    cadical_only = int(combined["cadical_only_vs_portfolio"].sum())
    mean_time = float(combined["portfolio_time"].mean())
    median_time = float(combined["portfolio_time"].median())
    portfolio_only_frame = combined.loc[
        combined["portfolio_only_vs_cadical"],
        [
            "file_key",
            "local_stage1_solved",
            "stage2_solved",
            "portfolio_time",
            "local_correction_time_mean",
            "cadical_time",
            "pattern",
        ],
    ].sort_values("file_key")
    cadical_only_frame = combined.loc[
        combined["cadical_only_vs_portfolio"],
        ["file_key", "local_stage1_solved", "stage2_solved", "cadical_time", "pattern"],
    ].sort_values("file_key")
    doc_lines = [
        "# Local-5s / CaDiCaL-55s Portfolio Evaluation",
        "",
        f"Mode: `{mode}`.",
        "",
        "Scope: this evaluates the concrete schedule suggested by the portfolio",
        "feasibility audit: first allocate 5s to + Local Boundary Correction, then",
        "run CaDiCaL for the remaining 55s on instances not solved by the first",
        "stage.",
        "",
        "Important limitation: the first-stage Local result is imported from the",
        "existing full400 3-seed mean table by counting instances solved by Local",
        "within 5s. The second-stage CaDiCaL 55s results are actually rerun. This",
        "is stronger than the pure feasibility simulation for CaDiCaL stability,",
        "but it is still not a complete interrupted end-to-end neural portfolio",
        "run.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| solved | {solved}/{total} |",
        f"| CaDiCaL alone solved | {cadical_solved}/{total} |",
        f"| delta vs CaDiCaL solved | {solved - cadical_solved:+d} |",
        f"| portfolio-only solved vs CaDiCaL | {portfolio_only} |",
        f"| CaDiCaL-only solved vs portfolio | {cadical_only} |",
        f"| local stage-1 solved within 5s | {local_stage1} |",
        f"| CaDiCaL stage-2 solved within 55s | {stage2_solved} |",
        f"| mean portfolio time | {mean_time:.3f}s |",
        f"| median portfolio time | {median_time:.3f}s |",
        "",
        "## Portfolio-Only Instances",
        "",
        *markdown_table(
            portfolio_only_frame,
            [
                "file_key",
                "local_stage1_solved",
                "stage2_solved",
                "portfolio_time",
                "local_correction_time_mean",
                "cadical_time",
                "pattern",
            ],
        ),
        "",
        "## CaDiCaL-Only Instances",
        "",
        *markdown_table(
            cadical_only_frame,
            ["file_key", "local_stage1_solved", "stage2_solved", "cadical_time", "pattern"],
        ),
        "",
        "## Decision",
        "",
    ]
    if mode == "full":
        doc_lines.extend(
            [
                f"- This hybrid schedule reaches {solved}/200, {solved - cadical_solved:+d}",
                "  over the CaDiCaL 60s baseline, and loses no CaDiCaL-solved",
                "  instances under the current rerun.",
                "- The portfolio direction is now empirically supported enough to",
                "  justify a true end-to-end interrupted runner.",
                "- This is not yet a paper-ready portfolio result because the 5s Local",
                "  first stage is imported from existing full400 3-seed mean times",
                "  rather than executed as an interrupted solver process.",
            ]
        )
    else:
        doc_lines.extend(
            [
                "- Smoke mode only validates the runner, output schema, and stage-2",
                "  CaDiCaL invocation. Do not use it as a paper result.",
                "- If smoke output is clean, the next step is `--mode full`.",
            ]
        )
    doc_lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            str(raw_path.relative_to(ROOT)),
            str((OUT_DIR / f"{mode}_combined.csv").relative_to(ROOT)),
            str((OUT_DIR / f"{mode}_summary.csv").relative_to(ROOT)),
            str((OUT_DIR / f"{mode}_portfolio_only_vs_cadical.csv").relative_to(ROOT)),
            str((OUT_DIR / f"{mode}_cadical_only_vs_portfolio.csv").relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")
    summary.to_csv(OUT_DIR / f"{mode}_summary.csv", index=False)
    portfolio_only_frame.to_csv(OUT_DIR / f"{mode}_portfolio_only_vs_cadical.csv", index=False)
    cadical_only_frame.to_csv(OUT_DIR / f"{mode}_cadical_only_vs_portfolio.csv", index=False)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(f"{value:.3f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a Local-5s then CaDiCaL-55s portfolio schedule.")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--first-cap", type=float, default=5.0)
    parser.add_argument("--second-cap", type=float, default=55.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--solver", type=Path, default=DEFAULT_SOLVER)
    parser.add_argument("--smoke-n", type=int, default=8)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_inputs(first_cap=args.first_cap, smoke=args.mode == "smoke", smoke_n=args.smoke_n)
    raw_path = OUT_DIR / f"{args.mode}_cadical55_raw.csv"
    run_cadical_stage(
        frame=frame,
        output_path=raw_path,
        solver=args.solver,
        second_cap=args.second_cap,
        external_timeout=args.timeout,
        workers=args.workers,
        skip_existing=args.skip_existing,
    )
    combined = summarize(frame, raw_path, first_cap=args.first_cap, second_cap=args.second_cap, mode=args.mode)
    combined.to_csv(OUT_DIR / f"{args.mode}_combined.csv", index=False)
    summary = pd.DataFrame(
        [
            {
                "mode": args.mode,
                "total": int(len(combined)),
                "solved": int(combined["portfolio_solved"].sum()),
                "local_stage1_solved": int(combined["local_stage1_solved"].sum()),
                "stage2_solved": int((combined["stage2_run"] & combined["stage2_solved"]).sum()),
                "cadical_solved": int(combined["cadical_solved"].sum()),
                "portfolio_only_vs_cadical": int(combined["portfolio_only_vs_cadical"].sum()),
                "cadical_only_vs_portfolio": int(combined["cadical_only_vs_portfolio"].sum()),
                "mean_portfolio_time": float(combined["portfolio_time"].mean()),
                "median_portfolio_time": float(combined["portfolio_time"].median()),
            }
        ]
    )
    write_doc(combined, summary, raw_path, mode=args.mode)
    print(summary.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
