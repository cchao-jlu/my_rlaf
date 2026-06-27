import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from run_march_sample_portfolio_multiseed import main, summarize, work_dir_lock


def write_minimal_cnf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")


def write_instance_raw(path: Path, file_key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "file": [str(path.with_name(file_key))],
            "Result": ["UNKNOWN"],
            "time": [60.0],
            "sample_id": [0],
            "family": ["3sat"],
            "size": [410],
            "file_key": [file_key],
            "sample_seed": [1729],
            "solver_seed": [1729],
            "num_samples_generated": [16],
            "full_cpu_lim": [60.0],
            "neural_generation_wall_time": [0.01],
            "solved": [False],
            "capped_solver_cpu": [60.0],
        }
    ).to_csv(path, index=False)


class MarchSamplePortfolioSummarizeTest(unittest.TestCase):
    def make_args(self, root: Path, allow_partial: bool) -> list[str]:
        source = root / "source"
        a_cnf = source / "3sat" / "410" / "a.cnf"
        b_cnf = source / "3sat" / "410" / "b.cnf"
        write_minimal_cnf(a_cnf)
        write_minimal_cnf(b_cnf)
        input_csv = root / "input.csv"
        pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "cnf_path": [str(a_cnf), str(b_cnf)],
            }
        ).to_csv(input_csv, index=False)
        out_dir = root / "out"
        write_instance_raw(
            out_dir / "instances" / "size410_a_seed1729_samples16_raw.csv",
            file_key="a.cnf",
        )
        args = [
            "run_march_sample_portfolio_multiseed.py",
            "--scope",
            "expanded",
            "--input",
            str(input_csv),
            "--source-root",
            str(source),
            "--subset-root",
            str(root / "subset"),
            "--out-dir",
            str(out_dir),
            "--doc",
            str(root / "doc.md"),
            "--sample-seeds",
            "1729",
            "--num-samples",
            "16",
            "--artifact-mode",
            "instance",
            "--full-cpu-lim",
            "60",
            "--summarize-only",
        ]
        if allow_partial:
            args.append("--allow-partial-summary")
        return args

    def test_strict_summarize_only_rejects_missing_instance_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.make_args(Path(tmp), allow_partial=False)
            with mock.patch.object(sys, "argv", args):
                with self.assertRaises(FileNotFoundError):
                    main()

    def test_partial_summarize_only_is_explicit_monitoring_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.make_args(root, allow_partial=True)
            with mock.patch.object(sys, "argv", args):
                main()

            self.assertTrue((root / "out" / "raw_samples_all.csv").exists())
            self.assertIn("Partial summary: True.", (root / "doc.md").read_text(encoding="utf-8"))

    def test_summaries_preserve_recorded_checkpoint_hash(self):
        raw = pd.DataFrame(
            {
                "file": ["a.cnf"],
                "Result": ["UNKNOWN"],
                "time": [60.0],
                "sample_id": [0],
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "sample_seed": [1729],
                "solver_seed": [1729],
                "num_samples_generated": [16],
                "full_cpu_lim": [60.0],
                "neural_generation_wall_time": [0.01],
                "source_checkpoint": ["/abs/checkpoint.pt"],
                "source_checkpoint_sha256": ["a" * 64],
            }
        )

        instance_seed, instance_oracle, size_seed, size_oracle = summarize(raw, num_samples=16)

        for frame in [instance_seed, instance_oracle, size_seed, size_oracle]:
            self.assertEqual(frame.iloc[0]["source_checkpoint"], "/abs/checkpoint.pt")
            self.assertEqual(frame.iloc[0]["source_checkpoint_sha256"], "a" * 64)

    def test_work_dir_lock_rejects_concurrent_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            with work_dir_lock(out_dir):
                with self.assertRaisesRegex(RuntimeError, "already using"):
                    with work_dir_lock(out_dir):
                        pass


if __name__ == "__main__":
    unittest.main()
