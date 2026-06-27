import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import launch_residual_dev_multiseed_mining
from launch_residual_dev_multiseed_mining import (
    active_march_processes,
    require_no_active_march_processes,
    require_train_multiseed_ready,
)


class LaunchResidualDevMultiseedMiningTest(unittest.TestCase):
    def write_progress(
        self,
        path: Path,
        *,
        completed_seed_pairs: int = 504,
        positive_instances: int = 16,
        decision: str = "ready_for_formal_multiseed_manifest",
        seeds: str = "1730,1731,1732",
        positive_floor_met: bool = True,
        complete_mining: bool = True,
        raw_artifacts_complete: bool = True,
    ) -> None:
        pd.DataFrame(
            {
                "expected_sample_seeds": [seeds],
                "expected_seed_pairs": [504],
                "completed_seed_pairs": [completed_seed_pairs],
                "raw_complete_seed_pairs": [completed_seed_pairs],
                "positive_instances": [positive_instances],
                "positive_floor_met": [positive_floor_met],
                "complete_mining": [complete_mining],
                "raw_artifacts_complete": [raw_artifacts_complete],
                "decision": [decision],
            }
        ).to_csv(path, index=False)

    def test_require_train_multiseed_ready_accepts_ready_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(progress)

            require_train_multiseed_ready(
                progress,
                expected_sample_seeds=(1730, 1731, 1732),
                min_positive_instances=16,
            )

    def test_require_train_multiseed_ready_rejects_incomplete_seed_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(
                progress,
                completed_seed_pairs=503,
                complete_mining=False,
                raw_artifacts_complete=False,
                decision="continue_mining",
            )

            with self.assertRaisesRegex(ValueError, "not ready"):
                require_train_multiseed_ready(
                    progress,
                    expected_sample_seeds=(1730, 1731, 1732),
                    min_positive_instances=16,
                )

    def test_require_train_multiseed_ready_rejects_wrong_seed_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(progress, seeds="1730,1731")

            with self.assertRaisesRegex(ValueError, "seed set"):
                require_train_multiseed_ready(
                    progress,
                    expected_sample_seeds=(1730, 1731, 1732),
                    min_positive_instances=16,
                )

    def test_require_train_multiseed_ready_rejects_sparse_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            self.write_progress(
                progress,
                positive_instances=8,
                positive_floor_met=False,
                decision="complete_but_sparse",
            )

            with self.assertRaisesRegex(ValueError, "not ready"):
                require_train_multiseed_ready(
                    progress,
                    expected_sample_seeds=(1730, 1731, 1732),
                    min_positive_instances=16,
                )

    def test_require_no_active_march_processes_rejects_active_process(self):
        with mock.patch(
            "launch_residual_dev_multiseed_mining.active_march_processes",
            return_value=["123 run_march_sample_portfolio_multiseed.py --scope expanded"],
        ):
            with self.assertRaisesRegex(RuntimeError, "Refusing to launch"):
                require_no_active_march_processes()

    def test_active_march_processes_parses_ps_output(self):
        results = [
            mock.Mock(
                returncode=0,
                stdout="101 /env/bin/python run_march_sample_portfolio_multiseed.py --scope expanded\n",
                stderr="",
            ),
            mock.Mock(returncode=0, stdout="102 solvers/march_weighted/march_nh x.cnf --cpu-lim=60\n", stderr=""),
            mock.Mock(
                returncode=0,
                stdout="103 /env/bin/python train_residual_contrastive_replay.py --epochs 8\n",
                stderr="",
            ),
            mock.Mock(returncode=1, stdout="", stderr=""),
            mock.Mock(returncode=1, stdout="", stderr=""),
        ]

        with mock.patch("launch_residual_dev_multiseed_mining.subprocess.run", side_effect=results):
            active = active_march_processes()

        self.assertEqual(len(active), 3)
        self.assertTrue(any("run_march_sample_portfolio_multiseed.py" in line for line in active))
        self.assertTrue(any("march_nh" in line for line in active))
        self.assertTrue(any("train_residual_contrastive_replay.py" in line for line in active))

    def test_main_launches_dev_multiseed_command_when_train_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            progress = root / "progress.csv"
            self.write_progress(progress)
            argv = [
                "launch_residual_dev_multiseed_mining.py",
                "--train-progress-csv",
                str(progress),
                "--expected-train-sample-seeds",
                "1730,1731,1732",
                "--input",
                "residual_dev.csv",
                "--source-root",
                "data/root",
                "--checkpoint",
                "model.pt",
                "--out-dir",
                "out",
                "--subset-root",
                "subset",
                "--doc",
                "doc.md",
                "--sample-seeds",
                "1730,1731,1732",
                "--dry-run",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("launch_residual_dev_multiseed_mining.require_no_active_march_processes"),
                mock.patch("launch_residual_dev_multiseed_mining.run_command") as run,
            ):
                launch_residual_dev_multiseed_mining.main()

            command = run.call_args.args[0]
            self.assertFalse(run.call_args.kwargs["detached"])
            self.assertTrue(run.call_args.kwargs["dry_run"])
            self.assertIn("run_march_sample_portfolio_multiseed.py", command)
            self.assertIn("--input", command)
            self.assertIn("residual_dev.csv", command)
            self.assertIn("--sample-seeds", command)
            self.assertIn("1730,1731,1732", command)
            self.assertIn("--artifact-mode", command)
            self.assertIn("instance", command)

    def test_main_rejects_dev_launch_when_train_progress_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            progress = root / "progress.csv"
            self.write_progress(
                progress,
                completed_seed_pairs=4,
                positive_instances=0,
                decision="continue_mining",
                positive_floor_met=False,
                complete_mining=False,
                raw_artifacts_complete=False,
            )
            argv = [
                "launch_residual_dev_multiseed_mining.py",
                "--train-progress-csv",
                str(progress),
                "--input",
                "residual_dev.csv",
                "--source-root",
                "data/root",
                "--checkpoint",
                "model.pt",
                "--out-dir",
                "out",
                "--subset-root",
                "subset",
                "--doc",
                "doc.md",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("launch_residual_dev_multiseed_mining.run_command") as run,
                self.assertRaisesRegex(ValueError, "not ready"),
            ):
                launch_residual_dev_multiseed_mining.main()

            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
