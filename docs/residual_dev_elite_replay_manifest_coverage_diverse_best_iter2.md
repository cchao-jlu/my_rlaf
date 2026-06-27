# Residual Elite Replay Manifest

This manifest contains solved sampled-March restarts for model-side
elite replay / behavior-cloning training. It is a training artifact,
not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv`
- max per instance: `4`
- min positive instances: `4`
- require raw complete: `True`
- expected sample seeds: `1729`
- expected num samples: `16`
- manifest rows: `17`
- positive instances: `7`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv | d4bba8eb74b68554739ed41fc89ed7eecb808b6df72e779fb4043045ecb1deb2 |

## Split Summary

| split | family | size | elite_rows | positive_instances |
| --- | --- | --- | --- | --- |
| residual_dev | 3sat | 410 | 9 | 3 |
| residual_dev | 3sat | 440 | 8 | 4 |

## Fastest Elites

| split | family | size | file_key | sample_seed | sample_id | elite_rank_in_instance | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| residual_dev | 3sat | 440 | 3sat_293.cnf | 1729 | 15 | 1 | 3.443 |
| residual_dev | 3sat | 440 | 3sat_234.cnf | 1729 | 7 | 1 | 11.46 |
| residual_dev | 3sat | 440 | 3sat_293.cnf | 1729 | 4 | 2 | 19.65 |
| residual_dev | 3sat | 440 | 3sat_279.cnf | 1729 | 4 | 1 | 32.7 |
| residual_dev | 3sat | 440 | 3sat_293.cnf | 1729 | 8 | 3 | 37.73 |
| residual_dev | 3sat | 440 | 3sat_293.cnf | 1729 | 10 | 4 | 46.88 |
| residual_dev | 3sat | 410 | 3sat_170.cnf | 1729 | 4 | 1 | 51.79 |
| residual_dev | 3sat | 410 | 3sat_170.cnf | 1729 | 0 | 2 | 52.84 |
| residual_dev | 3sat | 410 | 3sat_170.cnf | 1729 | 15 | 3 | 53.51 |
| residual_dev | 3sat | 410 | 3sat_170.cnf | 1729 | 12 | 4 | 54.62 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | 1729 | 12 | 1 | 54.89 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | 1729 | 0 | 2 | 56.53 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | 1729 | 15 | 3 | 56.56 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | 1729 | 4 | 4 | 56.81 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | 1729 | 0 | 1 | 59.4 |
| residual_dev | 3sat | 410 | 3sat_30.cnf | 1729 | 8 | 1 | 59.42 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | 1729 | 6 | 2 | 59.68 |
