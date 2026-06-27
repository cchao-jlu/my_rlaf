import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import finalize_residual_train_when_ready
from finalize_residual_train_when_ready import (
    active_mining_processes,
    artifact_fingerprint,
    finalizer_command,
    progress_ready,
    progress_refresh_command,
    wait_for_artifacts_settled,
)


class FinalizeResidualTrainWhenReadyTest(unittest.TestCase):
    def test_progress_ready_requires_complete_raw_and_ready_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [True],
                    "raw_artifacts_complete": [True],
                    "decision": ["ready_for_formal_elite_manifest"],
                }
            ).to_csv(path, index=False)

            self.assertTrue(progress_ready(path))

    def test_progress_ready_rejects_continue_mining(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [False],
                    "raw_artifacts_complete": [True],
                    "decision": ["continue_mining"],
                }
            ).to_csv(path, index=False)

            self.assertFalse(progress_ready(path))

    def test_main_waits_when_active_mining_process_exists(self):
        with mock.patch(
            "finalize_residual_train_when_ready.active_mining_processes",
            return_value=["123 run_march_sample_portfolio_multiseed.py"],
        ):
            with mock.patch("sys.argv", ["finalize_residual_train_when_ready.py"]):
                with mock.patch("finalize_residual_train_when_ready.run_command") as run:
                    finalize_residual_train_when_ready.main()

        run.assert_not_called()

    def test_active_mining_processes_parses_ps_output(self):
        output = (
            " 100 python idle.py\n"
            " 101 /env/bin/python run_march_sample_portfolio_multiseed.py --scope expanded\n"
            " 102 solvers/march_weighted/march_nh x.cnf --cpu-lim=60\n"
        )
        result = mock.Mock(returncode=0, stdout=output, stderr="")

        with mock.patch("finalize_residual_train_when_ready.subprocess.run", return_value=result):
            active = active_mining_processes()

        self.assertEqual(len(active), 2)
        self.assertIn("run_march_sample_portfolio_multiseed.py", active[0])
        self.assertIn("march_nh", active[1])

    def test_main_runs_finalizer_when_ready_and_inactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [True],
                    "raw_artifacts_complete": [True],
                    "decision": ["ready_for_formal_elite_manifest"],
                }
            ).to_csv(progress, index=False)
            argv = [
                "finalize_residual_train_when_ready.py",
                "--progress-csv",
                str(progress),
                "--split-csv",
                "split.csv",
                "--instances-dir",
                "instances",
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
                "--manifest-csv",
                "manifest.csv",
                "--manifest-doc",
                "manifest.md",
                "--audit-csv",
                "audit.csv",
                "--audit-doc",
                "audit.md",
                "--settle-seconds",
                "0",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_train_when_ready.active_mining_processes", return_value=[]),
                mock.patch("finalize_residual_train_when_ready.run_command") as run,
            ):
                finalize_residual_train_when_ready.main()

        command = run.call_args.args[0]
        self.assertIn("finalize_residual_elite_manifest.py", command)
        self.assertIn("--expected-split", command)
        self.assertIn("residual_train", command)

    def test_main_refreshes_then_waits_when_progress_not_ready(self):
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
            argv = [
                "finalize_residual_train_when_ready.py",
                "--progress-csv",
                str(progress),
                "--dry-run",
                "--settle-seconds",
                "0",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_train_when_ready.active_mining_processes", return_value=[]),
                mock.patch("finalize_residual_train_when_ready.run_command") as run,
                mock.patch("builtins.print") as print_mock,
            ):
                finalize_residual_train_when_ready.main()

        printed = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(1, len(commands))
        self.assertIn("summarize_residual_elite_mining.py", commands[0])
        self.assertIn("status=wait progress_not_ready", printed)
        self.assertIn("decision=continue_mining", printed)
        self.assertNotIn("finalize_residual_elite_manifest.py", printed)

    def test_artifact_fingerprint_tracks_instance_and_global_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instances = root / "instances"
            out_dir = root / "out"
            instances.mkdir()
            out_dir.mkdir()
            (instances / "x_raw.csv").write_text("raw\n", encoding="utf-8")
            (instances / "x_summary.csv").write_text("summary\n", encoding="utf-8")
            (out_dir / "raw_samples_all.csv").write_text("all\n", encoding="utf-8")

            before = artifact_fingerprint(instances, out_dir)
            (instances / "x_summary.csv").write_text("summary2\n", encoding="utf-8")
            after = artifact_fingerprint(instances, out_dir)

        self.assertNotEqual(before, after)

    def test_wait_for_artifacts_settled_detects_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            instances = root / "instances"
            out_dir = root / "out"
            instances.mkdir()
            out_dir.mkdir()
            (instances / "x_summary.csv").write_text("summary\n", encoding="utf-8")

            calls = [((("x", 1, 1),)), ((("x", 2, 1),))]
            with (
                mock.patch("finalize_residual_train_when_ready.artifact_fingerprint", side_effect=calls),
                mock.patch("finalize_residual_train_when_ready.time.sleep"),
            ):
                settled = wait_for_artifacts_settled(instances, out_dir, settle_seconds=1)

        self.assertFalse(settled)

    def test_main_waits_when_artifacts_are_not_settled(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [True],
                    "raw_artifacts_complete": [True],
                    "decision": ["ready_for_formal_elite_manifest"],
                }
            ).to_csv(progress, index=False)
            argv = [
                "finalize_residual_train_when_ready.py",
                "--progress-csv",
                str(progress),
                "--split-csv",
                "split.csv",
                "--instances-dir",
                "instances",
                "--out-dir",
                "out",
                "--portfolio-input",
                "split.csv",
                "--source-root",
                "data",
                "--checkpoint",
                "checkpoint.pt",
                "--subset-root",
                "subset",
                "--portfolio-doc",
                "portfolio.md",
                "--manifest-csv",
                "manifest.csv",
                "--manifest-doc",
                "manifest.md",
                "--audit-csv",
                "audit.csv",
                "--audit-doc",
                "audit.md",
            ]

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_train_when_ready.active_mining_processes", return_value=[]),
                mock.patch("finalize_residual_train_when_ready.run_command") as run,
                mock.patch("finalize_residual_train_when_ready.wait_for_artifacts_settled", return_value=False),
                mock.patch("builtins.print") as print_mock,
            ):
                finalize_residual_train_when_ready.main()

        commands = [call.args[0] for call in run.call_args_list]
        printed = "\n".join(str(call.args[0]) for call in print_mock.call_args_list)
        self.assertEqual(1, len(commands))
        self.assertIn("summarize_residual_elite_mining.py", commands[0])
        self.assertIn("status=wait artifacts_still_changing", printed)

    def test_progress_refresh_command_contains_summarizer_only(self):
        args = finalize_residual_train_when_ready.parse_args(
            [
                "--split-csv",
                "split.csv",
                "--instances-dir",
                "instances",
                "--progress-csv",
                "progress.csv",
                "--remaining-csv",
                "remaining.csv",
                "--progress-doc",
                "progress.md",
                "--min-positive-instances",
                "8",
            ]
        )

        command = progress_refresh_command(args)

        self.assertIn("summarize_residual_elite_mining.py", command)
        self.assertNotIn("run_march_sample_portfolio_multiseed.py", command)
        self.assertNotIn("finalize_residual_elite_manifest.py", command)

    def test_finalizer_command_contains_sampling_protocol(self):
        args = finalize_residual_train_when_ready.parse_args(
            [
                "--sample-seeds",
                "1729,1730",
                "--num-samples",
                "16",
            ]
        )

        command = finalizer_command(args)

        self.assertIn("--sample-seeds", command)
        self.assertIn("1729,1730", command)
        self.assertIn("--num-samples", command)
        self.assertIn("16", command)


if __name__ == "__main__":
    unittest.main()
