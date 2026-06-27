import unittest

import pandas as pd
import torch

from build_residual_contrastive_replay_manifest import (
    build_manifest,
    contrastive_group_count,
    enforce_contrastive_floor,
    positive_instance_count,
)
from train_residual_contrastive_replay import (
    enforce_contrastive_floor as enforce_training_contrastive_floor,
    grouped_batches,
    pairwise_margin_loss,
)


class ResidualContrastiveReplayTest(unittest.TestCase):
    def test_manifest_keeps_solved_and_same_instance_failed_samples(self):
        raw = pd.DataFrame(
            {
                "family": ["3sat"] * 6,
                "size": [410] * 6,
                "file_key": ["a.cnf", "a.cnf", "a.cnf", "b.cnf", "b.cnf", "c.cnf"],
                "sample_seed": [1729] * 6,
                "solver_seed": [1729] * 6,
                "num_samples_generated": [16] * 6,
                "sample_id": [0, 1, 2, 0, 1, 0],
                "Result": ["UNKNOWN", "SATISFIABLE", "SATISFIABLE", "UNSATISFIABLE", "UNKNOWN", "SATISFIABLE"],
                "CPU time": [60.0, 4.0, 2.0, 5.0, 60.0, 1.0],
                "dead_ends_in_main": [1.0, 10.0, 20.0, 15.0, 2.0, 30.0],
                "decisions": [1.0, 10.0, 20.0, 15.0, 2.0, 30.0],
                "file": ["data/a.cnf", "data/a.cnf", "data/a.cnf", "data/b.cnf", "data/b.cnf", "data/c.cnf"],
                "source_raw_csv": ["raw.csv"] * 6,
                "source_raw_sha256": ["0" * 64] * 6,
            }
        )

        manifest = build_manifest(
            raw=raw,
            split_map={
                ("3sat", 410, "a.cnf"): {
                    "split": "residual_train",
                    "cnf_path": "/abs/a.cnf",
                    "row_id": "a",
                },
                ("3sat", 410, "b.cnf"): {
                    "split": "residual_train",
                    "cnf_path": "/abs/b.cnf",
                    "row_id": "b",
                },
            },
            checkpoint=None,
            max_positives_per_instance=1,
            max_negatives_per_instance=1,
            negative_selection="low_progress",
            random_seed=1729,
        )

        self.assertEqual(len(manifest), 4)
        self.assertEqual(positive_instance_count(manifest), 2)
        self.assertEqual(contrastive_group_count(manifest), 2)
        a_positive = manifest[
            manifest["file_key"].eq("a.cnf") & manifest["sample_role"].eq("positive")
        ].iloc[0]
        self.assertEqual(int(a_positive["sample_id"]), 2)
        a_negative = manifest[
            manifest["file_key"].eq("a.cnf") & manifest["sample_role"].eq("negative")
        ].iloc[0]
        self.assertEqual(int(a_negative["sample_id"]), 0)
        self.assertEqual(a_negative["cnf_path"], "/abs/a.cnf")

    def test_manifest_floor_rejects_sparse_contrastive_groups(self):
        manifest = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "target_label": [1],
            }
        )

        with self.assertRaisesRegex(ValueError, "too few positive contrastive instances"):
            enforce_contrastive_floor(manifest, min_positive_instances=1)

    def test_training_floor_rejects_missing_negative_groups(self):
        manifest = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "target_label": [1],
            }
        )

        with self.assertRaisesRegex(ValueError, "too few contrastive groups"):
            enforce_training_contrastive_floor(manifest, min_positive_instances=1, label="train")

    def test_pairwise_margin_loss_prefers_positive_over_negative_log_prob(self):
        labels = torch.tensor([1.0, 0.0])
        good = pairwise_margin_loss(torch.tensor([0.5, 0.0]), labels, margin=0.1)
        bad = pairwise_margin_loss(torch.tensor([0.0, 0.5]), labels, margin=0.1)

        self.assertLess(float(good), float(bad))

    def test_pairwise_margin_loss_is_group_aware(self):
        labels = torch.tensor([1.0, 0.0])
        separated = pairwise_margin_loss(
            torch.tensor([0.0, 10.0]),
            labels,
            margin=0.1,
            group_ids=torch.tensor([0, 1]),
        )
        mixed = pairwise_margin_loss(
            torch.tensor([0.0, 10.0]),
            labels,
            margin=0.1,
            group_ids=torch.tensor([0, 0]),
        )

        self.assertAlmostEqual(float(separated), 0.0)
        self.assertGreater(float(mixed), 1.0)

    def test_grouped_batches_do_not_split_instance_groups(self):
        groups = [["a_pos", "a_neg"], ["b_pos", "b_neg", "b_neg2"], ["c_pos"]]

        batches = grouped_batches(groups, max_samples=4, shuffle=False, rng=None)

        self.assertEqual(batches, [["a_pos", "a_neg"], ["b_pos", "b_neg", "b_neg2", "c_pos"]])


if __name__ == "__main__":
    unittest.main()
