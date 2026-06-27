import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import launch_residual_dev_elite_mining
from launch_residual_dev_elite_mining import (
    REQUIRED_TRAIN_AUDIT_CHECKS,
    active_march_processes,
    require_audit_pass,
    require_no_active_march_processes,
    require_progress_ready,
)


class LaunchResidualDevEliteMiningTest(unittest.TestCase):
    def test_require_audit_pass_rejects_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.csv"
            rows = [
                {"check": check, "status": "pass", "detail": "ok"}
                for check in sorted(REQUIRED_TRAIN_AUDIT_CHECKS)
            ]
            rows[0]["status"] = "fail"
            pd.DataFrame(rows).to_csv(audit, index=False)

            with self.assertRaisesRegex(ValueError, "failed"):
                require_audit_pass(audit)

    def test_require_audit_pass_rejects_placeholder_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.csv"
            audit.write_text("check,status,detail\nx,pass,ok\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required checks"):
                require_audit_pass(audit)

    def write_passing_train_audit(self, path: Path) -> None:
        pd.DataFrame(
            {
                "check": sorted(REQUIRED_TRAIN_AUDIT_CHECKS),
                "status": ["pass"] * len(REQUIRED_TRAIN_AUDIT_CHECKS),
                "detail": ["ok"] * len(REQUIRED_TRAIN_AUDIT_CHECKS),
            }
        ).to_csv(path, index=False)

    def test_require_progress_ready_rejects_continue_mining(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [False],
                    "raw_artifacts_complete": [False],
                    "decision": ["continue_mining"],
                }
            ).to_csv(progress, index=False)

            with self.assertRaisesRegex(ValueError, "not ready"):
                require_progress_ready(progress)

    def test_require_no_active_march_processes_rejects_active_process(self):
        with mock.patch(
            "launch_residual_dev_elite_mining.active_march_processes",
            return_value=["123 run_march_sample_portfolio_multiseed.py --scope expanded"],
        ):
            with self.assertRaisesRegex(RuntimeError, "Refusing to launch"):
                require_no_active_march_processes()

    def test_active_march_processes_parses_ps_output(self):
        output = (
            " 100 python idle.py\n"
            " 101 /env/bin/python run_march_sample_portfolio_multiseed.py --scope expanded\n"
            " 102 solvers/march_weighted/march_nh x.cnf --cpu-lim=60\n"
            " 103 /env/bin/python train_residual_elite_replay.py --epochs 8\n"
        )
        result = mock.Mock(returncode=0, stdout=output, stderr="")

        with mock.patch("launch_residual_dev_elite_mining.subprocess.run", return_value=result):
            active = active_march_processes()

        self.assertEqual(len(active), 3)
        self.assertIn("run_march_sample_portfolio_multiseed.py", active[0])
        self.assertIn("march_nh", active[1])
        self.assertIn("train_residual_elite_replay.py", active[2])

    def test_main_checks_train_audit_and_launches_dev_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "train_audit.csv"
            self.write_passing_train_audit(audit)
            argv = [
                "launch_residual_dev_elite_mining.py",
                "--train-manifest-audit",
                str(audit),
                "--train-progress-csv",
                str(root / "train_progress.csv"),
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
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [True],
                    "raw_artifacts_complete": [True],
                    "decision": ["ready_for_formal_elite_manifest"],
                }
            ).to_csv(root / "train_progress.csv", index=False)

            with (
                mock.patch("sys.argv", argv),
                mock.patch("launch_residual_dev_elite_mining.require_no_active_march_processes"),
                mock.patch("launch_residual_dev_elite_mining.run_command") as run,
            ):
                launch_residual_dev_elite_mining.main()

            command = run.call_args.args[0]
            self.assertFalse(run.call_args.kwargs["detached"])
            self.assertIn("run_march_sample_portfolio_multiseed.py", command)
            self.assertIn("--input", command)
            self.assertIn("residual_dev.csv", command)
            self.assertIn("--artifact-mode", command)
            self.assertIn("instance", command)

    def test_main_rejects_dev_launch_when_train_progress_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "train_audit.csv"
            self.write_passing_train_audit(audit)
            progress = root / "train_progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [False],
                    "raw_artifacts_complete": [False],
                    "decision": ["continue_mining"],
                }
            ).to_csv(progress, index=False)
            argv = [
                "launch_residual_dev_elite_mining.py",
                "--train-manifest-audit",
                str(audit),
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
                mock.patch("launch_residual_dev_elite_mining.run_command") as run,
                self.assertRaisesRegex(ValueError, "not ready"),
            ):
                launch_residual_dev_elite_mining.main()

            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
