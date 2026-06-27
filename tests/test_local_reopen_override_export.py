import tempfile
import unittest
from pathlib import Path

from omegaconf import OmegaConf

from export_local_reopen_override_checkpoint import export_checkpoint


class LocalReopenOverrideExportTest(unittest.TestCase):
    def test_export_copies_checkpoint_and_appends_local_reopen_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir = Path(tmp) / "source"
            output_dir = Path(tmp) / "output"
            source_dir.mkdir()
            (source_dir / "best.pt").write_bytes(b"weights")
            OmegaConf.save(
                OmegaConf.create(
                    {
                        "model": {
                            "event_adapter": {
                                "selector_feature_names": ["warmup_c2000_rho_event_corr"]
                            }
                        }
                    }
                ),
                source_dir / "config.yaml",
            )

            exported = export_checkpoint(
                checkpoint=str(source_dir / "best.pt"),
                output_dir=str(output_dir),
                feature_names=[
                    "warmup_c1000_minus_warmup_c750_decisions",
                    "warmup_c2000_rho_event_corr",
                ],
                ops=[">=", ">="],
                values=[294.0, 0.036501],
            )

            cfg = OmegaConf.load(output_dir / "config.yaml")
            self.assertEqual(exported, output_dir / "best.pt")
            self.assertEqual((output_dir / "best.pt").read_bytes(), b"weights")
            self.assertEqual(
                list(cfg.model.event_adapter.selector_feature_names),
                [
                    "local_reopen_candidate",
                    "warmup_c2000_rho_event_corr",
                    "warmup_c1000_minus_warmup_c750_decisions",
                ],
            )
            self.assertTrue(bool(cfg.model.event_adapter.local_reopen_enabled))
            self.assertEqual(
                list(cfg.model.event_adapter.local_reopen_feature_names),
                [
                    "local_reopen_candidate",
                    "warmup_c1000_minus_warmup_c750_decisions",
                    "warmup_c2000_rho_event_corr",
                ],
            )
            self.assertEqual(list(cfg.model.event_adapter.local_reopen_ops), [">=", ">=", ">="])
            self.assertEqual(list(cfg.model.event_adapter.local_reopen_values), [1.0, 294.0, 0.036501])


if __name__ == "__main__":
    unittest.main()
