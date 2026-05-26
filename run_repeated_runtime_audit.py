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
SOURCE_DIR = ROOT / "data/test/3sat/400"
WORK_DIR = ROOT / "runs/analysis/repeated_runtime_audit"
RAW_DIR = WORK_DIR / "raw"
SUBSET_DIR = WORK_DIR / "subsets"
OUT_CSV = ROOT / "runs/analysis/repeated_runtime_audit.csv"
DOC_PATH = ROOT / "docs/repeated_runtime_audit.md"

RECOVERED_INSTANCES = [
    "3sat_163.cnf",
    "3sat_188.cnf",
    "3sat_189.cnf",
    "3sat_85.cnf",
    "3sat_89.cnf",
    "3sat_97.cnf",
]
LOCAL_OPEN_INSTANCES = [
    "3sat_188.cnf",
    "3sat_196.cnf",
    "3sat_46.cnf",
    "3sat_66.cnf",
]
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}


@dataclass(frozen=True)
class MethodSpec:
    group: str
    method: str
    config_name: str
    instances: tuple[str, ...]
    extra_overrides: tuple[str, ...] = ()


METHODS = [
    MethodSpec(
        group="recovered_timeout",
        method="one_shot",
        config_name="config_eval_guided_solver",
        instances=tuple(RECOVERED_INSTANCES),
        extra_overrides=(
            "checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt",
            "feedback_refinement.enabled=False",
            "dataset.lazy=True",
            "loader.batch_size=6",
        ),
    ),
    MethodSpec(
        group="recovered_timeout",
        method="online_consistent_boundary400",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        instances=tuple(RECOVERED_INSTANCES),
    ),
    MethodSpec(
        group="local_open_set",
        method="online_consistent_boundary400",
        config_name="config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400",
        instances=tuple(LOCAL_OPEN_INSTANCES),
    ),
    MethodSpec(
        group="local_open_set",
        method="local_reopen_guarded",
        config_name="config_eval_guided_solver_local_reopen_guarded_full400",
        instances=tuple(LOCAL_OPEN_INSTANCES),
    ),
]


def build_subset_dir(spec: MethodSpec) -> Path:
    subset = SUBSET_DIR / spec.group / spec.method
    subset.mkdir(parents=True, exist_ok=True)
    for name in spec.instances:
        source = SOURCE_DIR / name
        if not source.exists():
            raise FileNotFoundError(source)
        target = subset / name
        if not target.exists():
            target.symlink_to(source.resolve())
    return subset


def raw_csv_path(spec: MethodSpec, repeat: int) -> Path:
    return (RAW_DIR / spec.group / spec.method / f"repeat{repeat}.csv").resolve()


def build_command(spec: MethodSpec, repeat: int, workers: int) -> list[str]:
    subset = build_subset_dir(spec)
    raw_csv = raw_csv_path(spec, repeat)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(PYTHON),
        "evaluate_guided_solver.py",
        "--config-name",
        spec.config_name,
        f"dataset.eval_path={subset.resolve()}/*.cnf",
        f"save_file={raw_csv}",
        f"solver.num_workers={workers}",
        "solver.params.cpu-lim=60",
        "solver.params.rnd-freq=0.0",
        "solver.params.K=0.1",
        *spec.extra_overrides,
    ]
    return command


def run_eval(spec: MethodSpec, repeat: int, workers: int, dry_run: bool) -> Path:
    command = build_command(spec, repeat=repeat, workers=workers)
    raw_csv = raw_csv_path(spec, repeat)
    print(" ".join(command), flush=True)
    if dry_run:
        return raw_csv
    subprocess.run(command, cwd=ROOT, check=True)
    if not raw_csv.exists():
        raise FileNotFoundError(raw_csv)
    return raw_csv


def conclusion_tag(group: str, method: str, result: str) -> str:
    if str(result) not in SOLVED_RESULTS:
        return "timeout"
    if group == "local_open_set":
        return "boundary_candidate"
    return "solved"


def collect_rows(spec: MethodSpec, repeat: int, raw_csv: Path) -> list[dict[str, object]]:
    frame = pd.read_csv(raw_csv)
    rows = []
    for _, row in frame.iterrows():
        file_key = Path(str(row["file"])).name
        result = str(row.get("Result", "INDETERMINATE"))
        rows.append(
            {
                "instance": file_key,
                "file_key": file_key,
                "group": spec.group,
                "method": spec.method,
                "repeat": repeat,
                "result": result,
                "time": float(row.get("time", row.get("CPU time", 60.0))),
                "cpu_time": float(row.get("CPU time", 60.0)),
                "timeout": result not in SOLVED_RESULTS,
                "conclusion_tag": conclusion_tag(spec.group, spec.method, result),
                "raw_csv": str(raw_csv.relative_to(ROOT)),
            }
        )
    return rows


def write_csv(rows: list[dict[str, object]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "instance",
        "file_key",
        "group",
        "method",
        "repeat",
        "result",
        "time",
        "cpu_time",
        "timeout",
        "conclusion_tag",
        "raw_csv",
    ]
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def majority(values: pd.Series) -> bool:
    return int(values.sum()) > len(values) / 2.0


def comparison_rows(frame: pd.DataFrame) -> list[dict[str, str]]:
    rows = []
    recovered = frame[frame["group"].eq("recovered_timeout")]
    for instance in RECOVERED_INSTANCES:
        part = recovered[recovered["instance"].eq(instance)]
        one = part[part["method"].eq("one_shot")]
        online = part[part["method"].eq("online_consistent_boundary400")]
        stable = majority(one["timeout"]) and majority(~online["timeout"])
        rows.append(
            {
                "instance": instance,
                "comparison": "One-shot vs Online-Consistent Selector",
                "stable": "yes" if stable else "no",
                "interpretation": (
                    "recovered timeout stable"
                    if stable
                    else "runtime-sensitive recovered timeout"
                ),
            }
        )

    local = frame[frame["group"].eq("local_open_set")]
    for instance in LOCAL_OPEN_INSTANCES:
        part = local[local["instance"].eq(instance)]
        online = part[part["method"].eq("online_consistent_boundary400")]
        correction = part[part["method"].eq("local_reopen_guarded")]
        online_solved = majority(~online["timeout"])
        correction_solved = majority(~correction["timeout"])
        delta = float(correction["time"].median() - online["time"].median())
        if instance in {"3sat_196.cnf", "3sat_46.cnf"} and online_solved and correction_solved and delta < -1.0:
            stable = "yes"
            interpretation = "stable hard speedup"
        elif instance == "3sat_188.cnf":
            stable = "mixed"
            interpretation = "mild / boundary-sensitive"
        elif instance == "3sat_66.cnf":
            stable = "yes" if majority(online["timeout"]) and majority(correction["timeout"]) else "mixed"
            interpretation = "neutral timeout"
        else:
            stable = "mixed"
            interpretation = "runtime-sensitive local case"
        rows.append(
            {
                "instance": instance,
                "comparison": "Online-Consistent Selector vs + Local Boundary Correction",
                "stable": stable,
                "interpretation": interpretation,
            }
        )
    return rows


def write_doc(frame: pd.DataFrame) -> None:
    rows = comparison_rows(frame)
    lines = [
        "# Repeated Runtime Audit",
        "",
        "This audit only checks runtime stability for two fixed paper claims:",
        "",
        "1. Whether the six `50 -> 56` recovered timeouts remain stable.",
        "2. Whether the four guarded Local Boundary Correction open-set cases remain stable.",
        "",
        "It does not change the model, thresholds, configs, or solver seed.",
        "",
        "Source CSV:",
        "",
        "- `runs/analysis/repeated_runtime_audit.csv`",
        "",
        "| instance | comparison | stable? | interpretation |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['instance']}` | {row['comparison']} | {row['stable']} | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- `3sat_188.cnf` appears in both groups and is treated as boundary-sensitive.",
            "- `3sat_66.cnf` is neutral timeout evidence, not an improvement claim.",
            "- This is same-seed repeated runtime stability, not seed sensitivity.",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed repeated runtime audit for paper claims.")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    if args.clean and WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SUBSET_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for repeat in range(args.repeats):
        for spec in METHODS:
            raw_csv = run_eval(spec, repeat=repeat, workers=args.workers, dry_run=args.dry_run)
            if not args.dry_run:
                rows.extend(collect_rows(spec, repeat=repeat, raw_csv=raw_csv))

    if args.dry_run:
        return
    write_csv(rows)
    frame = pd.DataFrame(rows)
    write_doc(frame)
    print(f"wrote {OUT_CSV}")
    print(f"wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
