import unittest

import pandas as pd
import torch

from build_boundary_focused_trace import add_boundary_labels
from train_pairwise_recovery_selector import (
    choose_focus_threshold,
    choose_positive_floor_threshold,
    focus_keys_from_lists,
    choose_threshold,
    make_pair_indices,
)
from train_easy_slowdown_filter import add_filter_labels


class BoundaryPairwiseSelectorTest(unittest.TestCase):
    def test_boundary_labels_mark_recovery_positive_and_easy_slowdown_negative(self):
        frame = pd.DataFrame(
            [
                {
                    "file_key": "3sat_163.cnf",
                    "base_solved": False,
                    "adapter_solved": True,
                    "base_time": 60.0,
                    "adapter_time": 25.0,
                    "counterfactual_reason": "recovered_timeout",
                },
                {
                    "file_key": "3sat_25.cnf",
                    "base_solved": True,
                    "adapter_solved": True,
                    "base_time": 1.5,
                    "adapter_time": 20.0,
                    "counterfactual_reason": "neutral",
                },
                {
                    "file_key": "3sat_140.cnf",
                    "base_solved": True,
                    "adapter_solved": True,
                    "base_time": 40.0,
                    "adapter_time": 5.0,
                    "counterfactual_reason": "hard_speedup",
                },
            ]
        )

        labelled = add_boundary_labels(frame)

        by_key = labelled.set_index("file_key")
        self.assertEqual(by_key.loc["3sat_163.cnf", "boundary_label"], 1.0)
        self.assertEqual(by_key.loc["3sat_163.cnf", "boundary_reason"], "hard_recovery")
        self.assertEqual(by_key.loc["3sat_25.cnf", "boundary_label"], 0.0)
        self.assertEqual(by_key.loc["3sat_25.cnf", "boundary_reason"], "easy_slowdown")
        self.assertEqual(by_key.loc["3sat_140.cnf", "boundary_label"], 1.0)
        self.assertEqual(by_key.loc["3sat_140.cnf", "boundary_reason"], "hard_speedup")

    def test_pair_indices_rank_recovery_above_slowdown(self):
        frame = pd.DataFrame(
            {
                "boundary_label": [1.0, 1.0, 0.0, 0.0],
                "boundary_pair_weight": [2.0, 1.0, 3.0, 1.0],
                "boundary_reason": [
                    "hard_recovery",
                    "hard_speedup",
                    "easy_slowdown",
                    "lost_solution",
                ],
            }
        )

        pairs = make_pair_indices(frame, max_pairs=20)

        self.assertEqual(len(pairs), 4)
        self.assertTrue(all(frame.loc[pos, "boundary_label"] == 1.0 for pos, _, _ in pairs))
        self.assertTrue(all(frame.loc[neg, "boundary_label"] == 0.0 for _, neg, _ in pairs))
        self.assertIn((0, 2, 6.0), pairs)

    def test_threshold_prefers_recovery_before_zero_negative_policy(self):
        frame = pd.DataFrame(
            {
                "boundary_labelled": [True, True, True],
                "boundary_label": [1.0, 0.0, 0.0],
                "boundary_reason": ["hard_recovery", "easy_slowdown", "easy_slowdown"],
            }
        )
        probs = torch.tensor([0.72, 0.40, 0.20], dtype=torch.float32)

        threshold = choose_threshold(frame, probs, max_selected_fraction=0.5)

        self.assertLessEqual(threshold, 0.72)
        self.assertGreater(threshold, 0.40)

    def test_focus_threshold_opens_recovery_and_blocks_easy_slowdown(self):
        focus = pd.DataFrame(
            {
                "file_key": ["3sat_163.cnf", "3sat_25.cnf", "3sat_88.cnf"],
                "risk_prob": [0.70, 0.52, 0.59],
                "recovery_prob": [0.72, 0.21, 0.40],
            }
        )

        threshold = choose_focus_threshold(
            focus,
            risk_threshold=0.795,
            positive_keys=["3sat_163.cnf"],
            negative_keys=["3sat_25.cnf", "3sat_88.cnf"],
            fallback=0.9,
        )

        self.assertLessEqual(threshold, 0.72)
        self.assertGreater(threshold, 0.40)

    def test_focus_threshold_falls_back_when_recovery_and_negative_overlap(self):
        focus = pd.DataFrame(
            {
                "file_key": ["3sat_89.cnf", "3sat_88.cnf"],
                "risk_prob": [0.59, 0.59],
                "recovery_prob": [0.39, 0.52],
            }
        )

        threshold = choose_focus_threshold(
            focus,
            risk_threshold=0.795,
            positive_keys=["3sat_89.cnf"],
            negative_keys=["3sat_88.cnf"],
            fallback=0.7,
        )

        self.assertEqual(threshold, 0.7)

    def test_positive_floor_threshold_keeps_all_requested_recoveries(self):
        focus = pd.DataFrame(
            {
                "file_key": ["3sat_163.cnf", "3sat_89.cnf", "3sat_46.cnf"],
                "risk_prob": [0.70, 0.59, 0.56],
                "recovery_prob": [0.72, 0.39, 0.38],
            }
        )

        threshold = choose_positive_floor_threshold(
            focus,
            risk_threshold=0.795,
            positive_keys=["3sat_163.cnf", "3sat_89.cnf", "3sat_46.cnf"],
            fallback=0.9,
        )

        self.assertLess(threshold, 0.38)

    def test_focus_keys_include_requested_positive_and_negative_cases(self):
        keys = focus_keys_from_lists(
            ["3sat_163.cnf"],
            ["3sat_89.cnf", "3sat_46.cnf"],
            ["3sat_88.cnf"],
        )

        self.assertIn("3sat_163.cnf", keys)
        self.assertIn("3sat_89.cnf", keys)
        self.assertIn("3sat_46.cnf", keys)
        self.assertIn("3sat_88.cnf", keys)

    def test_slowdown_filter_labels_infer_base_bucket_when_missing(self):
        frame = pd.DataFrame(
            {
                "counterfactual_reason": ["easy_slowdown", "recovered_timeout"],
                "base_solved": [True, False],
                "base_time": [1.0, 60.0],
            }
        )

        labelled = add_filter_labels(frame)

        self.assertEqual(labelled.loc[0, "slowdown_filter_label"], 1.0)
        self.assertFalse(bool(labelled.loc[0, "slowdown_filter_keep_positive"]))
        self.assertTrue(bool(labelled.loc[1, "slowdown_filter_keep_positive"]))


if __name__ == "__main__":
    unittest.main()
