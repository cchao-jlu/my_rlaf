import unittest

import pandas as pd

from analyze_new_closed_old_on_local_gate import evaluate_rule, find_candidate_rules


class NewClosedOldOnLocalGateTest(unittest.TestCase):
    def test_rule_metrics_prioritize_opening_local_positives_without_negatives(self):
        frame = pd.DataFrame(
            {
                "file_key": ["p1.cnf", "p2.cnf", "n1.cnf", "z1.cnf"],
                "counterfactual_class": ["positive", "positive", "negative", "neutral"],
                "adapter_minus_base_time": [-10.0, -5.0, 3.0, 0.2],
                "score": [4.0, 3.0, 1.0, 3.5],
            }
        )

        metrics = evaluate_rule(frame, "score >= 3", frame["score"] >= 3.0)

        self.assertEqual(metrics["opened_positive"], 2)
        self.assertEqual(metrics["opened_negative"], 0)
        self.assertEqual(metrics["opened_neutral"], 1)
        self.assertAlmostEqual(metrics["net_gain_seconds"], 14.8)

    def test_candidate_rule_search_finds_simple_separating_threshold(self):
        frame = pd.DataFrame(
            {
                "file_key": ["p1.cnf", "p2.cnf", "n1.cnf", "n2.cnf", "z1.cnf", "z2.cnf"],
                "counterfactual_class": ["positive", "positive", "negative", "negative", "neutral", "neutral"],
                "adapter_minus_base_time": [-10.0, -5.0, 3.0, 2.0, -0.1, -20.0],
                "decision_drift": [4.0, 3.5, 1.0, 1.5, 3.2, 4.5],
                "corr": [0.2, 0.1, -0.1, -0.2, 0.0, -0.5],
            }
        )

        rules = find_candidate_rules(
            frame,
            feature_names=["decision_drift", "corr"],
            min_opened_positive=2,
            max_opened_negative=0,
            max_terms=1,
        )

        self.assertFalse(rules.empty)
        self.assertEqual(int(rules.iloc[0]["opened_positive"]), 2)
        self.assertEqual(int(rules.iloc[0]["opened_negative"]), 0)
        self.assertLessEqual(int(rules.iloc[0]["opened_neutral"]), 1)


if __name__ == "__main__":
    unittest.main()
