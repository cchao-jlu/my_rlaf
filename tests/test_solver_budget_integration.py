import unittest

import numpy as np

from src.solving.solver import solve_cnf


def pigeonhole_cnf(pigeons: int, holes: int) -> tuple[list[list[int]], int]:
    clauses: list[list[int]] = []

    def var(pigeon: int, hole: int) -> int:
        return pigeon * holes + hole + 1

    for pigeon in range(pigeons):
        clauses.append([var(pigeon, hole) for hole in range(holes)])

    for hole in range(holes):
        for first in range(pigeons):
            for second in range(first + 1, pigeons):
                clauses.append([-var(first, hole), -var(second, hole)])

    return clauses, pigeons * holes


class SolverBudgetIntegrationTest(unittest.TestCase):
    def test_weighted_glucose_conflict_budget_stops_during_search(self):
        clauses, num_vars = pigeonhole_cnf(pigeons=5, holes=4)
        var_params = np.ones((num_vars, 2), dtype=float)

        stats = solve_cnf(
            clauses,
            var_params=var_params,
            solver="glucose",
            **{
                "cpu-lim": 5,
                "conf-lim": 1,
                "rnd-freq": 0.0,
                "K": 0.1,
            },
        )

        self.assertEqual(stats.get("Result"), "INDETERMINATE")
        self.assertLessEqual(stats.get("conflicts", 0), 1)

    def test_weighted_glucose_emits_literal_polarity_events(self):
        clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
        var_params = np.ones((2, 2), dtype=float)

        stats = solve_cnf(
            clauses,
            var_params=var_params,
            solver="glucose",
            **{
                "cpu-lim": 5,
                "conf-lim": 5,
                "rnd-freq": 0.0,
                "K": 0.1,
                "collect-events": True,
            },
        )

        for key in [
            "event_var_pos_decisions",
            "event_var_neg_decisions",
            "event_var_pos_propagations",
            "event_var_neg_propagations",
            "event_var_pos_conflict_lits",
            "event_var_neg_conflict_lits",
            "event_var_pos_assignments",
            "event_var_neg_assignments",
        ]:
            self.assertIn(key, stats)
            self.assertEqual(len(stats[key]), 2)


if __name__ == "__main__":
    unittest.main()
