import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from finalize_residual_elite_manifest import ROOT, parse_bool_cell, require_ready, run_command
import finalize_residual_elite_manifest


class FinalizeResidualEliteManifestTest(unittest.TestCase):
    def test_require_ready_accepts_complete_positive_progress(self):
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

            require_ready(progress)

    def test_require_ready_rejects_positive_but_incomplete_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [False],
                    "raw_artifacts_complete": [True],
                    "decision": ["continue_mining"],
                }
            ).to_csv(progress, index=False)

            with self.assertRaisesRegex(ValueError, "not ready"):
                require_ready(progress)

    def test_require_ready_rejects_incomplete_raw_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            pd.DataFrame(
                {
                    "positive_floor_met": [True],
                    "complete_mining": [True],
                    "raw_artifacts_complete": [False],
                    "decision": ["ready_for_formal_elite_manifest"],
                }
            ).to_csv(progress, index=False)

            with self.assertRaisesRegex(ValueError, "raw_artifacts_complete"):
                require_ready(progress)

    def test_require_ready_rejects_string_false_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.csv"
            progress.write_text(
                "\n".join(
                    [
                        "positive_floor_met,complete_mining,raw_artifacts_complete,decision",
                        "True,False,True,ready_for_formal_elite_manifest",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "complete_mining"):
                require_ready(progress)

    def test_parse_bool_cell_rejects_ambiguous_values(self):
        with self.assertRaisesRegex(ValueError, "Invalid boolean"):
            parse_bool_cell("truthy", "flag")

    def test_run_command_uses_repo_cwd_and_pythonpath(self):
        with mock.patch("finalize_residual_elite_manifest.subprocess.run") as run:
            run_command(["python", "script.py"])

        _, kwargs = run.call_args
        self.assertEqual(kwargs["cwd"], ROOT)
        self.assertEqual(kwargs["env"]["PYTHONPATH"].split(":")[0], str(ROOT))
        self.assertEqual(kwargs["check"], True)

    def test_main_passes_expected_sampling_protocol_to_manifest_and_audit(self):
        argv = [
            "finalize_residual_elite_manifest.py",
            "--split-csv",
            "split.csv",
            "--instances-dir",
            "instances",
            "--min-positive-instances",
            "8",
            "--progress-csv",
            "progress.csv",
            "--remaining-csv",
            "remaining.csv",
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
            "1729,1730",
            "--num-samples",
            "16",
            "--manifest-csv",
            "manifest.csv",
            "--manifest-doc",
            "manifest.md",
            "--audit-csv",
            "audit.csv",
            "--audit-doc",
            "audit.md",
            "--expected-split",
            "residual_train",
        ]

        with (
            mock.patch("sys.argv", argv),
            mock.patch("finalize_residual_elite_manifest.run_command") as run,
            mock.patch("finalize_residual_elite_manifest.require_ready"),
            mock.patch("finalize_residual_elite_manifest.pd.read_csv", return_value=pd.DataFrame({"status": ["pass"]})),
        ):
            finalize_residual_elite_manifest.main()

        commands = [call.args[0] for call in run.call_args_list]
        build_command = next(command for command in commands if "build_residual_elite_replay_manifest.py" in command)
        audit_command = next(command for command in commands if "audit_residual_elite_replay_manifest.py" in command)
        self.assertIn("--expected-sample-seeds", build_command)
        self.assertIn("1729,1730", build_command)
        self.assertIn("--expected-num-samples", build_command)
        self.assertIn("16", build_command)
        self.assertIn("--expected-sample-seeds", audit_command)
        self.assertIn("1729,1730", audit_command)
        self.assertIn("--expected-num-samples", audit_command)
        self.assertIn("16", audit_command)


if __name__ == "__main__":
    unittest.main()
