import unittest

import pandas as pd

from summarize_residual_elite_mining import summarize


class ResidualEliteMiningSummaryTest(unittest.TestCase):
    def test_summary_counts_completion_and_keeps_mining_until_complete(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat"],
                "size": [410, 410, 425],
                "file_key": ["a.cnf", "b.cnf", "c.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "sample_seed": [1729, 1729],
                "solved_samples": [0, 2],
                "solved_any": [False, True],
                "best_time": [60.0, 3.0],
                "best_sample_id": [-1, 7],
                "raw_grid_complete": [True, True],
            }
        )

        summary, remaining = summarize(expected, completed, min_positive_instances=1)

        row = summary.iloc[0]
        self.assertEqual(int(row["expected_instances"]), 3)
        self.assertEqual(int(row["completed_instances"]), 2)
        self.assertEqual(int(row["remaining_instances"]), 1)
        self.assertEqual(int(row["positive_instances"]), 1)
        self.assertEqual(int(row["solved_samples"]), 2)
        self.assertEqual(bool(row["positive_floor_met"]), True)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertEqual(remaining.iloc[0]["file_key"], "c.cnf")

    def test_summary_is_ready_only_when_complete_and_positive_floor_met(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "sample_seed": [1729, 1729],
                "solved_samples": [1, 2],
                "solved_any": [True, True],
                "best_time": [4.0, 3.0],
                "best_sample_id": [1, 7],
                "raw_grid_complete": [True, True],
            }
        )

        summary, remaining = summarize(expected, completed, min_positive_instances=2)

        row = summary.iloc[0]
        self.assertEqual(int(row["remaining_instances"]), 0)
        self.assertEqual(bool(row["positive_floor_met"]), True)
        self.assertEqual(bool(row["complete_mining"]), True)
        self.assertEqual(row["decision"], "ready_for_formal_elite_manifest")
        self.assertTrue(remaining.empty)

    def test_summary_marks_complete_sparse_when_floor_not_met(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "sample_seed": [1729, 1729],
                "solved_samples": [1, 0],
                "solved_any": [True, False],
                "best_time": [4.0, 60.0],
                "best_sample_id": [1, -1],
                "raw_grid_complete": [True, True],
            }
        )

        summary, _ = summarize(expected, completed, min_positive_instances=2)

        row = summary.iloc[0]
        self.assertEqual(bool(row["positive_floor_met"]), False)
        self.assertEqual(bool(row["complete_mining"]), True)
        self.assertEqual(row["decision"], "complete_but_sparse")

    def test_summary_keeps_mining_when_positive_floor_not_met(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "sample_seed": [1729],
                "solved_samples": [0],
                "solved_any": [False],
                "best_time": [60.0],
                "best_sample_id": [-1],
                "raw_grid_complete": [True],
            }
        )

        summary, _ = summarize(expected, completed, min_positive_instances=1)

        self.assertEqual(bool(summary.iloc[0]["positive_floor_met"]), False)
        self.assertEqual(bool(summary.iloc[0]["complete_mining"]), False)
        self.assertEqual(summary.iloc[0]["decision"], "continue_mining")

    def test_summary_does_not_count_incomplete_raw_grid_as_completed(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "sample_seed": [1729, 1729],
                "solved_samples": [1, 1],
                "solved_any": [True, True],
                "best_time": [4.0, 3.0],
                "best_sample_id": [1, 7],
                "raw_grid_complete": [True, False],
            }
        )

        summary, remaining = summarize(expected, completed, min_positive_instances=1)

        row = summary.iloc[0]
        self.assertEqual(int(row["summary_completed_instances"]), 2)
        self.assertEqual(int(row["completed_instances"]), 1)
        self.assertEqual(int(row["raw_incomplete_instances"]), 1)
        self.assertEqual(int(row["unexpected_artifact_instances"]), 0)
        self.assertEqual(int(row["unexpected_raw_complete_instances"]), 0)
        self.assertEqual(bool(row["raw_artifacts_complete"]), False)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertEqual(remaining.iloc[0]["file_key"], "b.cnf")

    def test_summary_rejects_unexpected_artifacts_even_when_expected_split_is_complete(self):
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
                "size": [410, 410, 425],
                "file_key": ["a.cnf", "b.cnf", "extra.cnf"],
                "sample_seed": [1729, 1729, 1729],
                "solved_samples": [1, 1, 1],
                "solved_any": [True, True, True],
                "best_time": [4.0, 3.0, 2.0],
                "best_sample_id": [1, 7, 0],
                "raw_grid_complete": [True, True, True],
            }
        )

        summary, remaining = summarize(expected, completed, min_positive_instances=2)

        row = summary.iloc[0]
        self.assertEqual(int(row["completed_instances"]), 2)
        self.assertEqual(int(row["summary_completed_instances"]), 2)
        self.assertEqual(int(row["unexpected_artifact_instances"]), 1)
        self.assertEqual(int(row["unexpected_raw_complete_instances"]), 1)
        self.assertEqual(int(row["remaining_instances"]), 0)
        self.assertEqual(int(row["positive_instances"]), 2)
        self.assertEqual(bool(row["positive_floor_met"]), True)
        self.assertEqual(bool(row["complete_mining"]), False)
        self.assertEqual(bool(row["raw_artifacts_complete"]), False)
        self.assertEqual(row["decision"], "continue_mining")
        self.assertTrue(remaining.empty)

    def test_summary_requires_raw_grid_audit_column(self):
        expected = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )
        completed = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "sample_seed": [1729],
                "solved_samples": [1],
                "solved_any": [True],
                "best_time": [4.0],
                "best_sample_id": [1],
            }
        )

        with self.assertRaisesRegex(ValueError, "raw_grid_complete"):
            summarize(expected, completed, min_positive_instances=1)


if __name__ == "__main__":
    unittest.main()
