# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | pass | runs/analysis/benchmark_transition_band_expanded_strict60_smoke/combined.csv |
| strong_uses_strict_solved_column | pass | combined.csv must contain strict solved |
| strong_reports_late_solves | pass | late solved rows must be reported, not folded into strict solved |
| strong_strict60_consistent | pass | mismatches=0 |
| split_manifest_exists | fail | missing: runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv |
| heldout_neural_exists | fail | missing or empty: runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729/expanded_early_trace_summary.csv |
| heldout_non_neural_exists | fail | missing or empty: runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_budget120_seed1729/instance_summary.csv |
