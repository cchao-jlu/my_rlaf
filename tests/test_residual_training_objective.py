import unittest

import pandas as pd
import torch
from omegaconf import OmegaConf
from torch_geometric.data import HeteroData

from train_rlaf import add_advantage_weights, add_composite_target, add_sample_diversity_target


def _graph(cnf_id: int, var_params: torch.Tensor) -> HeteroData:
    data = HeteroData()
    data.cnf_id = torch.tensor(cnf_id)
    data["var"].var_params = var_params
    return data


class ResidualTrainingObjectiveTest(unittest.TestCase):
    def test_diversity_cost_penalizes_near_duplicate_unsolved_samples(self):
        cfg = OmegaConf.create(
            {
                "training": {
                    "target_stat": "composite_diverse",
                    "composite_diversity_weight": 1.0,
                    "composite_diversity_unsolved_only": True,
                }
            }
        )
        stats = pd.DataFrame(
            {
                "cnf_id": [0, 0, 0],
                "sample_id": [0, 1, 2],
                "Result": ["UNKNOWN", "UNKNOWN", "UNKNOWN"],
                "composite": [5.0, 5.0, 5.0],
            }
        )
        var_params = torch.tensor(
            [
                [[1.0, 1.0], [1.0, 1.0], [0.0, 2.0]],
                [[1.0, 1.0], [1.0, 1.0], [0.0, 2.0]],
            ],
            dtype=torch.float32,
        )

        out = add_sample_diversity_target(stats, [_graph(0, var_params)], cfg)

        self.assertGreater(
            out.loc[0, "sample_similarity_cost"],
            out.loc[2, "sample_similarity_cost"],
        )
        self.assertGreater(out.loc[0, "composite_diverse"], out.loc[2, "composite_diverse"])

    def test_unsolved_only_diversity_does_not_penalize_solved_sample(self):
        cfg = OmegaConf.create(
            {
                "training": {
                    "target_stat": "composite_diverse",
                    "composite_diversity_weight": 1.0,
                    "composite_diversity_unsolved_only": True,
                }
            }
        )
        stats = pd.DataFrame(
            {
                "cnf_id": [0, 0],
                "sample_id": [0, 1],
                "Result": ["SATISFIABLE", "UNKNOWN"],
                "composite": [1.0, 5.0],
            }
        )
        var_params = torch.tensor(
            [
                [[1.0, 1.0], [1.0, 1.0]],
                [[1.0, 1.0], [1.0, 1.0]],
            ],
            dtype=torch.float32,
        )

        out = add_sample_diversity_target(stats, [_graph(0, var_params)], cfg)

        self.assertAlmostEqual(out.loc[0, "composite_diverse"], 1.0)
        self.assertGreater(out.loc[1, "composite_diverse"], 5.0)

    def test_progress_target_rewards_unsolved_search_progress(self):
        cfg = OmegaConf.create(
            {
                "training": {
                    "target_stat": "composite_progress",
                    "composite_unsolved_penalty": 5.0,
                    "composite_cpu_weight": 0.0,
                    "composite_deadends_weight": 0.0,
                    "composite_conflicts_weight": 0.0,
                    "composite_decisions_weight": 0.0,
                    "composite_progress_deadends_weight": 1.0,
                    "composite_progress_decisions_weight": 0.0,
                    "composite_progress_conflicts_weight": 0.0,
                    "composite_progress_unsolved_only": True,
                }
            }
        )
        stats = pd.DataFrame(
            {
                "Result": ["UNKNOWN", "UNKNOWN", "SATISFIABLE"],
                "dead_ends_in_main": [1.0, 100.0, 100.0],
                "decisions": [0.0, 0.0, 0.0],
            }
        )

        out = add_composite_target(stats, cfg)

        self.assertLess(out.loc[1, "composite_progress"], out.loc[0, "composite_progress"])
        self.assertAlmostEqual(out.loc[2, "composite_progress_reward"], 0.0)

    def test_progress_diverse_adds_diversity_to_progress_base(self):
        cfg = OmegaConf.create(
            {
                "training": {
                    "target_stat": "composite_progress_diverse",
                    "composite_unsolved_penalty": 5.0,
                    "composite_cpu_weight": 0.0,
                    "composite_deadends_weight": 0.0,
                    "composite_conflicts_weight": 0.0,
                    "composite_decisions_weight": 0.0,
                    "composite_progress_deadends_weight": 0.0,
                    "composite_progress_decisions_weight": 0.0,
                    "composite_progress_conflicts_weight": 0.0,
                    "composite_progress_unsolved_only": True,
                    "composite_diversity_weight": 1.0,
                    "composite_diversity_unsolved_only": True,
                }
            }
        )
        stats = pd.DataFrame(
            {
                "cnf_id": [0, 0],
                "sample_id": [0, 1],
                "Result": ["UNKNOWN", "UNKNOWN"],
                "dead_ends_in_main": [0.0, 0.0],
                "decisions": [0.0, 0.0],
            }
        )
        var_params = torch.tensor(
            [
                [[1.0, 1.0], [1.0, 1.0]],
                [[1.0, 1.0], [1.0, 1.0]],
            ],
            dtype=torch.float32,
        )

        out = add_composite_target(stats, cfg)
        out = add_sample_diversity_target(out, [_graph(0, var_params)], cfg)

        self.assertIn("composite_progress", out.columns)
        self.assertIn("composite_progress_diverse", out.columns)
        self.assertGreater(out.loc[0, "composite_progress_diverse"], out.loc[0, "composite_progress"])

    def test_advantage_size_weights_scale_advantage(self):
        cfg = OmegaConf.create(
            {
                "training": {
                    "advantage_size_weights": {"410": 1.0, "440": 2.0},
                    "advantage_default_weight": 1.0,
                    "advantage_min_weight": 0.5,
                    "advantage_max_weight": 2.0,
                }
            }
        )
        stats = pd.DataFrame(
            {
                "size": [410, 440],
                "advantage": [1.0, -1.0],
            }
        )

        out = add_advantage_weights(stats, cfg)

        self.assertAlmostEqual(out.loc[0, "advantage"], 1.0)
        self.assertAlmostEqual(out.loc[1, "advantage"], -2.0)
        self.assertAlmostEqual(out.loc[1, "advantage_weight"], 2.0)


if __name__ == "__main__":
    unittest.main()
