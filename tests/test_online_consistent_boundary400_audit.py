import unittest

import pandas as pd

from audit_online_consistent_boundary400_decisions import (
    decision_change,
    diagnose_decision,
    map_cnf_ids_to_file_keys,
)
from sweep_online_consistent_boundary400_thresholds import (
    evaluate_threshold_policy,
    prepare_policy_branches,
)


class OnlineConsistentBoundary400AuditTest(unittest.TestCase):
    def test_cnf_id_mapping_uses_dataset_order(self):
        frame = pd.DataFrame({"cnf_id": [1, 0]})
        files = ["3sat_0.cnf", "3sat_1.cnf"]

        mapped = map_cnf_ids_to_file_keys(frame, files=files)

        self.assertEqual(mapped["file_key"].tolist(), ["3sat_1.cnf", "3sat_0.cnf"])

    def test_decision_diagnosis_marks_closed_old_adapter_slowdown(self):
        row = pd.Series(
            {
                "decision_change": "new_closed_old_on",
                "outcome_vs_old": "slower_both_solved",
            }
        )

        self.assertEqual(decision_change(old_use=True, new_use=False), "new_closed_old_on")
        self.assertIn("关闭旧 compact", diagnose_decision(row))

    def test_threshold_policy_uses_observed_old_adapter_proxy_and_flags_unknown_open(self):
        frame = pd.DataFrame(
            [
                {
                    "file_key": "observed_old.cnf",
                    "base_result": "INDETERMINATE",
                    "base_solved": False,
                    "base_time": 60.0,
                    "old_result": "SATISFIABLE",
                    "old_solved": True,
                    "old_time": 12.0,
                    "new_result": "INDETERMINATE",
                    "new_solved": False,
                    "new_time": 60.5,
                    "old_original_use_adapter": 1,
                    "selector_use_adapter": 0,
                    "risk_prob": 0.2,
                    "recovery_prob": 0.9,
                    "slowdown_prob": 0.1,
                },
                {
                    "file_key": "unknown.cnf",
                    "base_result": "INDETERMINATE",
                    "base_solved": False,
                    "base_time": 60.0,
                    "old_result": "INDETERMINATE",
                    "old_solved": False,
                    "old_time": 60.4,
                    "new_result": "INDETERMINATE",
                    "new_solved": False,
                    "new_time": 60.5,
                    "old_original_use_adapter": 0,
                    "selector_use_adapter": 0,
                    "risk_prob": 0.2,
                    "recovery_prob": 0.9,
                    "slowdown_prob": 0.1,
                },
            ]
        )
        prepared = prepare_policy_branches(frame)

        result = evaluate_threshold_policy(
            prepared,
            risk_threshold=0.3,
            recovery_threshold=0.8,
            slowdown_threshold=0.2,
        )

        self.assertEqual(result["unsupported_opened"], 1)
        self.assertEqual(result["recovered_timeout_vs_base_est"], 1)
        self.assertEqual(result["selector_solved_est"], 1)

    def test_threshold_policy_keeps_current_actual_when_decision_unchanged(self):
        frame = pd.DataFrame(
            [
                {
                    "file_key": "closed_recovered.cnf",
                    "base_result": "INDETERMINATE",
                    "base_solved": False,
                    "base_time": 60.0,
                    "old_result": "INDETERMINATE",
                    "old_solved": False,
                    "old_time": 60.4,
                    "new_result": "SATISFIABLE",
                    "new_solved": True,
                    "new_time": 25.0,
                    "old_original_use_adapter": 0,
                    "selector_use_adapter": 0,
                    "risk_prob": 0.8,
                    "recovery_prob": 0.1,
                    "slowdown_prob": 0.9,
                }
            ]
        )
        prepared = prepare_policy_branches(frame)

        result = evaluate_threshold_policy(
            prepared,
            risk_threshold=0.3,
            recovery_threshold=0.8,
            slowdown_threshold=0.2,
        )

        self.assertEqual(result["selector_solved_est"], 1)
        self.assertAlmostEqual(result["mean_time_est"], 25.0)


if __name__ == "__main__":
    unittest.main()
