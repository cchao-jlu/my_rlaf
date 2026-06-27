# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | fail | missing: None |
| candidate_manifest_not_requested | pass | no candidate manifest path provided |
| split_manifest_not_requested | pass | no split manifest path provided |
| heldout_neural_exists | pass | runs/analysis/tmp_non_neural_per_instance_smoke2/synthetic_neural_summary_for_audit.csv |
| heldout_non_neural_exists | pass | runs/analysis/tmp_non_neural_per_instance_smoke2/run/instance_summary.csv |
| heldout_same_instances | pass | neural=1 non_neural=1 symmetric_diff=0 |
| heldout_budget_match_per_instance | pass | bad_instances=0 max_diff=0.000 |
| heldout_budget_match | pass | neural_total_cpu_allocated_mean=0.200 non_neural_mean=0.200 diff=0.000 |
| heldout_neural_reports_probe_cpu_total | pass | neural summary should include allocated probe CPU |
| heldout_neural_reports_full_cpu_capped | pass | neural summary should include capped selected full-run CPU |
| heldout_neural_reports_total_cpu_allocated | pass | neural summary should include total allocated CPU for same-budget controls |
| heldout_neural_reports_full_cpu_allocated | pass | neural summary should include allocated selected full-run CPU |
| heldout_neural_reports_neural_generation_wall_time | pass | neural summary should include GNN/sample generation wall-clock overhead |
| heldout_neural_reports_probe_wall_time_total | pass | neural summary should include probe wall-clock overhead |
| heldout_neural_reports_full_wall_time_total | pass | neural summary should include selected full-run wall-clock time |
| heldout_neural_reports_total_wall_time | pass | neural summary should include total residual wall-clock time |
| heldout_neural_total_wall_time_consistent | pass | bad_rows=0 |
| selector_spec_exists | pass | runs/analysis/tmp_non_neural_per_instance_smoke2/selector_spec.json |
| selector_spec_has_required_fields | pass | missing=[] |
| selector_spec_reports_source | pass | selector_spec_source=runs/analysis/tmp_non_neural_per_instance_smoke2/dev_selector_spec.json |
| selector_spec_source_is_dev | pass | selector_spec_source=runs/analysis/tmp_non_neural_per_instance_smoke2/dev_selector_spec.json |
| selector_spec_source_split_is_dev | pass | selector_spec_source_split=dev |
| selector_spec_source_hash_matches | pass | expected=952b743fbb81834e8310650c64a2c8552ab96fd1eb48fbf86861f042cc550852 actual=952b743fbb81834e8310650c64a2c8552ab96fd1eb48fbf86861f042cc550852 |
| selector_spec_kind | pass | kind=fixed_early_trace_neural_selector |
| selector_spec_matches_selector_policy | pass | expected=probe_solved_then_high_deadends observed=['probe_solved_then_high_deadends'] |
| selector_spec_matches_top_k | pass | expected=1 observed=[1] |
| selector_spec_matches_probe_cpu_lim | pass | expected=0.1 observed=[0.1] |
| selector_spec_matches_num_samples_generated | pass | expected=1 observed=[1] |
| selector_spec_matches_solver_seed | pass | expected=1729 observed=[1729] |
| selector_spec_matches_probe_solved_cap | pass | expected=1 observed=[1] |
| selector_spec_matches_full_cpu_lim | pass | expected=0.1 observed=[0.1] |
| selector_spec_matches_sample_seeds | pass | expected=[1729] observed=[1729] |
| selector_spec_recomputes_effective_top_k | pass | bad_rows=0 |
| non_neural_schedule_exists | pass | runs/analysis/tmp_non_neural_per_instance_smoke2/source_schedule.csv |
| non_neural_schedule_reports_source | pass | schedule artifact should report the dev neural summary source |
| non_neural_schedule_reports_source_split | pass | schedule artifact must explicitly record the split used to derive the budget |
| non_neural_schedule_source_split_is_dev | pass | source_split=dev |
| non_neural_schedule_not_from_heldout | pass | source=runs/analysis/tmp_non_neural_per_instance_smoke2/synthetic_dev_summary.csv |
| non_neural_schedule_source_hash_matches | pass | expected=dc1ff28e97d87a8b3e427414f6c53491077a3573a761549f9428f9e1c71e2c63 actual=dc1ff28e97d87a8b3e427414f6c53491077a3573a761549f9428f9e1c71e2c63 |
| non_neural_schedule_contains_march | pass | solvers=['march', 'cadical_seed1'] |
| non_neural_schedule_contains_cadical | pass | solvers=['march', 'cadical_seed1'] |
| non_neural_schedule_contains_cadical_variant | pass | cadical_solvers=['cadical_seed1'] |
| non_neural_per_instance_schedules_follow_frozen_cycle | pass | bad_rows=0 solver_cycle=['march', 'cadical_seed1'] attempt_limit=0.1 |
| non_neural_schedule_matches_artifact | pass | per_instance schedules derived from frozen cycle; observed_count=1 |
| non_neural_run_schedule_source_exists | pass | runs/analysis/tmp_non_neural_per_instance_smoke2/run/schedule.csv |
| non_neural_run_schedule_source_matches | pass | expected=runs/analysis/tmp_non_neural_per_instance_smoke2/source_schedule.csv observed=['runs/analysis/tmp_non_neural_per_instance_smoke2/source_schedule.csv'] |
