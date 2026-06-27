# Residual Portfolio Paper Table

Scope: denominator-preserving summary for the residual portfolio mainline.
Oracle coverage is diagnostic; the paper claim must use fixed selected
neural portfolio versus fixed same-budget non-neural portfolio.

## Main Table

| quantity | value |
| --- | --- |
| candidate_instances | 1 |
| march_solved | 0 |
| cadical_solved | 0 |
| strong_solved_after_nominal_limit | 0 |
| union_solved | 0 |
| both_unknown_residual | 1 |
| oracle_neural_coverage | not_run |
| fixed_neural_residual_solves | 0 |
| fixed_neural_instances | 1 |
| fixed_neural_mean_allocated_budget | 496.000 |
| fixed_neural_mean_budget | 496.000 |
| fixed_neural_mean_probe_budget | 16.000 |
| fixed_neural_mean_full_budget | 480.000 |
| fixed_neural_mean_full_allocated_budget | 480.000 |
| fixed_non_neural_residual_solves | 0 |
| fixed_non_neural_instances | 1 |
| fixed_non_neural_mean_budget | 496.000 |
| neural_only_over_non_neural | 0 |
| non_neural_only_over_neural | 0 |

## Inputs

- strong_combined: `runs/analysis/tmp_paper_table_smoke/strong.csv`
- oracle_summary: `none`
- neural_summary: `runs/analysis/tmp_residual_audit_smoke/neural.csv`
- non_neural_summary: `runs/analysis/tmp_residual_audit_smoke/non_neural.csv`
- output_csv: `runs/analysis/tmp_paper_table_smoke/table.csv`
