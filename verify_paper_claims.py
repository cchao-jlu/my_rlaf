from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PAPER = ROOT / "paper/main.tex"
TABLES = ROOT / "docs/paper_tables_and_figures.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def main() -> None:
    paper = read_text(PAPER)
    tables = read_text(TABLES)
    combined_text = paper + "\n" + tables

    portfolio = pd.read_csv(ROOT / "runs/analysis/cadical_repeat_stability/portfolio_vs_cadical_repeats.csv")
    neural = pd.read_csv(ROOT / "runs/analysis/full400_seed_robustness/method_summary.csv")
    overlap = pd.read_csv(ROOT / "runs/analysis/cadical_repeated_neural_overlap/summary.csv")
    march = pd.read_csv(ROOT / "runs/analysis/march_full400_cpu60/strict60_summary.csv")
    march_repeats = pd.read_csv(ROOT / "runs/analysis/march_full400_cpu60/strict60_repeat_summary.csv")
    march_overlap = pd.read_csv(ROOT / "runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv")
    strong_gate = pd.read_csv(ROOT / "runs/analysis/stronger_cdcl_gate/summary.csv")
    solver_availability = pd.read_csv(ROOT / "runs/analysis/stronger_cdcl_gate/solver_availability.csv")
    lattice_methods = pd.read_csv(ROOT / "runs/analysis/failure_boundary_lattice/method_summary.csv")
    lattice_pairs = pd.read_csv(ROOT / "runs/analysis/failure_boundary_lattice/pair_summary.csv")
    benchmark_datasets = pd.read_csv(ROOT / "runs/analysis/benchmark_suitability_gate/dataset_inventory.csv")
    benchmark_march = pd.read_csv(ROOT / "runs/analysis/benchmark_suitability_gate/march_suitability_summary.csv")
    candidate_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_candidate_smoke/summary.csv")
    candidate_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_candidate_smoke/solver_overlap.csv")
    gate450_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/summary.csv")
    gate450_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/solver_overlap.csv")
    gate450_hard = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv")

    portfolio_solved = portfolio["portfolio_solved"].astype(int).tolist()
    cadical_solved = portfolio["cadical_solved"].astype(int).tolist()
    deltas = portfolio["delta_vs_same_repeat_cadical"].astype(int).tolist()
    local_first = portfolio["local_first_stage_solved"].astype(int).tolist()
    c2_solves = portfolio["cadical_second_stage_solved"].astype(int).tolist()
    c_only_loss = portfolio["cadical_only_vs_portfolio"].astype(int).tolist()

    require(portfolio_solved == [79, 80, 80], f"Unexpected portfolio solved counts: {portfolio_solved}")
    require(cadical_solved == [75, 80, 80], f"Unexpected CaDiCaL solved counts: {cadical_solved}")
    require(deltas == [4, 0, 0], f"Unexpected matched deltas: {deltas}")
    require(local_first == [40, 40, 40], f"Unexpected local first-stage counts: {local_first}")
    require(c2_solves == [39, 40, 40], f"Unexpected CaDiCaL second-stage counts: {c2_solves}")
    require(c_only_loss == [0, 0, 0], f"Unexpected CaDiCaL-only losses: {c_only_loss}")

    require("79--80/200" in paper, "paper/main.tex must state 79--80/200 portfolio result")
    require("75, 80, and 80" in paper, "paper/main.tex must state repeated CaDiCaL 75, 80, and 80")
    require("+4, 0, and 0" in paper, "paper/main.tex must state matched deltas +4, 0, and 0")
    require(
        "boundary-sensitive rather than a robust solved-count win" in paper
        or "boundary-sensitive rather than repeated-baseline robust" in paper,
        "paper/main.tex must explicitly demote robust solved-count claim",
    )

    neural_counts = {
        row["method"]: int(float(row["solved_mean"]))
        for _, row in neural.iterrows()
    }
    expected_neural = {
        "one_shot": 48,
        "online_consistent_boundary400": 53,
        "old_compact": 54,
        "local_reopen_guarded": 54,
    }
    require(neural_counts == expected_neural, f"Unexpected neural solved counts: {neural_counts}")
    for count in ["48/200", "53/200", "54/200"]:
        require(count in paper, f"paper/main.tex missing neural-stage count {count}")

    overlap_counts = {row["question"]: int(row["count"]) for _, row in overlap.iterrows()}
    expected_overlap = {
        "Local solved / CaDiCaL unsolved in all repeats": 3,
        "Online solved / CaDiCaL unsolved in all repeats": 2,
        "Local-only over Online / CaDiCaL unsolved in all repeats": 1,
        "One-shot timeout recovered by Online": 5,
        "Local Correction open set": 4,
    }
    for key, expected in expected_overlap.items():
        actual = overlap_counts.get(key)
        require(actual == expected, f"Unexpected overlap count for {key}: {actual}")
    require("3sat\\_188.cnf" in paper, "paper/main.tex must name 3sat_188 as Local-only boundary gain")
    require("3sat\\_147.cnf" in paper, "paper/main.tex must name 3sat_147 in full overlap audit")
    require("CaDiCaL solved all & 2/4" in paper, "paper/main.tex must state CaDiCaL solves 2/4 Local open set")

    march_row = march.iloc[0]
    require(int(march_row["repeats"]) == 3, "Unexpected March repeat count")
    require(float(march_row["solved_strict60"]) == 184.0, "Unexpected March strict-60 solved count")
    require(float(march_row["solved_strict60_std"]) == 0.0, "Unexpected March strict-60 solved std")
    require(int(march_row["solved_strict60_min"]) == 184, "Unexpected March strict-60 solved min")
    require(int(march_row["solved_strict60_max"]) == 184, "Unexpected March strict-60 solved max")
    require(float(march_row["solved_external65"]) == 192.0, "Unexpected March external-65 solved count")
    require(float(march_row["solved_external65_std"]) == 0.0, "Unexpected March external-65 solved std")
    require(float(march_row["solved_after_60_before_65"]) == 8.0, "Unexpected March after-60 count")
    require(int(march_row["strict60_stable_instances"]) == 200, "Unexpected March stable instance count")
    require(march_repeats["solved_strict60"].astype(int).tolist() == [184, 184, 184], "Unexpected March repeat strict counts")
    require(march_repeats["solved_external65"].astype(int).tolist() == [192, 192, 192], "Unexpected March repeat external counts")
    local_overlap = march_overlap.loc[march_overlap["method"].eq("+ Local Boundary Correction")].iloc[0]
    require(int(local_overlap["method_only_vs_march_all"]) == 0, "Local should have no strict repeated-March complement")
    require(int(local_overlap["march_all_only_vs_method"]) == 130, "Unexpected March-all-only vs Local count")
    require("184/200" in paper, "paper/main.tex must state March strict-60 184/200")
    require("each of three repeats" in paper, "paper/main.tex must state repeated March strict-60 count")
    require("stable on all 200 instances" in paper, "paper/main.tex must state March instance stability")
    require("March" in paper, "paper/main.tex must discuss March baseline")
    require(
        "removes the current strong-baseline complementarity claim" in paper
        or "no solved-count complement against repeated March strict-60" in paper,
        "paper/main.tex must state March removes current strong-baseline complementarity",
    )
    gate_counts = {row["item"]: int(row["value"]) for _, row in strong_gate.iterrows()}
    expected_gate = {
        "available_executable_strong_solvers": 2,
        "missing_external_solver_families": 3,
        "march_strict60_hard_instances": 16,
        "neural_solved_on_march_hard": 0,
        "online_solved_on_march_hard": 0,
        "portfolio_solved_repeats_on_march_hard": 0,
        "cadical_solved_repeats_on_march_hard": 0,
    }
    for key, expected in expected_gate.items():
        actual = gate_counts.get(key)
        require(actual == expected, f"Unexpected stronger-CDCL gate count for {key}: {actual}")
    missing_external = solver_availability.loc[
        solver_availability["solver"].isin(["Kissat", "MapleSAT", "CryptoMiniSat"]),
        "executable",
    ].astype(bool)
    require(not missing_external.any(), "Kissat/MapleSAT/CryptoMiniSat unexpectedly available; rerun stronger-CDCL gate")

    lattice_counts = {row["method"]: int(row["solved"]) for _, row in lattice_methods.iterrows()}
    expected_lattice_counts = {
        "Glucose default": 13,
        "One-shot": 48,
        "Online-Consistent Selector": 53,
        "Old Compact": 54,
        "+ Local Boundary Correction": 54,
        "CaDiCaL any-repeat": 80,
        "CaDiCaL all-repeat": 75,
        "March strict-60 all-repeat": 184,
        "Local5 -> CaDiCaL55 any-repeat": 80,
        "Local5 -> CaDiCaL55 all-repeat": 79,
    }
    require(lattice_counts == expected_lattice_counts, f"Unexpected lattice method counts: {lattice_counts}")
    lattice_pair_rows = {row["comparison"]: row for _, row in lattice_pairs.iterrows()}
    expected_lattice_pairs = {
        "Online vs One-shot": (5, 0),
        "Local vs Online": (1, 0),
        "Local vs CaDiCaL-all": (5, 26),
        "Local vs March-all": (0, 130),
        "Online vs March-all": (0, 131),
        "CaDiCaL-all vs March-all": (0, 109),
        "Portfolio-all vs March-all": (0, 105),
    }
    for key, (left_only, right_only) in expected_lattice_pairs.items():
        row = lattice_pair_rows.get(key)
        require(row is not None, f"Missing lattice pair row: {key}")
        require(int(row["left_only"]) == left_only, f"Unexpected lattice left_only for {key}: {row['left_only']}")
        require(int(row["right_only"]) == right_only, f"Unexpected lattice right_only for {key}: {row['right_only']}")

    dataset_inventory = {
        int(row["size"]): int(row["instances"])
        for _, row in benchmark_datasets.iterrows()
    }
    require(dataset_inventory == {250: 200, 300: 200, 350: 200, 400: 200}, f"Unexpected benchmark inventory: {dataset_inventory}")
    march_gate = {
        int(row["size"]): (str(row["protocol"]), int(row["total"]), int(row["solved"]))
        for _, row in benchmark_march.iterrows()
    }
    expected_march_gate = {
        250: ("smoke20", 20, 20),
        300: ("smoke20", 20, 20),
        350: ("smoke20", 20, 20),
        400: ("full200_repeat3_strict60", 200, 184),
    }
    require(march_gate == expected_march_gate, f"Unexpected benchmark suitability March gate: {march_gate}")

    candidate_counts = {
        (str(row["family"]), int(row["size"]), str(row["solver"])): (int(row["total"]), int(row["solved"]))
        for _, row in candidate_summary.iterrows()
    }
    expected_candidate_counts = {
        ("3sat", 450, "cadical"): (8, 5),
        ("3sat", 450, "march"): (8, 2),
        ("3sat", 500, "cadical"): (8, 1),
        ("3sat", 500, "march"): (8, 2),
        ("coloring", 400, "cadical"): (8, 8),
        ("coloring", 400, "march"): (8, 8),
        ("coloring", 500, "cadical"): (8, 8),
        ("coloring", 500, "march"): (8, 7),
    }
    require(candidate_counts == expected_candidate_counts, f"Unexpected candidate smoke counts: {candidate_counts}")
    candidate_overlap_counts = {
        (str(row["family"]), int(row["size"])): (int(row["both_unknown"]), int(row["union_solved"]))
        for _, row in candidate_overlap.iterrows()
    }
    expected_candidate_overlap = {
        ("3sat", 450): (3, 5),
        ("3sat", 500): (6, 2),
        ("coloring", 400): (0, 8),
        ("coloring", 500): (0, 8),
    }
    require(candidate_overlap_counts == expected_candidate_overlap, f"Unexpected candidate overlap counts: {candidate_overlap_counts}")

    gate450_counts = {
        str(row["solver"]): (int(row["total"]), int(row["solved"]), int(row["unknown"]))
        for _, row in gate450_summary.iterrows()
    }
    expected_gate450_counts = {
        "cadical": (24, 11, 13),
        "march": (24, 6, 18),
    }
    require(gate450_counts == expected_gate450_counts, f"Unexpected 3SAT-450 gate counts: {gate450_counts}")
    gate450_overlap_row = gate450_overlap.iloc[0]
    require(int(gate450_overlap_row["both_unknown"]) == 13, "Unexpected 3SAT-450 both-unknown count")
    require(int(gate450_overlap_row["union_solved"]) == 11, "Unexpected 3SAT-450 union solved count")
    require(len(gate450_hard) == 13, f"Unexpected 3SAT-450 hard subset size: {len(gate450_hard)}")

    stale_patterns = [
        "50/200",
        "56/200",
        "50 -> 56",
        "50/200 -> 56/200",
        "47.752",
        "46.222",
        "45.498",
    ]
    stale_hits = [pattern for pattern in stale_patterns if pattern in paper]
    require(not stale_hits, f"paper/main.tex contains stale single-run claims: {stale_hits}")

    forbidden_positive_claims = [
        "robustly improves over CaDiCaL",
        "robust solved-count improvement over CaDiCaL",
        "dominates CaDiCaL",
        "performance superiority over CaDiCaL",
    ]
    forbidden_hits = [pattern for pattern in forbidden_positive_claims if pattern in combined_text]
    require(not forbidden_hits, f"Paper docs contain forbidden positive claims: {forbidden_hits}")

    labels = set(re.findall(r"\\label\{([^}]+)\}", paper))
    refs = set(re.findall(r"\\(?:ref|autoref)\{([^}]+)\}", paper))
    require(not (refs - labels), f"Missing LaTeX labels: {sorted(refs - labels)}")
    require(sum(1 for char in paper if ord(char) > 127) == 0, "paper/main.tex contains non-ASCII")

    print("paper claim verification passed")
    print(f"portfolio={portfolio_solved}, cadical={cadical_solved}, deltas={deltas}")
    print(f"neural_counts={neural_counts}")
    print(f"overlap_counts={expected_overlap}")
    print("march_strict60=184 x3, march_external65=192 x3, stable_instances=200")
    print(f"stronger_cdcl_gate={expected_gate}")
    print(f"failure_boundary_lattice={expected_lattice_counts}")
    print(f"benchmark_suitability_march_gate={expected_march_gate}")
    print(f"benchmark_candidate_smoke={expected_candidate_counts}")
    print(f"benchmark_3sat450_gate={expected_gate450_counts}, both_unknown=13")


if __name__ == "__main__":
    main()
