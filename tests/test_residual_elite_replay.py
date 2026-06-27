import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import pandas as pd
from omegaconf import OmegaConf

from build_residual_elite_replay_manifest import (
    build_manifest,
    enforce_expected_sampling,
    enforce_raw_checkpoint_provenance,
    enforce_raw_completeness,
    enforce_positive_floor,
    instance_keys,
    load_raw_samples,
    load_split_map,
    positive_instance_count,
)
from train_residual_elite_replay import enforce_positive_floor as enforce_training_positive_floor
from train_residual_elite_replay import enforce_full_manifest_training
from train_residual_elite_replay import enforce_manifest_provenance
from train_residual_elite_replay import enforce_manifest_sampling_protocol
from train_residual_elite_replay import file_sha256 as replay_file_sha256
from train_residual_elite_replay import save_training_config


class ResidualEliteReplayManifestTest(unittest.TestCase):
    def test_manifest_keeps_fastest_solved_samples_per_instance(self):
        raw = pd.DataFrame(
            {
                "family": ["3sat"] * 5,
                "size": [410] * 5,
                "file_key": ["a.cnf", "a.cnf", "a.cnf", "b.cnf", "b.cnf"],
                "sample_seed": [1729] * 5,
                "solver_seed": [1729] * 5,
                "num_samples_generated": [16] * 5,
                "sample_id": [0, 1, 2, 0, 1],
                "Result": ["UNKNOWN", "SATISFIABLE", "SATISFIABLE", "UNSATISFIABLE", "UNKNOWN"],
                "CPU time": [60.0, 4.0, 2.0, 5.0, 60.0],
                "file": ["data/a.cnf", "data/a.cnf", "data/a.cnf", "data/b.cnf", "data/b.cnf"],
                "source_raw_csv": ["raw.csv"] * 5,
                "source_raw_sha256": ["0" * 64] * 5,
            }
        )

        manifest = build_manifest(
            raw=raw,
            split_map={
                ("3sat", 410, "a.cnf"): {
                    "split": "residual_train",
                    "cnf_path": "/abs/a.cnf",
                    "row_id": "a",
                }
            },
            checkpoint=None,
            max_per_instance=1,
        )

        self.assertEqual(len(manifest), 2)
        a = manifest[manifest["file_key"].eq("a.cnf")].iloc[0]
        self.assertEqual(int(a["sample_id"]), 2)
        self.assertEqual(a["split"], "residual_train")
        self.assertEqual(a["cnf_path"], "/abs/a.cnf")
        b = manifest[manifest["file_key"].eq("b.cnf")].iloc[0]
        self.assertEqual(str(b["Result"]), "UNSATISFIABLE")
        self.assertEqual(positive_instance_count(manifest), 2)

    def test_positive_floor_rejects_sparse_formal_manifest(self):
        manifest = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
            }
        )

        with self.assertRaisesRegex(ValueError, "too few positive instances"):
            enforce_positive_floor(manifest, min_positive_instances=2)

    def test_positive_floor_can_be_disabled_for_smoke_manifest(self):
        manifest = pd.DataFrame()

        enforce_positive_floor(manifest, min_positive_instances=0)

    def test_training_positive_floor_rejects_sparse_manifest(self):
        manifest = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )

        with self.assertRaisesRegex(ValueError, "train elite replay manifest"):
            enforce_training_positive_floor(manifest, min_positive_instances=2, label="train")

    def test_training_rejects_row_limited_manifest_without_explicit_smoke_flag(self):
        args = Namespace(
            limit_train_rows=2,
            limit_dev_rows=0,
            allow_partial_manifest_training=False,
        )

        with self.assertRaisesRegex(ValueError, "Partial manifest training"):
            enforce_full_manifest_training(args)

    def test_training_allows_row_limit_only_with_explicit_smoke_flag(self):
        args = Namespace(
            limit_train_rows=2,
            limit_dev_rows=0,
            allow_partial_manifest_training=True,
        )

        enforce_full_manifest_training(args)

    def test_training_provenance_rejects_wrong_checkpoint_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_train"],
                    "source_checkpoint_sha256": ["0" * 64],
                }
            )

            with self.assertRaisesRegex(ValueError, "checkpoint hash mismatch"):
                enforce_manifest_provenance(
                    manifest,
                    checkpoint=checkpoint,
                    expected_split="residual_train",
                    label="train",
                )

    def test_training_provenance_rejects_wrong_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_heldout"],
                    "source_checkpoint_sha256": [replay_file_sha256(checkpoint)],
                }
            )

            with self.assertRaisesRegex(ValueError, "split mismatch"):
                enforce_manifest_provenance(
                    manifest,
                    checkpoint=checkpoint,
                    expected_split="residual_train",
                    label="train",
                )

    def test_training_sampling_protocol_rejects_wrong_seed_or_num_samples(self):
        manifest = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "sample_seed": [1730],
                "num_samples_generated": [8],
                "sample_id": [3],
            }
        )

        with self.assertRaisesRegex(ValueError, "sample seed mismatch"):
            enforce_manifest_sampling_protocol(
                manifest,
                expected_sample_seeds=(1729,),
                expected_num_samples=8,
                label="train",
            )

        with self.assertRaisesRegex(ValueError, "num_samples_generated mismatch"):
            enforce_manifest_sampling_protocol(
                manifest,
                expected_sample_seeds=(1730,),
                expected_num_samples=16,
                label="train",
            )

    def test_training_sampling_protocol_checks_raw_sources_not_only_elite_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw.csv"
            raw.write_text(
                "family,size,file_key,sample_seed,solver_seed,num_samples_generated,sample_id,Result,CPU time\n"
                "3sat,410,a.cnf,1729,1729,16,0,SATISFIABLE,1.0\n"
                "3sat,410,a.cnf,1730,1729,16,0,UNKNOWN,60.0\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "sample_seed": [1729],
                    "num_samples_generated": [16],
                    "sample_id": [0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [replay_file_sha256(raw)],
                }
            )

            enforce_manifest_sampling_protocol(
                manifest,
                expected_sample_seeds=(1729, 1730),
                expected_num_samples=16,
                label="train",
            )

            with self.assertRaisesRegex(ValueError, "sample seed mismatch"):
                enforce_manifest_sampling_protocol(
                    manifest,
                    expected_sample_seeds=(1729,),
                    expected_num_samples=16,
                    label="train",
                )

    def test_raw_completeness_guard_rejects_partial_split_coverage(self):
        split = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        raw = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )

        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            enforce_raw_completeness(raw, split, require_raw_complete=True)

    def test_raw_completeness_guard_accepts_exact_split_coverage(self):
        split = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        raw = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat", "3sat"],
                "size": [410, 410, 410, 410],
                "file_key": ["b.cnf", "b.cnf", "a.cnf", "a.cnf"],
                "sample_seed": [1729, 1729, 1729, 1729],
                "num_samples_generated": [2, 2, 2, 2],
                "sample_id": [0, 1, 0, 1],
            }
        )

        enforce_raw_completeness(raw, split, require_raw_complete=True)
        self.assertEqual(len(instance_keys(raw)), 2)

    def test_raw_completeness_guard_rejects_truncated_sample_grid(self):
        split = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )
        raw = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "sample_seed": [1729],
                "num_samples_generated": [2],
                "sample_id": [0],
            }
        )

        with self.assertRaisesRegex(ValueError, "Raw sample grid"):
            enforce_raw_completeness(raw, split, require_raw_complete=True)

    def test_raw_completeness_guard_rejects_duplicate_sample_ids(self):
        split = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
            }
        )
        raw = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "sample_seed": [1729, 1729],
                "num_samples_generated": [2, 2],
                "sample_id": [0, 0],
            }
        )

        with self.assertRaisesRegex(ValueError, "duplicates=1"):
            enforce_raw_completeness(raw, split, require_raw_complete=True)

    def test_raw_completeness_guard_rejects_inconsistent_seed_sets(self):
        split = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
            }
        )
        raw = pd.DataFrame(
            {
                "family": ["3sat", "3sat", "3sat", "3sat", "3sat", "3sat"],
                "size": [410, 410, 410, 410, 410, 410],
                "file_key": ["a.cnf", "a.cnf", "b.cnf", "b.cnf", "b.cnf", "b.cnf"],
                "sample_seed": [1729, 1729, 1729, 1729, 1730, 1730],
                "num_samples_generated": [2, 2, 2, 2, 2, 2],
                "sample_id": [0, 1, 0, 1, 0, 1],
            }
        )

        with self.assertRaisesRegex(ValueError, "inconsistent_sample_seed_sets"):
            enforce_raw_completeness(raw, split, require_raw_complete=True)

    def test_expected_sampling_guard_rejects_wrong_seed_or_num_samples(self):
        raw = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "sample_seed": [1729, 1730],
                "num_samples_generated": [16, 16],
                "sample_id": [0, 0],
            }
        )

        with self.assertRaisesRegex(ValueError, "sample seed set"):
            enforce_expected_sampling(
                raw,
                expected_sample_seeds=(1729,),
                expected_num_samples=16,
            )

        with self.assertRaisesRegex(ValueError, "num_samples_generated"):
            enforce_expected_sampling(
                raw,
                expected_sample_seeds=(1729, 1730),
                expected_num_samples=8,
            )

    def test_raw_checkpoint_provenance_rejects_mismatched_recorded_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            raw = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "sample_seed": [1729],
                    "num_samples_generated": [16],
                    "sample_id": [0],
                    "source_checkpoint_sha256": ["0" * 64],
                }
            )

            with self.assertRaisesRegex(ValueError, "checkpoint hash"):
                enforce_raw_checkpoint_provenance(raw, checkpoint=checkpoint)

    def test_load_raw_samples_records_source_hash_and_split_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw.csv"
            raw_path.write_text(
                "family,size,file_key,sample_seed,solver_seed,num_samples_generated,sample_id,Result,CPU time\n"
                "3sat,410,a.cnf,1729,1729,16,0,SATISFIABLE,1.0\n",
                encoding="utf-8",
            )
            split_path = root / "split.csv"
            split_path.write_text(
                "family,size,file_key,split,row_id,cnf_path\n"
                "3sat,410,a.cnf,residual_train,3sat:410:a.cnf,/abs/a.cnf\n",
                encoding="utf-8",
            )

            raw = load_raw_samples([raw_path])
            split_map = load_split_map(split_path)

        self.assertIn("source_raw_sha256", raw.columns)
        self.assertEqual(split_map[("3sat", 410, "a.cnf")]["cnf_path"], "/abs/a.cnf")

    def test_training_config_records_manifest_hashes_and_positive_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            train_manifest_path = root / "train.csv"
            dev_manifest_path = root / "dev.csv"
            train_manifest_path.write_text("family,size,file_key\n3sat,410,a.cnf\n3sat,410,b.cnf\n", encoding="utf-8")
            dev_manifest_path.write_text("family,size,file_key\n3sat,425,c.cnf\n", encoding="utf-8")
            args = Namespace(
                checkpoint=checkpoint,
                train_manifest=train_manifest_path,
                dev_manifest=dev_manifest_path,
                epochs=8,
                batch_size=4,
                lr=5e-6,
                weight_decay=0.0,
                kl_penalty=0.05,
                scale_sigma=0.25,
                seed=1741,
                min_train_positive_instances=2,
                min_dev_positive_instances=1,
                expected_train_split="residual_train",
                expected_dev_split="residual_dev",
                expected_train_sample_seeds="1729",
                expected_dev_sample_seeds="1729",
                expected_train_num_samples=16,
                expected_dev_num_samples=16,
                limit_train_rows=0,
                limit_dev_rows=0,
                allow_partial_manifest_training=False,
            )
            train_manifest = pd.DataFrame(
                {
                    "family": ["3sat", "3sat", "3sat"],
                    "size": [410, 410, 410],
                    "file_key": ["a.cnf", "b.cnf", "b.cnf"],
                }
            )
            dev_manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [425],
                    "file_key": ["c.cnf"],
                }
            )

            save_training_config(
                args,
                model_cfg=OmegaConf.create({"scale_sigma": 0.25}),
                model_dir=root,
                train_manifest=train_manifest,
                dev_manifest=dev_manifest,
            )
            cfg = OmegaConf.load(root / "config.yaml")
            train_manifest_sha256 = replay_file_sha256(train_manifest_path)
            dev_manifest_sha256 = replay_file_sha256(dev_manifest_path)
            checkpoint_sha256 = replay_file_sha256(checkpoint)

        replay_cfg = cfg.elite_replay
        self.assertEqual(replay_cfg.train_manifest_sha256, train_manifest_sha256)
        self.assertEqual(replay_cfg.dev_manifest_sha256, dev_manifest_sha256)
        self.assertEqual(replay_cfg.source_checkpoint_sha256, checkpoint_sha256)
        self.assertEqual(int(replay_cfg.train_elite_rows), 3)
        self.assertEqual(int(replay_cfg.train_positive_instances), 2)
        self.assertEqual(int(replay_cfg.dev_elite_rows), 1)
        self.assertEqual(int(replay_cfg.dev_positive_instances), 1)
        self.assertEqual(int(replay_cfg.min_train_positive_instances), 2)
        self.assertEqual(int(replay_cfg.min_dev_positive_instances), 1)
        self.assertEqual(str(replay_cfg.expected_train_split), "residual_train")
        self.assertEqual(str(replay_cfg.expected_dev_split), "residual_dev")
        self.assertEqual(str(replay_cfg.expected_train_sample_seeds), "1729")
        self.assertEqual(str(replay_cfg.expected_dev_sample_seeds), "1729")
        self.assertEqual(int(replay_cfg.expected_train_num_samples), 16)
        self.assertEqual(int(replay_cfg.expected_dev_num_samples), 16)
        self.assertEqual(bool(replay_cfg.allow_partial_manifest_training), False)


if __name__ == "__main__":
    unittest.main()
