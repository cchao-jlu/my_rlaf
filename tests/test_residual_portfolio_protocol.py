import tempfile
import unittest
from pathlib import Path

import pandas as pd

from audit_residual_portfolio_protocol import (
    audit_gate_record,
    audit_heldout,
    audit_non_neural_schedule,
    audit_selector_spec,
)
from build_non_neural_schedule_from_neural_budget import build_schedule, format_variant_details
from decide_residual_portfolio_gate import (
    REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS,
    file_sha256,
    parse_bool_series,
    validate_oracle_summary,
    validate_oracle_checkpoint_provenance,
    validate_training_config_audit,
)
from run_residual_non_neural_budget_control import attach_instance_budgets, build_command
from summarize_residual_portfolio_paper_table import budget_match_counts
from summarize_residual_portfolio_paper_table import oracle_count, non_neural_counts, selected_neural_counts


class ResidualPortfolioProtocolTest(unittest.TestCase):
    def test_gate_training_config_audit_requires_formal_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.csv"
            audit.write_text("check,status,detail\nx,pass,ok\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required checks"):
                validate_training_config_audit(audit)

    def test_gate_training_config_audit_accepts_formal_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.csv"
            pd.DataFrame(
                {
                    "check": sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "status": ["pass"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "detail": ["ok"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                }
            ).to_csv(audit, index=False)

            checks, failures = validate_training_config_audit(audit)

        self.assertEqual(checks, len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS))
        self.assertEqual(failures, 0)

    def test_build_schedule_cycles_solver_variants(self):
        schedule = build_schedule(
            total_budget=130.0,
            solver_cycle=["march", "cadical_seed1", "cadical_plain_seed1"],
            attempt_limit=60.0,
        )

        self.assertEqual(
            schedule,
            [
                ("march", 60.0),
                ("cadical_seed1", 60.0),
                ("cadical_plain_seed1", 10.0),
            ],
        )

    def test_cadical_variant_command_records_fixed_config(self):
        command = build_command("cadical_plain_seed1", Path("x.cnf"), 0.5)

        self.assertIn("-t", command)
        self.assertIn("0.5", command)
        self.assertIn("--plain", command)
        self.assertIn("--seed=1", command)

    def test_variant_details_describe_frozen_schedule_entries(self):
        details = format_variant_details(["march", "cadical_shuffle_seed1"])

        self.assertIn("march(binary=march args=<none>)", details)
        self.assertIn("cadical_shuffle_seed1(binary=cadical args=--shuffle --seed=1)", details)

    def test_audit_rejects_non_dev_or_default_only_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            neural_summary = root / "neural_dev.csv"
            neural_summary.write_text("size,file_key,total_cpu_allocated\n410,a.cnf,120\n", encoding="utf-8")
            non_neural = pd.DataFrame(
                {
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "schedule": ["march:60,cadical:60"],
                }
            )
            schedule = root / "schedule.csv"
            schedule.write_text(
                "\n".join(
                    [
                        "neural_summary,neural_summary_sha256,source_split,schedule",
                        f"{neural_summary},missing,heldout,\"march:60,cadical:60\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            rows = audit_non_neural_schedule(non_neural=non_neural, schedule_path=schedule)

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["non_neural_schedule_source_split_is_dev"], "fail")
        self.assertEqual(by_name["non_neural_schedule_source_hash_matches"], "fail")
        self.assertEqual(by_name["non_neural_schedule_contains_cadical_variant"], "fail")

    def test_audit_rejects_selector_spec_without_dev_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "selector_spec.json"
            spec.write_text(
                """
{
  "kind": "fixed_early_trace_neural_selector",
  "selector_spec_source": "runs/analysis/heldout_selector/selector_spec.json",
  "checkpoint": "runs/GNN_March_3SAT/best.pt",
  "policy": "probe_solved_then_high_deadends",
  "top_k": 2,
  "probe_cpu_lim": 1.0,
  "full_cpu_lim": 60.0,
  "num_samples": 16,
  "sample_seeds": [1729],
  "solver_seed": 1729,
  "probe_solved_cap": 1
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            neural = pd.DataFrame(
                {
                    "selector_policy": ["probe_solved_then_high_deadends"],
                    "top_k": [2],
                    "probe_cpu_lim": [1.0],
                    "full_cpu_lim": [60.0],
                    "num_samples_generated": [16],
                    "solver_seed": [1729],
                    "probe_solved_cap": [1],
                    "sample_seed": [1729],
                    "selector_rule": ["fixed_top_k"],
                    "effective_top_k": [2],
                    "probe_solved_samples": [0],
                    "max_probe_deadends": [0.0],
                }
            )

            rows = audit_selector_spec(neural=neural, selector_spec_path=spec)

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["selector_spec_source_is_dev"], "fail")
        self.assertEqual(by_name["selector_spec_source_split_is_dev"], "fail")
        self.assertEqual(by_name["selector_spec_source_hash_matches"], "fail")

    def test_audit_rejects_selector_checkpoint_hash_mismatch_from_dev_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dev_spec = root / "dev_selector_spec.json"
            dev_spec.write_text(
                """
{
  "kind": "fixed_early_trace_neural_selector",
  "checkpoint_sha256": "devhash"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            spec = root / "heldout_selector_spec.json"
            spec.write_text(
                f"""
{{
  "kind": "fixed_early_trace_neural_selector",
  "selector_spec_source": "{dev_spec}",
  "selector_spec_source_sha256": "{file_sha256(dev_spec)}",
  "selector_spec_source_split": "dev",
  "checkpoint": "runs/GNN_March_3SAT/best.pt",
  "checkpoint_sha256": "heldouthash",
  "policy": "probe_solved_then_high_deadends",
  "top_k": 2,
  "probe_cpu_lim": 1.0,
  "full_cpu_lim": 60.0,
  "num_samples": 16,
  "sample_seeds": [1729],
  "solver_seed": 1729,
  "probe_solved_cap": 1
}}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            neural = pd.DataFrame(
                {
                    "selector_policy": ["probe_solved_then_high_deadends"],
                    "top_k": [2],
                    "probe_cpu_lim": [1.0],
                    "full_cpu_lim": [60.0],
                    "num_samples_generated": [16],
                    "solver_seed": [1729],
                    "probe_solved_cap": [1],
                    "sample_seed": [1729],
                    "selector_rule": ["fixed_top_k"],
                    "effective_top_k": [2],
                    "probe_solved_samples": [0],
                    "max_probe_deadends": [0.0],
                }
            )

            rows = audit_selector_spec(neural=neural, selector_spec_path=spec)

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["selector_spec_source_hash_matches"], "pass")
        self.assertEqual(by_name["selector_spec_checkpoint_hash_matches_source"], "fail")

    def test_attach_instance_budgets_uses_frozen_cycle_per_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            neural_summary = root / "neural_heldout.csv"
            neural_summary.write_text(
                "size,file_key,total_cpu_allocated\n"
                "410,a.cnf,121\n"
                "410,b.cnf,61\n",
                encoding="utf-8",
            )
            subset = pd.DataFrame(
                {
                    "family": ["3sat", "3sat"],
                    "size": [410, 410],
                    "file_key": ["a.cnf", "b.cnf"],
                }
            )

            budgeted, source = attach_instance_budgets(
                subset=subset,
                neural_budget_summary=neural_summary,
                schedule_metadata={"solver_cycle": "march,cadical_seed1", "attempt_limit": "60"},
                fallback_schedule=[("march", 60.0), ("cadical_seed1", 60.0)],
            )

        schedules = dict(zip(budgeted["file_key"], budgeted["non_neural_schedule"]))
        self.assertEqual(schedules["a.cnf"], "march:60,cadical_seed1:60,march:1")
        self.assertEqual(schedules["b.cnf"], "march:60,cadical_seed1:1")
        self.assertIn("per_instance_total_cpu_allocated", source)

    def test_audit_accepts_per_instance_budget_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_summary = root / "neural_dev.csv"
            source_summary.write_text("size,file_key,total_cpu_allocated\n410,a.cnf,60\n", encoding="utf-8")
            schedule = root / "schedule.csv"
            schedule.write_text(
                "\n".join(
                    [
                        "neural_summary,neural_summary_sha256,source_split,schedule,solver_cycle,attempt_limit",
                        f"{source_summary},{'0'*64},dev,\"march:60,cadical_seed1:60\",\"march,cadical_seed1\",60",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text(
                """
{
  "kind": "fixed_early_trace_neural_selector",
  "selector_spec_source": "dev_selector_spec.json",
  "selector_spec_source_sha256": "missing",
  "selector_spec_source_split": "dev",
  "checkpoint": "runs/GNN_March_3SAT/best.pt",
  "policy": "probe_solved_then_high_deadends",
  "top_k": 2,
  "probe_cpu_lim": 1.0,
  "full_cpu_lim": 60.0,
  "num_samples": 16,
  "sample_seeds": [1729],
  "solver_seed": 1729,
  "probe_solved_cap": 1
}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            neural = pd.DataFrame(
                {
                    "size": [410, 410],
                    "file_key": ["a.cnf", "b.cnf"],
                    "total_cpu_allocated": [121.0, 61.0],
                    "probe_cpu_total": [16.0, 16.0],
                    "full_cpu_allocated": [105.0, 45.0],
                    "full_cpu_capped": [60.0, 45.0],
                    "neural_generation_wall_time": [0.1, 0.1],
                    "probe_wall_time_total": [1.0, 1.0],
                    "full_wall_time_total": [2.0, 2.0],
                    "total_wall_time": [3.1, 3.1],
                    "selector_policy": ["probe_solved_then_high_deadends", "probe_solved_then_high_deadends"],
                    "top_k": [2, 2],
                    "probe_cpu_lim": [1.0, 1.0],
                    "full_cpu_lim": [60.0, 60.0],
                    "num_samples_generated": [16, 16],
                    "solver_seed": [1729, 1729],
                    "probe_solved_cap": [1, 1],
                    "sample_seed": [1729, 1729],
                    "selector_rule": ["fixed_top_k", "fixed_top_k"],
                    "effective_top_k": [2, 2],
                    "probe_solved_samples": [0, 0],
                    "max_probe_deadends": [0.0, 0.0],
                }
            )
            non_neural = pd.DataFrame(
                {
                    "size": [410, 410],
                    "file_key": ["a.cnf", "b.cnf"],
                    "budget_cpu_total": [121.0, 61.0],
                    "schedule": ["march:60,cadical_seed1:60,march:1", "march:60,cadical_seed1:1"],
                    "schedule_mode": ["per_instance", "per_instance"],
                }
            )

            rows = audit_heldout(
                neural_path=None,
                non_neural_path=None,
                budget_tolerance=1e-6,
                selector_spec_path=selector_spec,
                non_neural_schedule_path=schedule,
                non_neural_run_schedule_path=None,
            )
            # Directly exercise the budget checks with temporary CSVs because audit_heldout loads paths.
            neural_path = root / "neural.csv"
            non_neural_path = root / "non_neural.csv"
            neural.to_csv(neural_path, index=False)
            non_neural.to_csv(non_neural_path, index=False)
            rows = audit_heldout(
                neural_path=neural_path,
                non_neural_path=non_neural_path,
                budget_tolerance=1e-6,
                selector_spec_path=selector_spec,
                non_neural_schedule_path=schedule,
                non_neural_run_schedule_path=None,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["heldout_neural_group_keys_unique"], "pass")
        self.assertEqual(by_name["heldout_non_neural_instance_keys_unique"], "pass")
        self.assertEqual(by_name["heldout_budget_match_per_instance"], "pass")
        self.assertEqual(by_name["heldout_budget_match"], "pass")
        self.assertEqual(by_name["non_neural_per_instance_schedules_follow_frozen_cycle"], "pass")
        self.assertEqual(by_name["non_neural_schedule_matches_artifact"], "pass")

    def test_paper_table_bool_counts_do_not_treat_string_false_as_true(self):
        oracle = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "solved_any": ["False", "True"],
            }
        )
        neural = pd.DataFrame(
            {
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "solved_any_strict60": ["False", "True"],
                "total_cpu_capped": [60.0, 30.0],
            }
        )
        non_neural = pd.DataFrame(
            {
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "solved_any": ["False", "True"],
                "budget_cpu_total": [60.0, 60.0],
            }
        )

        self.assertEqual(oracle_count(oracle), 1)
        self.assertEqual(selected_neural_counts(neural)["fixed_neural_residual_solves"], 1)
        self.assertEqual(non_neural_counts(non_neural)["fixed_non_neural_residual_solves"], 1)

    def test_paper_table_rejects_duplicate_oracle_and_non_neural_keys(self):
        duplicate_oracle = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "solved_any": [False, True],
            }
        )
        duplicate_non_neural = pd.DataFrame(
            {
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "solved_any": [False, True],
                "budget_cpu_total": [60.0, 60.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "duplicate instance"):
            oracle_count(duplicate_oracle)
        with self.assertRaisesRegex(ValueError, "duplicate instance"):
            non_neural_counts(duplicate_non_neural)

    def test_file_sha256_records_gate_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.pt"
            path.write_text("checkpoint-bytes\n", encoding="utf-8")

            digest = file_sha256(path)

        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, "0" * 64)

    def test_gate_bool_parser_does_not_treat_string_false_as_true(self):
        values = parse_bool_series(pd.Series(["True", "False", 1, 0]), "solved_any")

        self.assertEqual(values.tolist(), [True, False, True, False])

    def test_gate_oracle_summary_rejects_wrong_denominator_by_default(self):
        oracle = pd.DataFrame(
            {
                "family": ["3sat"],
                "size": [410],
                "file_key": ["a.cnf"],
                "solved_any": [False],
            }
        )

        with self.assertRaisesRegex(ValueError, "denominator"):
            validate_oracle_summary(oracle, expected_total=49, allow_diagnostic_total=False)

    def test_gate_oracle_summary_rejects_duplicate_instance_keys(self):
        oracle = pd.DataFrame(
            {
                "family": ["3sat", "3sat"],
                "size": [410, 410],
                "file_key": ["a.cnf", "a.cnf"],
                "solved_any": [False, True],
            }
        )

        with self.assertRaisesRegex(ValueError, "duplicate instance"):
            validate_oracle_summary(oracle, expected_total=2, allow_diagnostic_total=False)

    def test_gate_training_config_audit_must_have_no_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            passing = root / "passing.csv"
            rows = [
                {"check": check, "status": "pass", "detail": "ok"}
                for check in sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)
            ]
            pd.DataFrame(rows).to_csv(passing, index=False)
            failing = root / "failing.csv"
            rows[0]["status"] = "fail"
            pd.DataFrame(rows).to_csv(failing, index=False)

            checks, failures = validate_training_config_audit(passing)
            self.assertEqual(checks, len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS))
            self.assertEqual(failures, 0)
            with self.assertRaisesRegex(ValueError, "has failures"):
                validate_training_config_audit(failing)

    def test_gate_rejects_oracle_summary_checkpoint_hash_mismatch_when_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checkpoint = root / "checkpoint.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            oracle = pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "solved_any": [False],
                    "source_checkpoint_sha256": ["0" * 64],
                }
            )

            with self.assertRaisesRegex(ValueError, "checkpoint hash"):
                validate_oracle_checkpoint_provenance(oracle, checkpoint_path=checkpoint)

    def test_final_audit_requires_passed_gate_record_matching_selector_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            checkpoint_hash = file_sha256(checkpoint)
            oracle = root / "oracle.csv"
            pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "solved_any": [True],
                    "source_checkpoint_sha256": [checkpoint_hash],
                }
            ).to_csv(oracle, index=False)
            training_audit = root / "training_config_audit.csv"
            pd.DataFrame(
                {
                    "check": sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "status": ["pass"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "detail": ["ok"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                }
            ).to_csv(training_audit, index=False)
            selector_spec.write_text(
                f"""
{{
  "kind": "fixed_early_trace_neural_selector",
  "checkpoint": "{checkpoint}",
  "checkpoint_sha256": "{checkpoint_hash}"
}}
""".strip()
                + "\n",
                encoding="utf-8",
            )
            gate_record.write_text(
                f"""
{{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "source": "{oracle}",
  "source_sha256": "{file_sha256(oracle)}",
  "checkpoint": "{checkpoint}",
  "checkpoint_sha256": "{checkpoint_hash}",
  "oracle_checkpoint_sha256": "{checkpoint_hash}",
  "oracle_checkpoint_provenance_check": "pass",
  "training_config_audit": "{training_audit}",
  "training_config_audit_sha256": "{file_sha256(training_audit)}",
  "training_config_audit_checks": {len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)},
  "training_config_audit_failures": 0,
  "allow_diagnostic_total": false,
  "total": 1,
  "expected_total": 1,
  "oracle_solved": 1,
  "pass_min": 1
}}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_decision_pass"], "pass")
        self.assertEqual(by_name["gate_record_denominator_matches"], "pass")
        self.assertEqual(by_name["gate_record_oracle_source_hash_matches"], "pass")
        self.assertEqual(by_name["gate_record_oracle_source_solved_matches_record"], "pass")
        self.assertEqual(by_name["gate_record_checkpoint_hash_matches"], "pass")
        self.assertEqual(by_name["gate_record_oracle_checkpoint_provenance_pass"], "pass")
        self.assertEqual(by_name["gate_record_oracle_source_checkpoint_hash_matches"], "pass")
        self.assertEqual(by_name["gate_record_training_config_audit_hash_matches"], "pass")
        self.assertEqual(by_name["gate_record_training_config_audit_has_formal_checks"], "pass")
        self.assertEqual(by_name["gate_record_training_config_audit_has_no_failures"], "pass")
        self.assertEqual(by_name["selector_spec_checkpoint_matches_gate_record"], "pass")

    def test_final_audit_rejects_gate_record_when_oracle_source_disagrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            checkpoint = root / "best.pt"
            checkpoint.write_text("checkpoint\n", encoding="utf-8")
            checkpoint_hash = file_sha256(checkpoint)
            oracle = root / "oracle.csv"
            pd.DataFrame(
                {
                    "family": ["3sat"],
                    "size": [410],
                    "file_key": ["a.cnf"],
                    "solved_any": [False],
                    "source_checkpoint_sha256": [checkpoint_hash],
                }
            ).to_csv(oracle, index=False)
            training_audit = root / "training_config_audit.csv"
            pd.DataFrame(
                {
                    "check": sorted(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "status": ["pass"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                    "detail": ["ok"] * len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS),
                }
            ).to_csv(training_audit, index=False)
            selector_spec.write_text(f'{{"checkpoint_sha256": "{checkpoint_hash}"}}\n', encoding="utf-8")
            gate_record.write_text(
                f"""
{{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "source": "{oracle}",
  "source_sha256": "{file_sha256(oracle)}",
  "checkpoint": "{checkpoint}",
  "checkpoint_sha256": "{checkpoint_hash}",
  "oracle_checkpoint_sha256": "{checkpoint_hash}",
  "oracle_checkpoint_provenance_check": "pass",
  "training_config_audit": "{training_audit}",
  "training_config_audit_sha256": "{file_sha256(training_audit)}",
  "training_config_audit_checks": {len(REQUIRED_TRAINING_CONFIG_AUDIT_CHECKS)},
  "training_config_audit_failures": 0,
  "allow_diagnostic_total": false,
  "total": 1,
  "expected_total": 1,
  "oracle_solved": 1,
  "pass_min": 1
}}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_decision_pass"], "pass")
        self.assertEqual(by_name["gate_record_oracle_source_hash_matches"], "pass")
        self.assertEqual(by_name["gate_record_oracle_source_solved_matches_record"], "fail")

    def test_final_audit_reports_unparseable_gate_record_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text('{"checkpoint_sha256": "abc123"}\n', encoding="utf-8")
            gate_record.write_text(
                """
{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "allow_diagnostic_total": false,
  "total": "forty-nine",
  "expected_total": 49,
  "oracle_solved": 5,
  "pass_min": 5,
  "checkpoint_sha256": "abc123"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_numeric_fields_parseable"], "fail")
        self.assertEqual(by_name["gate_record_denominator_matches"], "fail")

    def test_final_audit_rejects_boolean_gate_record_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text('{"checkpoint_sha256": "abc123"}\n', encoding="utf-8")
            gate_record.write_text(
                """
{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "allow_diagnostic_total": false,
  "total": true,
  "expected_total": 1,
  "oracle_solved": 1,
  "pass_min": 1,
  "checkpoint_sha256": "abc123"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_numeric_fields_parseable"], "fail")
        self.assertEqual(by_name["gate_record_denominator_matches"], "fail")

    def test_final_audit_rejects_failed_gate_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text('{"checkpoint_sha256": "abc123"}\n', encoding="utf-8")
            gate_record.write_text(
                """
{
  "kind": "residual_portfolio_gate_decision",
  "decision": "fail",
  "allow_diagnostic_total": false,
  "total": 49,
  "expected_total": 49,
  "oracle_solved": 2,
  "pass_min": 5,
  "checkpoint_sha256": "abc123"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_decision_pass"], "fail")
        self.assertEqual(by_name["gate_record_oracle_solved_meets_pass_min"], "fail")

    def test_final_audit_rejects_gate_record_without_explicit_non_diagnostic_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text('{"checkpoint_sha256": "abc123"}\n', encoding="utf-8")
            gate_record.write_text(
                """
{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "total": 49,
  "expected_total": 49,
  "oracle_solved": 5,
  "pass_min": 5,
  "checkpoint_sha256": "abc123"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_decision_pass"], "pass")
        self.assertEqual(by_name["gate_record_not_diagnostic_total"], "fail")

    def test_final_audit_rejects_string_non_diagnostic_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate_record = root / "gate.json"
            selector_spec = root / "selector_spec.json"
            selector_spec.write_text('{"checkpoint_sha256": "abc123"}\n', encoding="utf-8")
            gate_record.write_text(
                """
{
  "kind": "residual_portfolio_gate_decision",
  "decision": "pass",
  "allow_diagnostic_total": "false",
  "total": 49,
  "expected_total": 49,
  "oracle_solved": 5,
  "pass_min": 5,
  "checkpoint_sha256": "abc123"
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            rows = audit_gate_record(
                gate_record_path=gate_record,
                selector_spec_path=selector_spec,
                require_gate_pass=True,
            )

        by_name = {row["check"]: row["status"] for row in rows}
        self.assertEqual(by_name["gate_record_decision_pass"], "pass")
        self.assertEqual(by_name["gate_record_not_diagnostic_total"], "fail")

    def test_paper_table_reports_per_instance_budget_diff(self):
        neural = pd.DataFrame(
            {
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "total_cpu_allocated": [121.0, 61.0],
            }
        )
        non_neural = pd.DataFrame(
            {
                "size": [410, 410],
                "file_key": ["a.cnf", "b.cnf"],
                "budget_cpu_total": [121.0, 60.5],
            }
        )

        counts = budget_match_counts(neural, non_neural)

        self.assertEqual(counts["same_budget_max_per_instance_diff"], 0.5)
        self.assertEqual(counts["same_budget_mean_per_instance_diff"], 0.25)


if __name__ == "__main__":
    unittest.main()
