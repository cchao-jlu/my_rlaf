# Residual Elite Replay Manifest

This manifest contains solved sampled-March restarts for model-side
elite replay / behavior-cloning training. It is a training artifact,
not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv`
- max per instance: `4`
- manifest rows: `6`
- positive instances: `2`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv | 5ca693dce8b4293c55c6f3d43dc037c0fc33eba109e55e26be48189afbcaf7fa |

## Split Summary

| split | family | size | elite_rows | positive_instances |
| --- | --- | --- | --- | --- |
| residual_train | 3sat | 410 | 6 | 2 |

## Fastest Elites

| split | family | size | file_key | sample_seed | sample_id | elite_rank_in_instance | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| residual_train | 3sat | 410 | 3sat_13.cnf | 1729 | 2 | 1 | 55.46 |
| residual_train | 3sat | 410 | 3sat_13.cnf | 1729 | 12 | 2 | 55.5 |
| residual_train | 3sat | 410 | 3sat_13.cnf | 1729 | 8 | 3 | 56.04 |
| residual_train | 3sat | 410 | 3sat_13.cnf | 1729 | 11 | 4 | 56.46 |
| residual_train | 3sat | 410 | 3sat_122.cnf | 1729 | 5 | 1 | 56.91 |
| residual_train | 3sat | 410 | 3sat_122.cnf | 1729 | 13 | 2 | 57.71 |
