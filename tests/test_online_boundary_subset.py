import unittest

import pandas as pd
from omegaconf import OmegaConf

from build_online_consistent_boundary_subset import select_boundary_subset
from train_two_stage_risk_controller import stage_selector_feature_union


class OnlineBoundarySubsetTest(unittest.TestCase):
    def test_selects_focus_outcomes_slowdowns_and_near_threshold_without_full_set(self):
        frame = pd.DataFrame(
            [
                {
                    "policy": "current_pairwise_veto",
                    "file_key": "3sat_163.cnf",
                    "use_adapter": 1,
                    "base_solved": 0,
                    "selected_solved": 1,
                    "lost_solution_est": 0,
                    "recovered_timeout_est": 1,
                    "selected_time_est": 2.0,
                    "base_time": 60.0,
                    "current_time": 2.0,
                    "old_time": 60.0,
                    "risk_prob": 0.7,
                    "recovery_prob": 0.8,
                    "slowdown_prob": 0.05,
                },
                {
                    "policy": "current_pairwise_veto",
                    "file_key": "3sat_122.cnf",
                    "use_adapter": 0,
                    "base_solved": 1,
                    "selected_solved": 0,
                    "lost_solution_est": 1,
                    "recovered_timeout_est": 0,
                    "selected_time_est": 61.0,
                    "base_time": 59.0,
                    "current_time": 61.0,
                    "old_time": 59.0,
                    "risk_prob": 0.796,
                    "recovery_prob": 0.1,
                    "slowdown_prob": 0.3,
                },
                {
                    "policy": "current_pairwise_veto",
                    "file_key": "3sat_88.cnf",
                    "use_adapter": 1,
                    "base_solved": 1,
                    "selected_solved": 1,
                    "lost_solution_est": 0,
                    "recovered_timeout_est": 0,
                    "selected_time_est": 3.0,
                    "base_time": 1.0,
                    "current_time": 3.0,
                    "old_time": 1.0,
                    "risk_prob": 0.5,
                    "recovery_prob": 0.5,
                    "slowdown_prob": 0.2,
                },
                {
                    "policy": "current_pairwise_veto",
                    "file_key": "3sat_near.cnf",
                    "use_adapter": 0,
                    "base_solved": 0,
                    "selected_solved": 0,
                    "lost_solution_est": 0,
                    "recovered_timeout_est": 0,
                    "selected_time_est": 60.0,
                    "base_time": 60.0,
                    "current_time": 60.0,
                    "old_time": 60.0,
                    "risk_prob": 0.7953,
                    "recovery_prob": 0.1,
                    "slowdown_prob": 0.9,
                },
                {
                    "policy": "current_pairwise_veto",
                    "file_key": "3sat_background.cnf",
                    "use_adapter": 0,
                    "base_solved": 0,
                    "selected_solved": 0,
                    "lost_solution_est": 0,
                    "recovered_timeout_est": 0,
                    "selected_time_est": 60.0,
                    "base_time": 60.0,
                    "current_time": 60.0,
                    "old_time": 60.0,
                    "risk_prob": 0.2,
                    "recovery_prob": 0.1,
                    "slowdown_prob": 0.9,
                },
            ]
        )

        subset = select_boundary_subset(
            frame,
            max_size=4,
            near_threshold_count=1,
            slowdown_count=1,
            focus_keys=["3sat_163.cnf"],
        )

        keys = set(subset["file_key"])
        self.assertLess(len(subset), len(frame))
        self.assertIn("3sat_163.cnf", keys)
        self.assertIn("3sat_122.cnf", keys)
        self.assertIn("3sat_88.cnf", keys)
        self.assertIn("3sat_near.cnf", keys)
        self.assertNotIn("3sat_background.cnf", keys)
        self.assertIn("current_recovered", subset.set_index("file_key").loc["3sat_163.cnf", "selection_tags"])
        self.assertIn("current_lost", subset.set_index("file_key").loc["3sat_122.cnf", "selection_tags"])
        self.assertIn("selected_slowdown", subset.set_index("file_key").loc["3sat_88.cnf", "selection_tags"])
        self.assertIn("near_threshold", subset.set_index("file_key").loc["3sat_near.cnf", "selection_tags"])

    def test_stage_selector_feature_union_keeps_existing_slowdown_veto_features(self):
        adapter = OmegaConf.create(
            {
                "selector_feature_names": ["old_feature"],
                "slowdown_selector_feature_names": [
                    "recovery_prob",
                    "warmup_c2000_event_entropy_norm",
                ],
            }
        )

        features = stage_selector_feature_union(
            adapter,
            risk_features=["warmup_c500_solved"],
            recovery_features=["warmup_c2000_decisions"],
        )

        self.assertEqual(
            features,
            [
                "warmup_c500_solved",
                "warmup_c2000_decisions",
                "recovery_prob",
                "warmup_c2000_event_entropy_norm",
            ],
        )


if __name__ == "__main__":
    unittest.main()
