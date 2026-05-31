from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/benchmark_suitability_gate"
DOC_PATH = ROOT / "docs/benchmark_suitability_gate.md"


def dataset_count(size: int) -> int:
    return len(list((ROOT / f"data/test/3sat/{size}").glob("*.cnf")))


def load_smoke(size: int) -> dict[str, object]:
    path = ROOT / f"runs/analysis/benchmark_suitability_smoke/march_{size}_smoke.csv"
    frame = pd.read_csv(path)
    solved = frame["Result"].astype(str).isin({"SATISFIABLE", "UNSATISFIABLE"})
    times = pd.to_numeric(frame["time"], errors="coerce")
    return {
        "size": size,
        "protocol": "smoke20",
        "total": int(len(frame)),
        "solved": int(solved.sum()),
        "unknown": int((~solved).sum()),
        "mean_time": float(times.mean()),
        "median_time": float(times.median()),
        "max_time": float(times.max()),
        "external_timeouts": int(frame["external_timeout"].astype(str).str.lower().isin({"true", "1", "yes"}).sum()),
        "source": str(path.relative_to(ROOT)),
    }


def load_full400() -> dict[str, object]:
    summary = pd.read_csv(ROOT / "runs/analysis/march_full400_cpu60/strict60_summary.csv").iloc[0]
    return {
        "size": 400,
        "protocol": "full200_repeat3_strict60",
        "total": 200,
        "solved": int(float(summary["solved_strict60"])),
        "unknown": 200 - int(float(summary["solved_strict60"])),
        "mean_time": float(summary["mean_time_strict60"]),
        "median_time": float(summary["median_time_strict60"]),
        "max_time": 60.0,
        "external_timeouts": int(float(summary["external_timeouts"])),
        "source": "runs/analysis/march_full400_cpu60/strict60_summary.csv",
    }


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset_rows = [{"family": "3sat", "size": size, "instances": dataset_count(size)} for size in [250, 300, 350, 400]]
    datasets = pd.DataFrame(dataset_rows)
    datasets.to_csv(OUT_DIR / "dataset_inventory.csv", index=False)

    march_rows = [load_smoke(size) for size in [250, 300, 350]]
    march_rows.append(load_full400())
    march = pd.DataFrame(march_rows)
    march["solved_rate"] = march["solved"] / march["total"]
    march.to_csv(OUT_DIR / "march_suitability_summary.csv", index=False)

    solver_inventory = pd.DataFrame(
        [
            {
                "solver": "Glucose",
                "path": "solvers/glucose/simp/glucose_static",
                "executable": (ROOT / "solvers/glucose/simp/glucose_static").exists(),
                "role": "unguided CDCL baseline",
            },
            {
                "solver": "Weighted Glucose",
                "path": "solvers/glucose_weighted/simp/glucose_static",
                "executable": (ROOT / "solvers/glucose_weighted/simp/glucose_static").exists(),
                "role": "neural workflow solver",
            },
            {
                "solver": "CaDiCaL",
                "path": "solvers/cadical/cadical",
                "executable": (ROOT / "solvers/cadical/cadical").exists(),
                "role": "strong CDCL baseline",
            },
            {
                "solver": "March",
                "path": "solvers/march/march_nh",
                "executable": (ROOT / "solvers/march/march_nh").exists(),
                "role": "lookahead baseline",
            },
            {
                "solver": "Kissat",
                "path": "solvers/kissat/kissat",
                "executable": (ROOT / "solvers/kissat/kissat").exists(),
                "role": "missing external strong-solver gate",
            },
            {
                "solver": "MapleSAT",
                "path": "solvers/maplesat/maplesat",
                "executable": (ROOT / "solvers/maplesat/maplesat").exists(),
                "role": "missing external strong-solver gate",
            },
            {
                "solver": "CryptoMiniSat",
                "path": "solvers/cryptominisat/cryptominisat5",
                "executable": (ROOT / "solvers/cryptominisat/cryptominisat5").exists(),
                "role": "missing external strong-solver gate",
            },
        ]
    )
    solver_inventory.to_csv(OUT_DIR / "solver_inventory.csv", index=False)

    lines = [
        "# Benchmark Suitability Gate",
        "",
        "Scope: decide whether the current held-out benchmark package can support",
        "a top-conference performance claim. This is a benchmark audit only: it",
        "does not modify neural models, selectors, thresholds, solver code, or",
        "Local Boundary Correction.",
        "",
        "## Dataset Inventory",
        "",
        *markdown_table(datasets, ["family", "size", "instances"]),
        "",
        "## Available Strong Solver Artifacts",
        "",
        *markdown_table(solver_inventory, ["solver", "path", "executable", "role"]),
        "",
        "## March Suitability Probe",
        "",
        "March is the strongest available baseline in the current checkout on the",
        "random 3SAT held-out family. For 250/300/350, this gate uses a 20-instance",
        "smoke probe. For 400, it uses the existing repeated full200 strict-60",
        "audit.",
        "",
        *markdown_table(
            march,
            [
                "size",
                "protocol",
                "total",
                "solved",
                "unknown",
                "solved_rate",
                "mean_time",
                "median_time",
                "max_time",
                "external_timeouts",
            ],
        ),
        "",
        "## Decision",
        "",
        "- The current benchmark family is random 3SAT only, with 200 held-out",
        "  instances each at sizes 250, 300, 350, and 400.",
        "- March solves all 20 smoke instances at 250, 300, and 350. The 250/300",
        "  smoke probes are sub-second on average, and 350 is still fully solved",
        "  in the smoke set.",
        "- On full400, March strict-60 solves 184/200 in all three repeats and",
        "  strictly contains all current neural-guided solved sets.",
        "- Therefore the current benchmark package is not suitable for a",
        "  top-conference performance claim unless March/lookahead solvers are",
        "  explicitly excluded by a well-justified protocol. It is suitable for a",
        "  neural-guidance failure-boundary and risk-control study.",
        "- The next hard gate for a performance route is not another selector. It is",
        "  either a new benchmark protocol where strong solvers are not trivially",
        "  dominant, or external Kissat/MapleSAT/CryptoMiniSat artifacts evaluated",
        "  under the same repeated 60s protocol.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/benchmark_suitability_gate/dataset_inventory.csv",
        "runs/analysis/benchmark_suitability_gate/solver_inventory.csv",
        "runs/analysis/benchmark_suitability_gate/march_suitability_summary.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(march.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
