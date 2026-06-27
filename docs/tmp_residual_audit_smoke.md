# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | fail | missing: None |
| split_manifest_not_requested | pass | no split manifest path provided |
| heldout_neural_exists | pass | runs/analysis/tmp_residual_audit_smoke/neural.csv |
| heldout_non_neural_exists | pass | runs/analysis/tmp_residual_audit_smoke/non_neural.csv |
| heldout_same_instances | pass | neural=1 non_neural=1 symmetric_diff=0 |
| heldout_budget_match | pass | neural_mean=496.000 non_neural_mean=496.000 diff=0.000 |
| heldout_neural_reports_probe_budget | pass | neural summary should include probe_cpu_total |
| heldout_neural_reports_full_budget | pass | neural summary should include full_cpu_capped |
| selector_spec_exists | pass | runs/analysis/tmp_residual_audit_smoke/selector_spec.json |
| selector_spec_has_required_fields | pass | missing=[] |
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
