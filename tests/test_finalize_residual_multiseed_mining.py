import tempfile
import unittest
import fcntl
from pathlib import Path
from unittest import mock

import pandas as pd

import finalize_residual_multiseed_mining
from finalize_residual_multiseed_mining import (
    active_mining_processes,
    progress_refresh_command,
    require_complete_progress,
    strict_summarize_command,
    work_dir_lock_is_held,
)


class FinalizeResidualMultiseedMiningTest(unittest.TestCase):
    def write_progress(
        self,
        path: Path,
        *,
        decision: str = "ready_for_formal_multiseed_manifest",
        completed_seed_pairs: int = 504,
        raw_complete_seed_pairs: int = 504,
        positive_instances: int = 16,
        positive_floor_met: bool = True,
        complete_mining: bool = True,
        raw_artifacts_complete: bool = True,
        seeds: str = "1730,1731,1732",
    ) -> None:
        pd.DataFrame(
            {
                "expected_sample_seeds": [seeds],
                "expected_seed_pairs": [504],
                "completed_seed_pairs": [completed_seed_pairs],
                "raw_complete_seed_pairs": [raw_complete_seed_pairs],
                "positive_instances": [positive_instances],
                "positive_floor_met": [positive_floor_met],
                "complete_mining": [complete_mining],
                "raw_artifacts_complete": [raw_artifacts_complete],
                "decision": [decision],
            }
        ).to_csv(path, index=False)

    def test_require_complete_progress_accepts_ready_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(progress)

            decision = require_complete_progress(
                progress,
                expected_sample_seeds=(1730, 1731, 1732),
                min_positive_instances=16,
                require_positive_floor=True,
            )

        self.assertEqual(decision, "ready_for_formal_multiseed_manifest")

    def test_require_complete_progress_accepts_sparse_when_floor_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(
                progress,
                decision="complete_but_sparse",
                positive_instances=3,
                positive_floor_met=False,
            )

            decision = require_complete_progress(
                progress,
                expected_sample_seeds=(1730, 1731, 1732),
                min_positive_instances=16,
                require_positive_floor=False,
            )

        self.assertEqual(decision, "complete_but_sparse")

    def test_require_complete_progress_rejects_sparse_when_floor_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(
                progress,
                decision="complete_but_sparse",
                positive_instances=3,
                positive_floor_met=False,
            )

            with self.assertRaisesRegex(ValueError, "positive_floor"):
                require_complete_progress(
                    progress,
                    expected_sample_seeds=(1730, 1731, 1732),
                    min_positive_instances=16,
                    require_positive_floor=True,
                )

    def test_require_complete_progress_rejects_incomplete_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(
                progress,
                completed_seed_pairs=503,
                raw_complete_seed_pairs=503,
                complete_mining=False,
                raw_artifacts_complete=False,
                decision="continue_mining",
            )

            with self.assertRaisesRegex(ValueError, "not ready"):
                require_complete_progress(
                    progress,
                    expected_sample_seeds=(1730, 1731, 1732),
                    min_positive_instances=16,
                    require_positive_floor=False,
                )

    def test_active_mining_processes_parses_ps_output(self):
        results = [
            mock.Mock(
                returncode=0,
                stdout="101 /env/bin/python run_march_sample_portfolio_multiseed.py --scope expanded\n",
                stderr="",
            ),
            mock.Mock(returncode=0, stdout="102 solvers/march_weighted/march_nh x.cnf --cpu-lim=60\n", stderr=""),
        ]

        with mock.patch("finalize_residual_multiseed_mining.subprocess.run", side_effect=results):
            active = active_mining_processes()

        self.assertEqual(len(active), 2)
        self.assertTrue(any("run_march_sample_portfolio_multiseed.py" in line for line in active))
        self.assertTrue(any("march_nh" in line for line in active))

    def test_commands_use_multiseed_summarizer_and_strict_portfolio_summary(self):
        args = finalize_residual_multiseed_mining.parse_args(
            [
                "--split-csv",
                "split.csv",
                "--instances-dir",
                "instances",
                "--progress-csv",
                "progress.csv",
                "--remaining-csv",
                "remaining.csv",
                "--positives-csv",
                "positives.csv",
                "--progress-doc",
                "progress.md",
                "--portfolio-input",
                "split.csv",
                "--source-root",
                "data",
                "--checkpoint",
                "checkpoint.pt",
                "--out-dir",
                "out",
                "--subset-root",
                "subset",
                "--portfolio-doc",
                "portfolio.md",
                "--sample-seeds",
                "1730,1731,1732",
                "--num-samples",
                "16",
            ]
        )

        refresh = progress_refresh_command(args)
        strict = strict_summarize_command(args)

        self.assertIn("summarize_residual_multiseed_mining.py", refresh)
        self.assertIn("--expected-sample-seeds", refresh)
        self.assertIn("1730,1731,1732", refresh)
        self.assertIn("run_march_sample_portfolio_multiseed.py", strict)
        self.assertIn("--summarize-only", strict)
        self.assertNotIn("--allow-partial-summary", strict)

    def test_main_waits_when_active_mining_process_exists(self):
        with mock.patch(
            "finalize_residual_multiseed_mining.active_mining_processes",
            return_value=["123 run_march_sample_portfolio_multiseed.py"],
        ):
            with (
                mock.patch("sys.argv", ["finalize_residual_multiseed_mining.py"]),
                mock.patch("finalize_residual_multiseed_mining.work_dir_lock_is_held", return_value=False),
                mock.patch("finalize_residual_multiseed_mining.run_command") as run,
                mock.patch("builtins.print") as printed,
            ):
                finalize_residual_multiseed_mining.main()

        run.assert_not_called()
        self.assertIn("active_mining_processes", printed.call_args.args[0])

    def test_work_dir_lock_is_held_detects_runner_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            lock = out_dir / ".run_march_sample_portfolio_multiseed.lock"
            with lock.open("w", encoding="utf-8") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertTrue(work_dir_lock_is_held(out_dir))
                fcntl.flock(handle, fcntl.LOCK_UN)

            self.assertFalse(work_dir_lock_is_held(out_dir))

    def test_main_waits_when_work_dir_lock_is_held(self):
        with (
            mock.patch("sys.argv", ["finalize_residual_multiseed_mining.py"]),
            mock.patch("finalize_residual_multiseed_mining.work_dir_lock_is_held", return_value=True),
            mock.patch("finalize_residual_multiseed_mining.run_command") as run,
            mock.patch("builtins.print") as printed,
        ):
            finalize_residual_multiseed_mining.main()

        run.assert_not_called()
        self.assertIn("active_work_dir_lock", printed.call_args.args[0])

    def test_main_runs_strict_summary_when_ready_and_inactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            progress = root / "progress.csv"
            self.write_progress(progress)
            argv = [
                "finalize_residual_multiseed_mining.py",
                "--progress-csv",
                str(progress),
                "--settle-seconds",
                "0",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_multiseed_mining.work_dir_lock_is_held", return_value=False),
                mock.patch("finalize_residual_multiseed_mining.active_mining_processes", return_value=[]),
                mock.patch("finalize_residual_multiseed_mining.run_command") as run,
                mock.patch("finalize_residual_multiseed_mining.wait_for_artifacts_settled", return_value=True),
            ):
                finalize_residual_multiseed_mining.main()

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(2, len(commands))
        self.assertIn("summarize_residual_multiseed_mining.py", commands[0])
        self.assertIn("run_march_sample_portfolio_multiseed.py", commands[1])
        self.assertIn("--summarize-only", commands[1])


if __name__ == "__main__":
    unittest.main()
