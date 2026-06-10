import math
import unittest
from types import SimpleNamespace

import pandas as pd
import torch

from evaluate_guided_solver import add_total_time_columns


def graph(cnf_id: int, gpu_time: float) -> SimpleNamespace:
    return SimpleNamespace(cnf_id=torch.tensor([cnf_id]), gpu_time=gpu_time)


class TimeAccountingTest(unittest.TestCase):
    def test_add_total_time_columns_counts_refinement_solver_and_guidance_time(self):
        final_stats = pd.DataFrame(
            {
                "cnf_id": [0, 1],
                "CPU time": [10.0, 20.0],
                "decisions": [1.0, 2.0],
            }
        )
        final_data = [graph(0, 1.0), graph(1, 2.0)]
        refinement_stats = [
            pd.DataFrame({"cnf_id": [0, 1], "CPU time": [3.0, 4.0]}),
            pd.DataFrame({"cnf_id": [0, 1], "CPU time": [5.0, 6.0]}),
        ]
        refinement_data = [
            [graph(0, 0.1), graph(1, 0.2)],
            [graph(0, 0.3), graph(1, 0.4)],
        ]

        merged = add_total_time_columns(
            final_stats,
            final_data,
            refinement_stats_list=refinement_stats,
            refinement_data_lists=refinement_data,
        ).sort_values("cnf_id")

        row0 = merged.iloc[0]
        row1 = merged.iloc[1]
        self.assertTrue(math.isclose(row0["refinement CPU time"], 8.0))
        self.assertTrue(math.isclose(row0["refinement GPU time"], 0.4))
        self.assertTrue(math.isclose(row0["GPU time"], 1.4))
        self.assertTrue(math.isclose(row0["time"], 19.4))
        self.assertTrue(math.isclose(row1["time"], 32.6))


if __name__ == "__main__":
    unittest.main()
