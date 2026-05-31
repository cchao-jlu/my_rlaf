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


if __name__ == "__main__":
    main()
