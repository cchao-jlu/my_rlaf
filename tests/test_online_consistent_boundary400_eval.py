import unittest

import pandas as pd

from summarize_online_consistent_boundary400_eval import outcome_vs


class OnlineConsistentBoundary400EvalTest(unittest.TestCase):
    def test_outcome_vs_old_marks_recovered_and_lost(self):
        recovered = pd.Series(
            {
                "old_solved": False,
                "new_solved": True,
                "delta_time_vs_old": -10.0,
            }
        )
        lost = pd.Series(
            {
                "old_solved": True,
                "new_solved": False,
                "delta_time_vs_old": 10.0,
            }
        )

        self.assertEqual(outcome_vs(recovered, "old"), "recovered_timeout")
        self.assertEqual(outcome_vs(lost, "old"), "lost_solution")

    def test_outcome_vs_old_uses_time_epsilon_for_both_solved(self):
        faster = pd.Series({"old_solved": True, "new_solved": True, "delta_time_vs_old": -0.2})
        tie = pd.Series({"old_solved": True, "new_solved": True, "delta_time_vs_old": 0.05})
        slower = pd.Series({"old_solved": True, "new_solved": True, "delta_time_vs_old": 0.2})

        self.assertEqual(outcome_vs(faster, "old"), "faster_both_solved")
        self.assertEqual(outcome_vs(tie, "old"), "tie_both_solved")
        self.assertEqual(outcome_vs(slower, "old"), "slower_both_solved")


if __name__ == "__main__":
    unittest.main()
