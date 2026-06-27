# Residual Portfolio Paper Table

Scope: denominator-preserving summary for the residual portfolio mainline.
Oracle coverage is diagnostic; the paper claim must use fixed selected
neural portfolio versus fixed same-budget non-neural portfolio.

## Main Table

| quantity | value |
| --- | --- |
| candidate_instances | 150 |
| march_solved | 96 |
| cadical_solved | 67 |
| union_solved | 101 |
| both_unknown_residual | 49 |
| oracle_neural_coverage | 1 |
| fixed_neural_residual_solves | not_run |
| fixed_neural_instances | 0 |
| fixed_neural_mean_budget | not_run |
| fixed_non_neural_residual_solves | not_run |
| fixed_non_neural_instances | 0 |
| fixed_non_neural_mean_budget | not_run |
| neural_only_over_non_neural | not_run |
| non_neural_only_over_neural | not_run |

## Inputs

- strong_combined: `runs/analysis/benchmark_transition_band_expanded/combined.csv`
- oracle_summary: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/instance_oracle_summary.csv`
- neural_summary: `none`
- non_neural_summary: `none`
- output_csv: `runs/analysis/benchmark_transition_band_expanded/residual_portfolio_paper_table_smoke.csv`
