import unittest

import pandas as pd

from summarize_residual_multiseed_mining import summarize


class ResidualMultiseedMiningSummaryTest(unittest.TestCase):
    def test_summary_counts_instance_seed_pairs(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat"],
                "size": [410, 410, 410],
                "file_key": ["a.cnf", "a.cnf", "b.cnf"],
                "sample_seed": [1730, 1731, 1730],
                "solved_samples": [0, 2, 1],
                "solved_any": [False, True, True],
                "best_time": [60.0, 3.0, 4.0],
                "best_sample_id": [-1, 7, 1],
                "raw_grid_complete": [True, True, True],
            }
        )

        summary, remaining, positives = summarize(
            expected=expected,
            completed=completed,
            expected_sample_seeds=(1730, 1731),
            min_positive_instances=2,
        )

        row = summary.iloc[0]
        self.assertEqual(int(row["expected_seed_pairs"]), 4)
        self.assertEqual(int(row["completed_seed_pairs"]), 3)
        self.assertEqual(int(row["completed_instances_any_seed"]), 2)
        self.assertEqual(int(row["completed_instances_all_seeds"]), 1)
        self.assertEqual(int(row["remaining_seed_pairs"]), 1)
        self.assertEqual(int(row["positive_instances"]), 2)
        self.assertEqual(int(row["positive_seed_pairs"]), 2)
        self.assertEqual(int(row["solved_samples"]), 3)
        self.assertEqual(bool(row["positive_floor_met"]), True)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertEqual(remaining.iloc[0]["file_key"], "b.cnf")
        self.assertEqual(int(remaining.iloc[0]["sample_seed"]), 1731)
        self.assertEqual(len(positives), 2)

    def test_summary_is_ready_only_when_all_seed_pairs_complete(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat", "3sat"],
                "size": [410, 410, 410, 410],
                "file_key": ["a.cnf", "a.cnf", "b.cnf", "b.cnf"],
                "sample_seed": [1730, 1731, 1730, 1731],
                "solved_samples": [1, 0, 0, 2],
                "solved_any": [True, False, False, True],
                "best_time": [5.0, 60.0, 60.0, 4.0],
                "best_sample_id": [2, -1, -1, 3],
                "raw_grid_complete": [True, True, True, True],
            }
        )

        summary, remaining, _ = summarize(
            expected=expected,
            completed=completed,
            expected_sample_seeds=(1730, 1731),
            min_positive_instances=2,
        )

        row = summary.iloc[0]
        self.assertEqual(int(row["completed_seed_pairs"]), 4)
        self.assertEqual(int(row["completed_instances_all_seeds"]), 2)
        self.assertEqual(int(row["positive_instances"]), 2)
        self.assertEqual(bool(row["complete_mining"]), True)
        self.assertEqual(bool(row["raw_artifacts_complete"]), True)
        self.assertEqual(row["decision"], "ready_for_formal_multiseed_manifest")
        self.assertTrue(remaining.empty)

    def test_summary_does_not_count_incomplete_raw_seed_pair_as_complete(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "sample_seed": [1730, 1731],
                "solved_samples": [1, 1],
                "solved_any": [True, True],
                "best_time": [5.0, 4.0],
                "best_sample_id": [2, 3],
                "raw_grid_complete": [True, False],
            }
        )

        summary, remaining, positives = summarize(
            expected=expected,
            completed=completed,
            expected_sample_seeds=(1730, 1731),
            min_positive_instances=1,
        )

        row = summary.iloc[0]
        self.assertEqual(int(row["summary_completed_seed_pairs"]), 2)
        self.assertEqual(int(row["completed_seed_pairs"]), 1)
        self.assertEqual(int(row["raw_incomplete_seed_pairs"]), 1)
        self.assertEqual(int(row["remaining_seed_pairs"]), 1)
        self.assertEqual(int(row["positive_instances"]), 1)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(bool(row["raw_artifacts_complete"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertEqual(int(remaining.iloc[0]["sample_seed"]), 1731)
        self.assertEqual(len(positives), 1)

    def test_summary_rejects_ready_when_extra_or_duplicate_seed_pair_exists(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat"],
                "size": [410, 410, 410],
                "file_key": ["a.cnf", "a.cnf", "extra.cnf"],
                "sample_seed": [1730, 1730, 1730],
                "solved_samples": [1, 1, 1],
                "solved_any": [True, True, True],
                "best_time": [5.0, 4.0, 2.0],
                "best_sample_id": [2, 3, 0],
                "raw_grid_complete": [True, True, True],
            }
        )

        summary, remaining, _ = summarize(
            expected=expected,
            completed=completed,
            expected_sample_seeds=(1730,),
            min_positive_instances=1,
        )

        row = summary.iloc[0]
        self.assertEqual(int(row["completed_seed_pairs"]), 1)
        self.assertEqual(int(row["duplicate_summary_seed_pairs"]), 1)
        self.assertEqual(int(row["unexpected_artifact_seed_pairs"]), 1)
        self.assertEqual(bool(row["positive_floor_met"]), True)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(bool(row["raw_artifacts_complete"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertTrue(remaining.empty)


if __name__ == "__main__":
    unittest.main()
