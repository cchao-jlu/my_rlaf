import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import finalize_residual_elite_replay_pipeline
from finalize_residual_elite_replay_pipeline import (
    REQUIRED_MANIFEST_AUDIT_CHECKS,
    REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS,
    require_audit_pass,
)


class FinalizeResidualEliteReplayPipelineTest(unittest.TestCase):
    def test_require_audit_pass_rejects_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.csv"
            rows = [{"check": check, "status": "pass", "detail": "ok"} for check in sorted(REQUIRED_MANIFEST_AUDIT_CHECKS)]
            rows[0]["status"] = "fail"
            pd.DataFrame(rows).to_csv(audit, index=False)

            with self.assertRaisesRegex(ValueError, "Audit failed"):
                require_audit_pass(audit, REQUIRED_MANIFEST_AUDIT_CHECKS)

    def test_require_audit_pass_rejects_placeholder_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = root / "audit.csv"
            audit.write_text("check,status,detail\nx,pass,ok\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required checks"):
                require_audit_pass(audit, REQUIRED_MANIFEST_AUDIT_CHECKS)

    def write_passing_audit(self, path: Path, checks: set[str]) -> None:
        pd.DataFrame(
            {
                "check": sorted(checks),
                "status": ["pass"] * len(checks),
                "detail": ["ok"] * len(checks),
            }
        ).to_csv(path, index=False)

    def write_common_inputs(self, root: Path) -> dict[str, Path]:
        paths = {}
        for name in ["source.pt", "train.csv", "dev.csv", "train_split.csv", "train_audit.csv", "dev_audit.csv"]:
            path = root / name
            if name.endswith("audit.csv"):
                self.write_passing_audit(path, REQUIRED_MANIFEST_AUDIT_CHECKS)
            else:
                path.write_text("data\n", encoding="utf-8")
            paths[name] = path
        return paths

    def common_argv(self, root: Path, model_dir: Path, training_audit: Path) -> list[str]:
        return [
            "finalize_residual_elite_replay_pipeline.py",
            "--checkpoint",
            str(root / "source.pt"),
            "--train-manifest",
            str(root / "train.csv"),
            "--dev-manifest",
            str(root / "dev.csv"),
            "--train-split-csv",
            str(root / "train_split.csv"),
            "--train-manifest-audit",
            str(root / "train_audit.csv"),
            "--dev-manifest-audit",
            str(root / "dev_audit.csv"),
            "--model-dir",
            str(model_dir),
            "--training-config-audit-csv",
            str(training_audit),
            "--training-config-audit-doc",
            str(root / "training_audit.md"),
        ]

    def test_train_audit_stage_runs_training_and_training_config_audit_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_common_inputs(root)
            model_dir = root / "model"
            model_dir.mkdir()
            training_audit = root / "training_audit.csv"
            argv = self.common_argv(root, model_dir, training_audit)

            def fake_run(command):
                if "train_residual_elite_replay.py" in command:
                    (model_dir / "best.pt").write_text("checkpoint\n", encoding="utf-8")
                    (model_dir / "config.yaml").write_text("elite_replay: {}\n", encoding="utf-8")
                if "audit_residual_elite_replay_manifest.py" in command:
                    self.write_passing_audit(training_audit, REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_elite_replay_pipeline.run_command", side_effect=fake_run) as run,
            ):
                finalize_residual_elite_replay_pipeline.main()

            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn("train_residual_elite_replay.py", commands[0])
            self.assertIn("audit_residual_elite_replay_manifest.py", commands[1])
            self.assertEqual(2, len(commands))

    def test_gate_stage_uses_existing_oracle_and_training_config_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_common_inputs(root)
            oracle = root / "oracle.csv"
            oracle.write_text("data\n", encoding="utf-8")
            model_dir = root / "model"
            model_dir.mkdir()
            (model_dir / "best.pt").write_text("checkpoint\n", encoding="utf-8")
            training_audit = root / "training_audit.csv"
            self.write_passing_audit(training_audit, REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)
            gate_output = root / "gate.md"
            gate_record = root / "gate.json"
            argv = [
                *self.common_argv(root, model_dir, training_audit),
                "--stage",
                "gate",
                "--oracle-summary",
                str(oracle),
                "--gate-output",
                str(gate_output),
                "--gate-record-json",
                str(gate_record),
                "--gate-name",
                "elite_replay_all49",
            ]

            def fake_run(command):
                if "decide_residual_portfolio_gate.py" in command:
                    gate_output.write_text("gate\n", encoding="utf-8")

            with (
                mock.patch("sys.argv", argv),
                mock.patch("finalize_residual_elite_replay_pipeline.run_command", side_effect=fake_run) as run,
            ):
                finalize_residual_elite_replay_pipeline.main()

            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(1, len(commands))
            gate_command = commands[0]
            self.assertIn("decide_residual_portfolio_gate.py", gate_command)
            self.assertIn("--training-config-audit", gate_command)
            self.assertIn(str(training_audit), gate_command)
            self.assertIn(str(model_dir / "best.pt"), gate_command)
            self.assertIn("--record-json", gate_command)
            self.assertIn(str(gate_record), gate_command)

    def test_gate_stage_requires_oracle_artifact_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_common_inputs(root)
            model_dir = root / "model"
            model_dir.mkdir()
            (model_dir / "best.pt").write_text("checkpoint\n", encoding="utf-8")
            training_audit = root / "training_audit.csv"
            self.write_passing_audit(training_audit, REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)
            argv = [
                *self.common_argv(root, model_dir, training_audit),
                "--stage",
                "gate",
            ]

            with mock.patch("sys.argv", argv):
                with self.assertRaisesRegex(ValueError, "Gate stage requires"):
                    finalize_residual_elite_replay_pipeline.main()


if __name__ == "__main__":
    unittest.main()
