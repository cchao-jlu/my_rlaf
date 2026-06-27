# Residual Elite Replay Manifest

This manifest contains solved sampled-March restarts for model-side
elite replay / behavior-cloning training. It is a training artifact,
not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualTargetedIter22/last.pt`
- checkpoint sha256: `4cf7537b86c86d8caec832d064ee4704388ec881874d30950930d832fa329058`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22/both_unknown_subset.csv`
- max per instance: `4`
- manifest rows: `5`
- positive instances: `2`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22/raw_samples_all.csv | 49d4c6ee84c038c155afb3ce11efb604e80f469672075c55de49700ec1e847a5 |

## Split Summary

| split | family | size | elite_rows | positive_instances |
| --- | --- | --- | --- | --- |
|  | 3sat | 410 | 4 | 1 |
|  | 3sat | 425 | 1 | 1 |

## Fastest Elites

| split | family | size | file_key | sample_seed | sample_id | elite_rank_in_instance | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | 3sat | 410 | 3sat_12.cnf | 1729 | 11 | 1 | 1.05 |
|  | 3sat | 410 | 3sat_12.cnf | 1729 | 7 | 2 | 11.69 |
|  | 3sat | 410 | 3sat_12.cnf | 1729 | 12 | 3 | 18.66 |
|  | 3sat | 410 | 3sat_12.cnf | 1729 | 9 | 4 | 19.85 |
|  | 3sat | 425 | 3sat_28.cnf | 1729 | 3 | 1 | 59.24 |
