import tempfile
import unittest
from pathlib import Path

import pandas as pd

from summarize_residual_oracle_union import load_oracle, parse_bool, summarize


class ResidualOracleUnionTest(unittest.TestCase):
    def test_parse_bool_strictly_handles_false_string(self):
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool("0"))
        self.assertTrue(parse_bool("true"))

    def test_union_combines_checkpoint_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "a.csv"
            b = root / "b.csv"
            pd.DataFrame(
                {
                    "family": ["3sat", "3sat"],
                    "size": [410, 425],
                    "file_key": ["x.cnf", "y.cnf"],
                    "solved_any": [True, False],
                    "solved_samples": [2, 0],
                    "best_time": [1.0, 60.0],
                }
            ).to_csv(a, index=False)
            pd.DataFrame(
                {
                    "family": ["3sat", "3sat"],
                    "size": [410, 425],
                    "file_key": ["x.cnf", "y.cnf"],
                    "solved_any": ["False", "True"],
                    "solved_samples": [0, 1],
                    "best_time": [60.0, 5.0],
                }
            ).to_csv(b, index=False)

            union, per_tag, _ = summarize([a, b], ["a", "b"])

            self.assertEqual(len(union), 2)
            self.assertEqual(int(union["oracle_solved_any"].sum()), 2)
            self.assertEqual(per_tag.set_index("tag").loc["a", "oracle_solved"], 1)
            self.assertEqual(per_tag.set_index("tag").loc["b", "oracle_solved"], 1)

    def test_load_oracle_rejects_duplicate_keys_within_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.csv"
            pd.DataFrame(
                {
                    "family": ["3sat", "3sat"],
                    "size": [410, 410],
                    "file_key": ["x.cnf", "x.cnf"],
                    "solved_any": [True, False],
                }
            ).to_csv(path, index=False)

            with self.assertRaisesRegex(ValueError, "Duplicate oracle keys"):
                summarize([path], ["dup"])

    def test_load_oracle_normalizes_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oracle.csv"
            pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": ["410"],
                    "file_key": ["x.cnf"],
                    "solved_any": ["False"],
                }
            ).to_csv(path, index=False)

            frame = load_oracle(path, tag="t")

            self.assertEqual(frame.loc[0, "size"], 410)
            self.assertFalse(bool(frame.loc[0, "solved_any"]))
            self.assertEqual(int(frame.loc[0, "solved_samples"]), 0)


if __name__ == "__main__":
    unittest.main()
