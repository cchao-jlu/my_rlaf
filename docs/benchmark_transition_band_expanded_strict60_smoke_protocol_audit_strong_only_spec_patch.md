# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | pass | runs/analysis/benchmark_transition_band_expanded_strict60_smoke/combined.csv |
| strong_uses_strict_solved_column | pass | combined.csv must contain strict solved |
| strong_reports_late_solves | pass | late solved rows must be reported, not folded into strict solved |
| strong_strict60_consistent | pass | mismatches=0 |
| split_manifest_not_requested | pass | no split manifest path provided |
| heldout_audit_not_requested | pass | no held-out summary paths provided |
