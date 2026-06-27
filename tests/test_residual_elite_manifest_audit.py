import tempfile
import unittest
from pathlib import Path

import pandas as pd
from omegaconf import OmegaConf

from audit_residual_elite_replay_manifest import audit_manifest, audit_training_config, file_sha256


class ResidualEliteManifestAuditTest(unittest.TestCase):
    def test_audit_accepts_manifest_with_matching_split_raw_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            cnf = root / "a.cnf"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
            raw = root / "raw.csv"
            raw_rows = [
                {
                    "family": "3sat",
                    "size": 410,
                    "file_key": "a.cnf",
                    "sample_seed": 1729,
                    "solver_seed": 1729,
                    "num_samples_generated": 16,
                    "sample_id": sample_id,
                    "Result": "SATISFIABLE" if sample_id == 3 else "UNKNOWN",
                    "CPU time": 1.0 if sample_id == 3 else 60.0,
                }
                for sample_id in range(16)
            ]
            pd.DataFrame(raw_rows).to_csv(raw, index=False)
            split = root / "split.csv"
            split.write_text(
                f"family,size,file_key,split,row_id,cnf_path\n"
                f"3sat,410,a.cnf,residual_train,3sat:410:a.cnf,{cnf}\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_train"],
                    "row_id": ["3sat:410:a.cnf"],
                    "cnf_path": [str(cnf)],
                    "sample_seed": [1729],
                    "solver_seed": [1729],
                    "num_samples_generated": [16],
                    "sample_id": [3],
                    "elite_rank_in_instance": [1],
                    "Result": ["SATISFIABLE"],
                    "CPU time": [1.0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [file_sha256(raw)],
                    "source_checkpoint": [str(checkpoint.resolve())],
                    "source_checkpoint_sha256": [file_sha256(checkpoint)],
                }
            )
            manifest_path = root / "manifest.csv"
            manifest.to_csv(manifest_path, index=False)

            rows = audit_manifest(
                manifest_path=manifest_path,
                split_csv=split,
                checkpoint=checkpoint,
                expected_split="residual_train",
                min_positive_instances=1,
                max_per_instance=4,
                expected_sample_seeds=(1729,),
                expected_num_samples=16,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertTrue(all(row["status"] == "pass" for row in rows))
        self.assertEqual(by_name["manifest_rows_match_solved_raw_samples"], "pass")
        self.assertEqual(by_name["manifest_raw_sources_sample_seeds_match_expected"], "pass")
        self.assertEqual(by_name["manifest_raw_sources_num_samples_match_expected"], "pass")

    def test_audit_rejects_wrong_sampling_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            cnf = root / "a.cnf"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
            raw = root / "raw.csv"
            pd.DataFrame(
                [
                    {
                        "family": "3sat",
                        "size": 410,
                        "file_key": "a.cnf",
                        "sample_seed": 1730,
                        "solver_seed": 1729,
                        "num_samples_generated": 8,
                        "sample_id": sample_id,
                        "Result": "SATISFIABLE" if sample_id == 3 else "UNKNOWN",
                        "CPU time": 1.0 if sample_id == 3 else 60.0,
                    }
                    for sample_id in range(8)
                ]
            ).to_csv(raw, index=False)
            split = root / "split.csv"
            split.write_text(
                f"family,size,file_key,split,row_id,cnf_path\n"
                f"3sat,410,a.cnf,residual_train,3sat:410:a.cnf,{cnf}\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_train"],
                    "row_id": ["3sat:410:a.cnf"],
                    "cnf_path": [str(cnf)],
                    "sample_seed": [1730],
                    "solver_seed": [1729],
                    "num_samples_generated": [8],
                    "sample_id": [3],
                    "elite_rank_in_instance": [1],
                    "Result": ["SATISFIABLE"],
                    "CPU time": [1.0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [file_sha256(raw)],
                    "source_checkpoint": [str(checkpoint.resolve())],
                    "source_checkpoint_sha256": [file_sha256(checkpoint)],
                }
            )
            manifest_path = root / "manifest.csv"
            manifest.to_csv(manifest_path, index=False)

            rows = audit_manifest(
                manifest_path=manifest_path,
                split_csv=split,
                checkpoint=checkpoint,
                expected_split="residual_train",
                min_positive_instances=1,
                max_per_instance=4,
                expected_sample_seeds=(1729,),
                expected_num_samples=16,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["manifest_raw_sources_sample_seeds_match_expected"], "fail")
        self.assertEqual(by_name["manifest_raw_sources_num_samples_match_expected"], "fail")

    def test_audit_rejects_raw_checkpoint_hash_mismatch_when_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            cnf = root / "a.cnf"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
            raw = root / "raw.csv"
            pd.DataFrame(
                [
                    {
                        "family": "3sat",
                        "size": 410,
                        "file_key": "a.cnf",
                        "sample_seed": 1729,
                        "solver_seed": 1729,
                        "num_samples_generated": 16,
                        "sample_id": sample_id,
                        "Result": "SATISFIABLE" if sample_id == 3 else "UNKNOWN",
                        "CPU time": 1.0 if sample_id == 3 else 60.0,
                        "source_checkpoint_sha256": "0" * 64,
                    }
                    for sample_id in range(16)
                ]
            ).to_csv(raw, index=False)
            split = root / "split.csv"
            split.write_text(
                f"family,size,file_key,split,row_id,cnf_path\n"
                f"3sat,410,a.cnf,residual_train,3sat:410:a.cnf,{cnf}\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_train"],
                    "row_id": ["3sat:410:a.cnf"],
                    "cnf_path": [str(cnf)],
                    "sample_seed": [1729],
                    "solver_seed": [1729],
                    "num_samples_generated": [16],
                    "sample_id": [3],
                    "elite_rank_in_instance": [1],
                    "Result": ["SATISFIABLE"],
                    "CPU time": [1.0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [file_sha256(raw)],
                    "source_checkpoint": [str(checkpoint.resolve())],
                    "source_checkpoint_sha256": [file_sha256(checkpoint)],
                }
            )
            manifest_path = root / "manifest.csv"
            manifest.to_csv(manifest_path, index=False)

            rows = audit_manifest(
                manifest_path=manifest_path,
                split_csv=split,
                checkpoint=checkpoint,
                expected_split="residual_train",
                min_positive_instances=1,
                max_per_instance=4,
                expected_sample_seeds=(1729,),
                expected_num_samples=16,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["manifest_raw_sources_checkpoint_hash_matches_when_recorded"], "fail")

    def test_audit_rejects_wrong_split_and_sparse_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            cnf = root / "a.cnf"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
            raw = root / "raw.csv"
            raw_rows = [
                {
                    "family": "3sat",
                    "size": 410,
                    "file_key": "a.cnf",
                    "sample_seed": 1729,
                    "solver_seed": 1729,
                    "num_samples_generated": 16,
                    "sample_id": sample_id,
                    "Result": "SATISFIABLE" if sample_id == 3 else "UNKNOWN",
                    "CPU time": 1.0 if sample_id == 3 else 60.0,
                }
                for sample_id in range(16)
            ]
            pd.DataFrame(raw_rows).to_csv(raw, index=False)
            split = root / "split.csv"
            split.write_text(
                f"family,size,file_key,split,row_id,cnf_path\n"
                f"3sat,410,a.cnf,residual_heldout,3sat:410:a.cnf,{cnf}\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_heldout"],
                    "row_id": ["3sat:410:a.cnf"],
                    "cnf_path": [str(cnf)],
                    "sample_seed": [1729],
                    "solver_seed": [1729],
                    "num_samples_generated": [16],
                    "sample_id": [3],
                    "elite_rank_in_instance": [1],
                    "Result": ["SATISFIABLE"],
                    "CPU time": [1.0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [file_sha256(raw)],
                    "source_checkpoint": [str(checkpoint.resolve())],
                    "source_checkpoint_sha256": [file_sha256(checkpoint)],
                }
            )
            manifest_path = root / "manifest.csv"
            manifest.to_csv(manifest_path, index=False)

            rows = audit_manifest(
                manifest_path=manifest_path,
                split_csv=split,
                checkpoint=checkpoint,
                expected_split="residual_train",
                min_positive_instances=2,
                max_per_instance=4,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["manifest_positive_instances_meet_floor"], "fail")
        self.assertEqual(by_name["manifest_split_matches_expected"], "fail")
        self.assertEqual(by_name["split_csv_matches_expected_split"], "fail")

    def test_audit_rejects_incomplete_raw_sample_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            cnf = root / "a.cnf"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="utf-8")
            raw = root / "raw.csv"
            raw.write_text(
                "family,size,file_key,sample_seed,solver_seed,num_samples_generated,sample_id,Result,CPU time\n"
                "3sat,410,a.cnf,1729,1729,2,0,SATISFIABLE,1.0\n",
                encoding="utf-8",
            )
            split = root / "split.csv"
            split.write_text(
                f"family,size,file_key,split,row_id,cnf_path\n"
                f"3sat,410,a.cnf,residual_train,3sat:410:a.cnf,{cnf}\n",
                encoding="utf-8",
            )
            manifest = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "split": ["residual_train"],
                    "row_id": ["3sat:410:a.cnf"],
                    "cnf_path": [str(cnf)],
                    "sample_seed": [1729],
                    "solver_seed": [1729],
                    "num_samples_generated": [2],
                    "sample_id": [0],
                    "elite_rank_in_instance": [1],
                    "Result": ["SATISFIABLE"],
                    "CPU time": [1.0],
                    "source_raw_csv": [str(raw)],
                    "source_raw_sha256": [file_sha256(raw)],
                    "source_checkpoint": [str(checkpoint.resolve())],
                    "source_checkpoint_sha256": [file_sha256(checkpoint)],
                }
            )
            manifest_path = root / "manifest.csv"
            manifest.to_csv(manifest_path, index=False)

            rows = audit_manifest(
                manifest_path=manifest_path,
                split_csv=split,
                checkpoint=checkpoint,
                expected_split="residual_train",
                min_positive_instances=1,
                max_per_instance=4,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["manifest_raw_sources_have_complete_sample_grid"], "fail")

    def test_training_config_audit_accepts_matching_replay_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            train = root / "train_manifest.csv"
            dev = root / "dev_manifest.csv"
            pd.DataFrame(
                {
                    "family": ["3sat", "3sat", "3sat"],
                    "size": [410, 410, 410],
                    "file_key": ["a.cnf", "b.cnf", "b.cnf"],
                }
            ).to_csv(train, index=False)
            pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [425],
                    "file_key": ["c.cnf"],
                }
            ).to_csv(dev, index=False)
            config = root / "config.yaml"
            OmegaConf.save(
                OmegaConf.create(
                    {
                        "elite_replay": {
                            "source_checkpoint_sha256": file_sha256(checkpoint),
                            "train_manifest": str(train.resolve()),
                            "train_manifest_sha256": file_sha256(train),
                            "train_elite_rows": 3,
                            "train_positive_instances": 2,
                            "dev_manifest": str(dev.resolve()),
                            "dev_manifest_sha256": file_sha256(dev),
                            "dev_elite_rows": 1,
                            "dev_positive_instances": 1,
                            "min_train_positive_instances": 2,
                            "min_dev_positive_instances": 1,
                            "expected_train_split": "residual_train",
                            "expected_dev_split": "residual_dev",
                            "expected_train_sample_seeds": "1729",
                            "expected_dev_sample_seeds": "1729",
                            "expected_train_num_samples": 16,
                            "expected_dev_num_samples": 16,
                            "allow_partial_manifest_training": False,
                            "limit_train_rows": 0,
                            "limit_dev_rows": 0,
                        }
                    }
                ),
                config,
            )

            rows = audit_training_config(
                config_path=config,
                checkpoint=checkpoint,
                train_manifest=train,
                dev_manifest=dev,
                min_train_positive_instances=2,
                min_dev_positive_instances=1,
                expected_train_split="residual_train",
                expected_dev_split="residual_dev",
                expected_train_sample_seeds="1729",
                expected_dev_sample_seeds="1729",
                expected_train_num_samples=16,
                expected_dev_num_samples=16,
            )

        self.assertTrue(all(row["status"] == "pass" for row in rows))

    def test_training_config_audit_rejects_wrong_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "source.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            train = root / "train_manifest.csv"
            pd.DataFrame({"family": ["3sat"], "size": [410], "file_key": ["a.cnf"]}).to_csv(train, index=False)
            config = root / "config.yaml"
            OmegaConf.save(
                OmegaConf.create(
                    {
                        "elite_replay": {
                            "source_checkpoint_sha256": file_sha256(checkpoint),
                            "train_manifest": str(train.resolve()),
                            "train_manifest_sha256": file_sha256(train),
                            "train_elite_rows": 1,
                            "train_positive_instances": 1,
                            "min_train_positive_instances": 0,
                            "min_dev_positive_instances": 0,
                            "expected_train_split": "residual_heldout",
                            "expected_dev_split": "residual_heldout",
                            "expected_train_sample_seeds": "1730",
                            "expected_dev_sample_seeds": "1730",
                            "expected_train_num_samples": 8,
                            "expected_dev_num_samples": 8,
                            "allow_partial_manifest_training": True,
                            "limit_train_rows": 2,
                            "limit_dev_rows": 1,
                        }
                    }
                ),
                config,
            )

            rows = audit_training_config(
                config_path=config,
                checkpoint=checkpoint,
                train_manifest=train,
                dev_manifest=None,
                min_train_positive_instances=8,
                min_dev_positive_instances=4,
                expected_train_split="residual_train",
                expected_dev_split="residual_dev",
                expected_train_sample_seeds="1729",
                expected_dev_sample_seeds="1729",
                expected_train_num_samples=16,
                expected_dev_num_samples=16,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["training_config_min_train_positive_floor_matches"], "fail")
        self.assertEqual(by_name["training_config_min_dev_positive_floor_matches"], "fail")
        self.assertEqual(by_name["training_config_expected_train_split_matches"], "fail")
        self.assertEqual(by_name["training_config_expected_dev_split_matches"], "fail")
        self.assertEqual(by_name["training_config_expected_train_sample_seeds_match"], "fail")
        self.assertEqual(by_name["training_config_expected_dev_sample_seeds_match"], "fail")
        self.assertEqual(by_name["training_config_expected_train_num_samples_match"], "fail")
        self.assertEqual(by_name["training_config_expected_dev_num_samples_match"], "fail")
        self.assertEqual(by_name["training_config_disallows_partial_manifest_training"], "fail")
        self.assertEqual(by_name["training_config_uses_full_manifests"], "fail")


if __name__ == "__main__":
    unittest.main()
