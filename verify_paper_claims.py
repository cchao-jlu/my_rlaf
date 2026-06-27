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
    candidate_neural_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_candidate_neural_triage/summary.csv")
    candidate_neural_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_candidate_neural_triage/overlap.csv")
    transition_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_transition_band/solver_overlap.csv")
    transition_neural_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_transition_band_neural_triage/summary.csv")
    transition_neural_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_transition_band_neural_triage/overlap.csv")
    march_guidance_transition_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_march_guidance_transition_triage/summary.csv")
    march_guidance_transition_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_march_guidance_transition_triage/overlap.csv")
    march_guidance_transition_full_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_march_guidance_transition_full/strong_solver_overlap_summary.csv")
    march_sample_instance = pd.read_csv(ROOT / "runs/analysis/benchmark_march_sample_portfolio_triage/instance_summary.csv")
    march_sample_size = pd.read_csv(ROOT / "runs/analysis/benchmark_march_sample_portfolio_triage/size_summary.csv")
    march_sample_focused = pd.read_csv(ROOT / "runs/analysis/benchmark_march_sample_portfolio_multiseed/focused_sample_portfolio_summary.csv")
    gate450_summary = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/summary.csv")
    gate450_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/solver_overlap_by_repeat.csv")
    gate450_stable_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/solver_overlap_stable.csv")
    gate450_hard = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv")
    gate450_neural = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_neural_gate/method_summary.csv")
    gate450_neural_overlap = pd.read_csv(ROOT / "runs/analysis/benchmark_3sat450_neural_gate/strong_hard_neural_overlap.csv")

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
    candidate_neural_counts = {
        (str(row["family"]), int(row["size"]), str(row["method"]), int(row["seed"])): (int(row["n"]), int(row["solved"]))
        for _, row in candidate_neural_summary.iterrows()
    }
    expected_candidate_neural_counts = {}
    for seed in [1, 2, 3]:
        expected_candidate_neural_counts[("3sat", 450, "one_shot", seed)] = (3, 0)
        expected_candidate_neural_counts[("3sat", 450, "online_consistent_boundary400", seed)] = (3, 0)
        expected_candidate_neural_counts[("3sat", 500, "one_shot", seed)] = (6, 0)
        expected_candidate_neural_counts[("3sat", 500, "online_consistent_boundary400", seed)] = (6, 0)
    require(
        candidate_neural_counts == expected_candidate_neural_counts,
        f"Unexpected candidate neural triage counts: {candidate_neural_counts}",
    )
    candidate_neural_patterns = candidate_neural_overlap["pattern"].map(lambda value: str(value).zfill(2))
    require(
        set(candidate_neural_patterns) == {"00"},
        f"Unexpected candidate neural triage patterns: {sorted(candidate_neural_patterns.unique())}",
    )
    candidate_neural_subset = {
        (str(family), int(size)): int(count)
        for (family, size), count in candidate_neural_overlap.groupby(["family", "size"]).size().items()
    }
    require(candidate_neural_subset == {("3sat", 450): 3, ("3sat", 500): 6}, f"Unexpected candidate neural subset: {candidate_neural_subset}")

    transition_overlap_counts = {
        int(row["size"]): (int(row["total"]), int(row["both_solved"]), int(row["march_only"]), int(row["cadical_only"]), int(row["both_unknown"]), int(row["union_solved"]))
        for _, row in transition_overlap.iterrows()
    }
    expected_transition_overlap = {
        410: (12, 4, 5, 0, 3, 9),
        425: (12, 8, 1, 1, 2, 10),
        440: (12, 4, 0, 2, 6, 6),
    }
    require(transition_overlap_counts == expected_transition_overlap, f"Unexpected transition-band overlap: {transition_overlap_counts}")
    transition_neural_counts = {
        (int(row["size"]), str(row["method"]), int(row["seed"])): (int(row["n"]), int(row["solved"]))
        for _, row in transition_neural_summary.iterrows()
    }
    expected_transition_neural_counts = {}
    for seed in [1, 2, 3]:
        expected_transition_neural_counts[(410, "one_shot", seed)] = (3, 0)
        expected_transition_neural_counts[(410, "online_consistent_boundary400", seed)] = (3, 0)
        expected_transition_neural_counts[(425, "one_shot", seed)] = (2, 0)
        expected_transition_neural_counts[(425, "online_consistent_boundary400", seed)] = (2, 0)
        expected_transition_neural_counts[(440, "one_shot", seed)] = (6, 0)
        expected_transition_neural_counts[(440, "online_consistent_boundary400", seed)] = (6, 0)
    require(
        transition_neural_counts == expected_transition_neural_counts,
        f"Unexpected transition-band neural triage counts: {transition_neural_counts}",
    )
    transition_neural_patterns = transition_neural_overlap["pattern"].map(lambda value: str(value).zfill(2))
    require(
        set(transition_neural_patterns) == {"00"},
        f"Unexpected transition-band neural triage patterns: {sorted(transition_neural_patterns.unique())}",
    )
    transition_neural_subset = {
        int(size): int(count)
        for size, count in transition_neural_overlap.groupby("size").size().items()
    }
    require(transition_neural_subset == {410: 3, 425: 2, 440: 6}, f"Unexpected transition-band neural subset: {transition_neural_subset}")
    march_guidance_transition_counts = {
        (int(row["size"]), int(row["seed"])): (int(row["n"]), int(row["solved"]))
        for _, row in march_guidance_transition_summary.iterrows()
    }
    expected_march_guidance_transition_counts = {}
    for seed in [1, 2, 3]:
        expected_march_guidance_transition_counts[(410, seed)] = (3, 0)
        expected_march_guidance_transition_counts[(425, seed)] = (2, 0)
        expected_march_guidance_transition_counts[(440, seed)] = (6, 0)
    require(
        march_guidance_transition_counts == expected_march_guidance_transition_counts,
        f"Unexpected March-guidance transition triage counts: {march_guidance_transition_counts}",
    )
    march_guidance_transition_subset = {
        int(size): int(count)
        for size, count in march_guidance_transition_overlap.groupby("size").size().items()
    }
    require(
        march_guidance_transition_subset == {410: 3, 425: 2, 440: 6},
        f"Unexpected March-guidance transition subset: {march_guidance_transition_subset}",
    )
    require(
        int(march_guidance_transition_overlap["solved_seeds"].sum()) == 0,
        "March-guidance transition triage unexpectedly solved at least one seed",
    )
    march_guidance_transition_full_counts = {
        int(row["size"]): (
            int(row["march_solved"]),
            int(row["cadical_solved"]),
            int(row["strong_union_solved"]),
            int(row["march_guided_solved"]),
            int(row["guided_only_vs_union"]),
            int(row["guided_only_vs_march"]),
            int(row["march_only_vs_guided"]),
        )
        for _, row in march_guidance_transition_full_summary.iterrows()
    }
    expected_march_guidance_transition_full = {
        410: (9, 4, 9, 9, 0, 0, 0),
        425: (9, 9, 10, 10, 0, 1, 0),
        440: (4, 6, 6, 5, 0, 2, 1),
    }
    require(
        march_guidance_transition_full_counts == expected_march_guidance_transition_full,
        f"Unexpected March-guidance full transition overlap: {march_guidance_transition_full_counts}",
    )
    march_sample_size_counts = {
        int(row["size"]): (int(row["instances"]), int(row["num_samples"]), int(row["solved_any"]), float(row["mean_solved_samples"]), int(row["max_solved_samples"]))
        for _, row in march_sample_size.iterrows()
    }
    expected_march_sample_size = {
        410: (3, 4, 1, 2 / 3, 2),
        425: (2, 4, 0, 0.0, 0),
        440: (6, 4, 0, 0.0, 0),
    }
    require(march_sample_size_counts.keys() == expected_march_sample_size.keys(), f"Unexpected sampled March sizes: {march_sample_size_counts}")
    for size, expected in expected_march_sample_size.items():
        actual = march_sample_size_counts[size]
        require(actual[:3] == expected[:3], f"Unexpected sampled March count tuple for {size}: {actual}")
        require(abs(actual[3] - expected[3]) < 1e-9, f"Unexpected sampled March mean for {size}: {actual[3]}")
        require(actual[4] == expected[4], f"Unexpected sampled March max for {size}: {actual[4]}")
    march_sample_solved = march_sample_instance[march_sample_instance["solved_any"].astype(bool)]
    require(len(march_sample_instance) == 11, f"Unexpected sampled March instance count: {len(march_sample_instance)}")
    require(len(march_sample_solved) == 1, f"Unexpected sampled March solved-any count: {len(march_sample_solved)}")
    solved_row = march_sample_solved.iloc[0]
    require(int(solved_row["size"]) == 410, f"Unexpected sampled March solved size: {solved_row.to_dict()}")
    require(str(solved_row["file_key"]) == "3sat_2.cnf", f"Unexpected sampled March solved instance: {solved_row.to_dict()}")
    require(int(solved_row["samples"]) == 4, f"Unexpected sampled March sample count: {solved_row.to_dict()}")
    require(int(solved_row["solved_samples"]) == 2, f"Unexpected sampled March solved samples: {solved_row.to_dict()}")
    require(abs(float(solved_row["best_time"]) - 31.813) < 1e-6, f"Unexpected sampled March best time: {solved_row.to_dict()}")
    focused_rows = {
        (int(row["size"]), str(row["file_key"])): row
        for _, row in march_sample_focused.iterrows()
    }
    expected_focused = {
        (410, "3sat_2.cnf"): (3, 16, 48, 37, 35, 3, 3),
        (410, "3sat_3.cnf"): (3, 16, 48, 0, 0, 0, 0),
        (410, "3sat_8.cnf"): (3, 16, 48, 0, 0, 0, 0),
        (440, "3sat_8.cnf"): (3, 16, 48, 5, 4, 3, 2),
    }
    require(focused_rows.keys() == expected_focused.keys(), f"Unexpected focused sampled rows: {sorted(focused_rows)}")
    for key, expected in expected_focused.items():
        row = focused_rows[key]
        actual = (
            int(row["sample_seeds"]),
            int(row["samples_per_seed"]),
            int(row["total_samples"]),
            int(row["returned_solved_samples"]),
            int(row["strict60_solved_samples"]),
            int(row["returned_solved_seeds"]),
            int(row["strict60_solved_seeds"]),
        )
        require(actual == expected, f"Unexpected focused sampled values for {key}: {actual}")
    require(
        bool(focused_rows[(410, "3sat_2.cnf")]["strict60_solved_any"]),
        "410/3sat_2.cnf should have strict-60 sampled complementarity",
    )
    require(
        bool(focused_rows[(440, "3sat_8.cnf")]["strict60_solved_any"]),
        "440/3sat_8.cnf should have strict-60 sampled complementarity",
    )

    gate450_counts = {
        (str(row["solver"]), int(row["repeat"])): (int(row["total"]), int(row["solved"]), int(row["unknown"]))
        for _, row in gate450_summary.iterrows()
    }
    expected_gate450_counts = {
        ("cadical", 0): (24, 11, 13),
        ("cadical", 1): (24, 11, 13),
        ("cadical", 2): (24, 11, 13),
        ("march", 0): (24, 6, 18),
        ("march", 1): (24, 6, 18),
        ("march", 2): (24, 6, 18),
    }
    require(gate450_counts == expected_gate450_counts, f"Unexpected 3SAT-450 gate counts: {gate450_counts}")
    for _, row in gate450_overlap.iterrows():
        require(int(row["both_unknown"]) == 13, f"Unexpected 3SAT-450 repeat both-unknown count: {row.to_dict()}")
        require(int(row["union_solved"]) == 11, f"Unexpected 3SAT-450 repeat union solved count: {row.to_dict()}")
    gate450_stable_row = gate450_stable_overlap.iloc[0]
    require(int(gate450_stable_row["repeats"]) == 3, "Unexpected 3SAT-450 stable repeat count")
    require(int(gate450_stable_row["both_unsolved_all"]) == 13, "Unexpected 3SAT-450 stable hard count")
    require(int(gate450_stable_row["union_solved_any"]) == 11, "Unexpected 3SAT-450 stable union count")
    require(len(gate450_hard) == 13, f"Unexpected 3SAT-450 hard subset size: {len(gate450_hard)}")
    gate450_neural_counts = {
        row["method"]: (int(row["seeds"]), float(row["solved_mean"]), int(row["solved_min"]), int(row["solved_max"]))
        for _, row in gate450_neural.iterrows()
    }
    expected_gate450_neural = {
        "one_shot": (3, 0.0, 0, 0),
        "online_consistent_boundary400": (3, 0.0, 0, 0),
    }
    require(gate450_neural_counts == expected_gate450_neural, f"Unexpected 3SAT-450 neural gate counts: {gate450_neural_counts}")
    require(len(gate450_neural_overlap) == 13, f"Unexpected 3SAT-450 neural overlap size: {len(gate450_neural_overlap)}")
    gate450_patterns = gate450_neural_overlap["pattern"].map(lambda value: str(value).zfill(2))
    require(
        set(gate450_patterns) == {"00"},
        f"Unexpected 3SAT-450 neural solved pattern: {sorted(gate450_patterns.unique())}",
    )

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
    print("benchmark_candidate_neural_triage=3sat450 0/3 x3, 3sat500 0/6 x3")
    print("benchmark_transition_band=410/425/440 mixed strong-solver gate, neural 0/11 x3")
    print("march_guidance_transition_triage=0/11 x3")
    print("march_guidance_transition_full=guided_only_vs_union 0, guided_only_vs_march 3")
    print("march_sample_portfolio_triage=1/11 solved-any, 3sat_2.cnf solved by 2/4 samples")
    print("march_sample_portfolio_focused=410/3sat_2 strict60 35/48, 440/3sat_8 strict60 4/48")
    print(f"benchmark_3sat450_gate={expected_gate450_counts}, both_unknown=13")
    print(f"benchmark_3sat450_neural_gate={expected_gate450_neural}, patterns=00 x13")


if __name__ == "__main__":
    main()
