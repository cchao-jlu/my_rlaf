# Residual Elite Replay Manifest

This manifest contains solved sampled-March restarts for model-side
elite replay / behavior-cloning training. It is a training artifact,
not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv`
- max per instance: `4`
- min positive instances: `8`
- require raw complete: `True`
- expected sample seeds: `1729`
- expected num samples: `16`
- manifest rows: `109`
- positive instances: `30`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv | 813da5c139c42e4fbc95d7e251f5ee3c240698a2816c13a86a728daf7ee502d4 |

## Split Summary

| split | family | size | elite_rows | positive_instances |
| --- | --- | --- | --- | --- |
| residual_train | 3sat | 410 | 42 | 12 |
| residual_train | 3sat | 425 | 41 | 11 |
| residual_train | 3sat | 440 | 26 | 7 |

## Fastest Elites

| split | family | size | file_key | sample_seed | sample_id | elite_rank_in_instance | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| residual_train | 3sat | 440 | 3sat_118.cnf | 1729 | 1 | 1 | 0.2712 |
| residual_train | 3sat | 440 | 3sat_118.cnf | 1729 | 5 | 2 | 0.3388 |
| residual_train | 3sat | 440 | 3sat_135.cnf | 1729 | 0 | 1 | 0.5715 |
| residual_train | 3sat | 440 | 3sat_135.cnf | 1729 | 7 | 2 | 0.9667 |
| residual_train | 3sat | 440 | 3sat_142.cnf | 1729 | 15 | 1 | 1.322 |
| residual_train | 3sat | 440 | 3sat_115.cnf | 1729 | 15 | 1 | 1.773 |
| residual_train | 3sat | 440 | 3sat_135.cnf | 1729 | 8 | 3 | 4.974 |
| residual_train | 3sat | 440 | 3sat_230.cnf | 1729 | 13 | 1 | 5.923 |
| residual_train | 3sat | 440 | 3sat_135.cnf | 1729 | 2 | 4 | 6.466 |
| residual_train | 3sat | 440 | 3sat_115.cnf | 1729 | 6 | 2 | 8.651 |
| residual_train | 3sat | 440 | 3sat_118.cnf | 1729 | 2 | 3 | 9.411 |
| residual_train | 3sat | 440 | 3sat_118.cnf | 1729 | 12 | 4 | 9.949 |
| residual_train | 3sat | 440 | 3sat_115.cnf | 1729 | 10 | 3 | 10.71 |
| residual_train | 3sat | 440 | 3sat_142.cnf | 1729 | 12 | 2 | 14.06 |
| residual_train | 3sat | 440 | 3sat_142.cnf | 1729 | 0 | 3 | 16.33 |
| residual_train | 3sat | 440 | 3sat_230.cnf | 1729 | 6 | 2 | 18.63 |
| residual_train | 3sat | 440 | 3sat_230.cnf | 1729 | 0 | 3 | 19.25 |
| residual_train | 3sat | 425 | 3sat_229.cnf | 1729 | 14 | 1 | 19.93 |
| residual_train | 3sat | 440 | 3sat_115.cnf | 1729 | 14 | 4 | 31.1 |
| residual_train | 3sat | 440 | 3sat_142.cnf | 1729 | 11 | 4 | 33.21 |
