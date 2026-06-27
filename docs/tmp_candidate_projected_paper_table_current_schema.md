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
| strong_gate_candidate_instances | 150 |
| march_solved | 96 |
| cadical_solved | 67 |
| strong_solved_after_nominal_limit | 0 |
| union_solved | 101 |
| both_unknown_residual | 49 |
| residual_train_instances | not_reported |
| residual_dev_instances | not_reported |
| residual_heldout_instances | not_reported |
| residual_split_source | not_reported |
| residual_split_input_sha256 | not_reported |
| residual_split_candidate_manifest_sha256 | not_reported |
| oracle_neural_coverage | not_run |
| fixed_neural_residual_solves | not_run |
| fixed_neural_instances | 0 |
| fixed_neural_mean_allocated_budget | not_run |
| fixed_neural_mean_budget | not_run |
| fixed_neural_mean_probe_budget | not_run |
| fixed_neural_mean_generation_wall_time | not_run |
| fixed_neural_mean_probe_wall_time | not_run |
| fixed_neural_mean_full_allocated_budget | not_run |
| fixed_neural_mean_full_budget | not_run |
| fixed_neural_mean_full_wall_time | not_run |
| fixed_neural_mean_total_wall_time | not_run |
| fixed_non_neural_residual_solves | not_run |
| fixed_non_neural_instances | 0 |
| fixed_non_neural_mean_budget | not_run |
| fixed_non_neural_mean_wall_time | not_run |
| neural_only_over_non_neural | not_run |
| non_neural_only_over_neural | not_run |
| heldout_residual_manifest_instances | not_reported |
| heldout_neural_missing_instances | not_reported |
| heldout_non_neural_missing_instances | not_reported |

## Inputs

- strong_combined: `runs/analysis/benchmark_transition_band_expanded/combined.csv`
- candidate_manifest: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv`
- candidate_metadata: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json`
- split_manifest: `none`
- split_metadata: `none`
- oracle_summary: `none`
- neural_summary: `none`
- non_neural_summary: `none`
- output_csv: `runs/analysis/tmp_candidate_projected_paper_table_current_schema.csv`
