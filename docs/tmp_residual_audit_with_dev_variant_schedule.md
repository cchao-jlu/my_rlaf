# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | pass | runs/analysis/benchmark_transition_band_expanded_strict60_smoke/combined.csv |
| strong_uses_strict_solved_column | pass | combined.csv must contain strict solved |
| strong_reports_late_solves | pass | late solved rows must be reported, not folded into strict solved |
| strong_strict60_consistent | pass | mismatches=0 |
| candidate_manifest_not_requested | pass | no candidate manifest path provided |
| split_manifest_exists | fail | missing: runs/analysis/tmp_residual_audit_smoke/split_manifest.csv |
| heldout_neural_exists | pass | runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/expanded_early_trace_summary.csv |
| heldout_non_neural_exists | pass | runs/analysis/tmp_residual_audit_smoke/non_neural.csv |
| heldout_same_instances | pass | neural=1 non_neural=1 symmetric_diff=0 |
| heldout_budget_match | pass | neural_total_cpu_allocated_mean=496.000 non_neural_mean=496.000 diff=0.000 |
| heldout_neural_reports_probe_cpu_total | pass | neural summary should include allocated probe CPU |
| heldout_neural_reports_full_cpu_capped | pass | neural summary should include capped selected full-run CPU |
| heldout_neural_reports_total_cpu_allocated | pass | neural summary should include total allocated CPU for same-budget controls |
| heldout_neural_reports_full_cpu_allocated | pass | neural summary should include allocated selected full-run CPU |
| heldout_neural_reports_neural_generation_wall_time | fail | neural summary should include GNN/sample generation wall-clock overhead |
| heldout_neural_reports_probe_wall_time_total | fail | neural summary should include probe wall-clock overhead |
| heldout_neural_reports_full_wall_time_total | fail | neural summary should include selected full-run wall-clock time |
| heldout_neural_reports_total_wall_time | fail | neural summary should include total residual wall-clock time |
| selector_spec_exists | pass | runs/analysis/tmp_residual_audit_smoke/selector_spec.json |
| selector_spec_has_required_fields | fail | missing=['probe_solved_cap'] |
| selector_spec_reports_source | pass | selector_spec_source=runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/selector_spec.json |
| selector_spec_source_is_dev | pass | selector_spec_source=runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/selector_spec.json |
| selector_spec_kind | pass | kind=fixed_early_trace_neural_selector |
| non_neural_schedule_exists | pass | runs/analysis/tmp_residual_audit_smoke/non_neural_schedule_from_dev_variants.csv |
| non_neural_schedule_reports_source | pass | schedule artifact should report the dev neural summary source |
| non_neural_schedule_reports_source_split | pass | schedule artifact must explicitly record the split used to derive the budget |
| non_neural_schedule_source_split_is_dev | pass | source_split=dev |
| non_neural_schedule_not_from_heldout | pass | source=runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/expanded_early_trace_summary.csv |
| non_neural_schedule_source_hash_matches | pass | expected=1c7f02883ab0114505d7b25ba08f5db2009b98805652158d1f726259533d6096 actual=1c7f02883ab0114505d7b25ba08f5db2009b98805652158d1f726259533d6096 |
| non_neural_schedule_contains_march | pass | solvers=['march', 'cadical_seed1', 'cadical_plain_seed1', 'cadical_shuffle_seed1', 'march', 'cadical_seed1', 'cadical_plain_seed1', 'cadical_shuffle_seed1', 'march'] |
| non_neural_schedule_contains_cadical | pass | solvers=['march', 'cadical_seed1', 'cadical_plain_seed1', 'cadical_shuffle_seed1', 'march', 'cadical_seed1', 'cadical_plain_seed1', 'cadical_shuffle_seed1', 'march'] |
| non_neural_schedule_contains_cadical_variant | pass | cadical_solvers=['cadical_plain_seed1', 'cadical_seed1', 'cadical_shuffle_seed1'] |
| non_neural_schedule_matches_artifact | fail | expected=march:60,cadical_seed1:60,cadical_plain_seed1:60,cadical_shuffle_seed1:60,march:60,cadical_seed1:60,cadical_plain_seed1:60,cadical_shuffle_seed1:60,march:16 observed=['march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16'] |
| non_neural_run_schedule_source_not_requested | pass | no non-neural run schedule.csv provided |
