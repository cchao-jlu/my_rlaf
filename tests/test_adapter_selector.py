import unittest

import pandas as pd
import torch

from src.training.adapter_selector import (
    choose_threshold_for_time,
    fit_linear_selector,
    selected_time,
    selector_training_frame,
)
from train_adapter_selector import selector_specs_from_args


class AdapterSelectorTest(unittest.TestCase):
    def test_fit_linear_selector_learns_separable_labels(self):
        features = torch.tensor(
            [
                [-2.0],
                [-1.0],
                [1.0],
                [2.0],
            ],
            dtype=torch.float32,
        )
        labels = torch.tensor([0.0, 0.0, 1.0, 1.0], dtype=torch.float32)

        selector, probs = fit_linear_selector(
            features,
            labels,
            feature_names=["base_rho_mean"],
            epochs=300,
            lr=0.1,
            l2=0.0,
        )

        self.assertEqual(selector.feature_names, ["base_rho_mean"])
        self.assertEqual(len(selector.weights), 1)
        self.assertLess(float(probs[0]), 0.5)
        self.assertGreater(float(probs[-1]), 0.5)

    def test_choose_threshold_for_time_selects_faster_policy(self):
        base_time = torch.tensor([10.0, 10.0, 5.0, 5.0])
        adapter_time = torch.tensor([5.0, 5.0, 10.0, 10.0])
        probabilities = torch.tensor([0.9, 0.8, 0.2, 0.1])

        threshold, mean_time = choose_threshold_for_time(base_time, adapter_time, probabilities)

        self.assertLessEqual(threshold, 0.8)
        self.assertGreater(threshold, 0.2)
        self.assertEqual(mean_time, 5.0)
        self.assertTrue(torch.allclose(
            selected_time(base_time, adapter_time, probabilities, threshold),
            torch.tensor([5.0, 5.0, 5.0, 5.0]),
        ))

    def test_selector_training_frame_labels_adapter_wins(self):
        features = pd.DataFrame({"cnf_id": [0, 1], "base_rho_mean": [0.1, -0.1]})
        base_eval = pd.DataFrame({"cnf_id": [0, 1], "time": [10.0, 5.0]})
        adapter_eval = pd.DataFrame({"cnf_id": [0, 1], "time": [6.0, 8.0]})

        frame = selector_training_frame(features, base_eval, adapter_eval)

        self.assertEqual(frame["label"].tolist(), [1.0, 0.0])
        self.assertEqual(frame["gain"].tolist(), [4.0, -3.0])

    def test_selector_specs_from_args_supports_repeated_dataset_triples(self):
        specs = selector_specs_from_args(
            datasets=["300/*.cnf", "350/*.cnf"],
            base_eval_csvs=["base300.csv", "base350.csv"],
            adapter_eval_csvs=["adapter300.csv", "adapter350.csv"],
        )

        self.assertEqual(specs, [
            ("300/*.cnf", "base300.csv", "adapter300.csv"),
            ("350/*.cnf", "base350.csv", "adapter350.csv"),
        ])

    def test_selector_specs_from_args_rejects_mismatched_counts(self):
        with self.assertRaises(ValueError):
            selector_specs_from_args(
                datasets=["300/*.cnf", "350/*.cnf"],
                base_eval_csvs=["base300.csv"],
                adapter_eval_csvs=["adapter300.csv", "adapter350.csv"],
            )


if __name__ == "__main__":
    unittest.main()
