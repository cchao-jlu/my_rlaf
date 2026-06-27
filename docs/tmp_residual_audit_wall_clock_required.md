# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | fail | missing: None |
| candidate_manifest_not_requested | pass | no candidate manifest path provided |
| split_manifest_not_requested | pass | no split manifest path provided |
| heldout_neural_exists | pass | runs/analysis/tmp_residual_audit_smoke/neural.csv |
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
| selector_spec_has_required_fields | pass | missing=[] |
| selector_spec_reports_source | pass | selector_spec_source=runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/selector_spec.json |
| selector_spec_source_is_dev | pass | selector_spec_source=runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/selector_spec.json |
| selector_spec_kind | pass | kind=fixed_early_trace_neural_selector |
| selector_spec_matches_selector_policy | pass | expected=probe_solved_then_high_deadends observed=['probe_solved_then_high_deadends'] |
| selector_spec_matches_top_k | pass | expected=2 observed=[2] |
| selector_spec_matches_probe_cpu_lim | pass | expected=1.0 observed=[1.0] |
| selector_spec_matches_num_samples_generated | pass | expected=16 observed=[16] |
| selector_spec_matches_solver_seed | pass | expected=1729 observed=[1729] |
| selector_spec_matches_adaptive_top_k_a | pass | expected=8 observed=[8] |
| selector_spec_matches_adaptive_top_k_b | pass | expected=4 observed=[4] |
| selector_spec_matches_full_cpu_lim | pass | expected=60.0 observed=[60.0] |
| selector_spec_matches_sample_seeds | pass | expected=[1729] observed=[1729] |
| selector_spec_matches_adaptive_threshold_a | pass | expected=6.0 observed=[6.0] |
| selector_spec_matches_adaptive_threshold_b | pass | expected=3.0 observed=[3.0] |
| selector_spec_recomputes_effective_top_k | pass | bad_rows=0 |
| non_neural_schedule_exists | pass | runs/analysis/tmp_residual_audit_smoke/non_neural_schedule.csv |
| non_neural_schedule_reports_source | fail | schedule artifact should report the dev neural summary source |
| non_neural_schedule_matches_artifact | pass | expected=march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16 observed=['march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16'] |
| non_neural_run_schedule_source_exists | fail | missing: runs/analysis/tmp_residual_audit_smoke/non_neural_run_schedule.csv |
