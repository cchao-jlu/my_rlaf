import unittest

import pandas as pd

from sweep_online_pairwise_veto_thresholds import build_focus_audit, distinct_policy_rows, vectorized_sweep


class OnlineThresholdSweepTest(unittest.TestCase):
    def test_vectorized_sweep_does_not_credit_unsupported_adapter_openings(self):
        frame = pd.DataFrame(
            {
                "risk_prob": [0.1],
                "recovery_prob": [0.9],
                "slowdown_prob": [0.1],
                "current_use_adapter": [False],
                "base_solved": [False],
                "base_time": [60.0],
                "current_solved": [False],
                "current_time": [60.0],
                "old_time": [60.0],
                "file_key": ["3sat_89.cnf"],
            }
        )

        sweep = vectorized_sweep(
            frame,
            risk_values=[0.5],
            recovery_values=[0.5],
            slowdown_values=[0.5],
        )

        row = sweep.iloc[0]
        self.assertEqual(row["unsupported_opened"], 1)
        self.assertEqual(row["supported"], False)
        self.assertEqual(row["selector_solved_est"], 0)
        self.assertEqual(row["mean_time_est"], 60.0)

    def test_build_focus_audit_deduplicates_policy_labels(self):
        frame = pd.DataFrame(
            {
                "file_key": ["3sat_89.cnf"],
                "current_use_adapter": [True],
                "risk_prob": [0.2],
                "recovery_prob": [0.8],
                "slowdown_prob": [0.1],
                "base_result": ["INDETERMINATE"],
                "base_time": [60.0],
                "old_result": ["SATISFIABLE"],
                "old_time": [1.0],
                "actual_result": ["SATISFIABLE"],
                "actual_time": [2.0],
            }
        )
        first = pd.Series([True], index=frame.index)
        duplicate = pd.Series([False], index=frame.index)

        audit = build_focus_audit(frame, [("policy_a", first), ("policy_a", duplicate)])

        self.assertEqual(audit["policy"].tolist(), ["policy_a"])
        self.assertEqual(audit["use_adapter"].tolist(), [1])

    def test_distinct_policy_rows_collapses_equivalent_decisions(self):
        frame = pd.DataFrame(
            {
                "risk_threshold": [0.5, 0.5000000001, 0.8],
                "recovery_threshold": [0.2, 0.2, 0.7],
                "slowdown_threshold": [0.3, 0.3, 0.1],
                "selected": [3, 3, 2],
                "decision_changed": [1, 1, 2],
                "selector_solved_est": [52, 52, 51],
                "lost_solution_est": [1, 1, 0],
                "recovered_timeout_est": [3, 3, 1],
                "mean_time_est": [46.0, 46.0, 47.0],
                "unsupported_opened": [0, 0, 0],
            }
        )

        distinct = distinct_policy_rows(frame)

        self.assertEqual(len(distinct), 2)
        self.assertEqual(distinct["selector_solved_est"].tolist(), [52, 51])


if __name__ == "__main__":
    unittest.main()
