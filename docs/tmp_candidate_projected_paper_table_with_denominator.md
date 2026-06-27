# Residual Portfolio Paper Table

Scope: denominator-preserving summary for the residual portfolio mainline.
Oracle coverage is diagnostic; the paper claim must use fixed selected
neural portfolio versus fixed same-budget non-neural portfolio.

## Main Table

| quantity | value |
| --- | --- |
| full_candidate_instances | 900 |
| candidate_train_instances | 450 |
| candidate_dev_instances | 225 |
| candidate_heldout_instances | 225 |
| candidate_generation_seed | 2041 |
| candidate_split_seed | 1729 |
| candidate_manifest_sha256 | c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc |
| candidate_instances | 150 |
| march_solved | 92 |
| cadical_solved | 67 |
| strong_solved_after_nominal_limit | 4 |
| union_solved | 98 |
| both_unknown_residual | 52 |
| residual_train_instances | 25 |
| residual_dev_instances | 11 |
| residual_heldout_instances | 13 |
| residual_split_source | candidate_manifest |
| residual_split_input_sha256 | 7291d6c2a148ddf6965cbebb446bc52bfd3a7473d32ae9375f5a8050ab76b15c |
| residual_split_candidate_manifest_sha256 | c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc |
| oracle_neural_coverage | 1 |
| fixed_neural_residual_solves | not_run |
| fixed_neural_instances | 0 |
| fixed_neural_mean_allocated_budget | not_run |
| fixed_neural_mean_budget | not_run |
| fixed_neural_mean_probe_budget | not_run |
| fixed_neural_mean_full_allocated_budget | not_run |
| fixed_neural_mean_full_budget | not_run |
| fixed_non_neural_residual_solves | not_run |
| fixed_non_neural_instances | 0 |
| fixed_non_neural_mean_budget | not_run |
| neural_only_over_non_neural | not_run |
| non_neural_only_over_neural | not_run |
| heldout_residual_manifest_instances | 13 |
| heldout_neural_missing_instances | not_run |
| heldout_non_neural_missing_instances | not_run |

## Inputs

- strong_combined: `runs/analysis/benchmark_transition_band_expanded_strict60_smoke/combined.csv`
- candidate_manifest: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv`
- candidate_metadata: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json`
- split_manifest: `runs/analysis/tmp_candidate_projected_split_smoke/manifest.csv`
- split_metadata: `runs/analysis/tmp_candidate_projected_split_smoke/split_metadata.json`
- oracle_summary: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/instance_oracle_summary.csv`
- neural_summary: `none`
- non_neural_summary: `none`
- output_csv: `runs/analysis/tmp_candidate_projected_split_smoke/paper_table_with_denominator.csv`
