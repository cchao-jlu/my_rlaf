# Residual Contrastive Replay Manifest

This manifest contains solved sampled-March restarts and same-CNF failed
samples for model-side contrastive residual-policy training. It is a
training artifact, not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv`
- max positives per instance: `2`
- max negatives per instance: `4`
- negative selection: `low_progress`
- min positive instances: `8`
- require raw complete: `True`
- expected sample seeds: `1729`
- expected num samples: `16`
- manifest rows: `156`
- positive instances: `27`
- contrastive groups: `27`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv | 813da5c139c42e4fbc95d7e251f5ee3c240698a2816c13a86a728daf7ee502d4 |

## Role Summary

| split | family | size | sample_role | rows | instances |
| --- | --- | --- | --- | --- | --- |
| residual_train | 3sat | 410 | negative | 44 | 12 |
| residual_train | 3sat | 410 | positive | 23 | 12 |
| residual_train | 3sat | 425 | negative | 35 | 9 |
| residual_train | 3sat | 425 | positive | 18 | 9 |
| residual_train | 3sat | 440 | negative | 24 | 6 |
| residual_train | 3sat | 440 | positive | 12 | 6 |

## Selected Samples

| split | family | size | file_key | sample_role | sample_seed | sample_id | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| residual_train | 3sat | 440 | 3sat_135.cnf | positive | 1729 | 0 | 0.5715 |
| residual_train | 3sat | 440 | 3sat_135.cnf | positive | 1729 | 7 | 0.9667 |
| residual_train | 3sat | 440 | 3sat_142.cnf | positive | 1729 | 15 | 1.322 |
| residual_train | 3sat | 440 | 3sat_115.cnf | positive | 1729 | 15 | 1.773 |
| residual_train | 3sat | 440 | 3sat_230.cnf | positive | 1729 | 13 | 5.923 |
| residual_train | 3sat | 440 | 3sat_115.cnf | positive | 1729 | 6 | 8.651 |
| residual_train | 3sat | 440 | 3sat_142.cnf | positive | 1729 | 12 | 14.06 |
| residual_train | 3sat | 440 | 3sat_230.cnf | positive | 1729 | 6 | 18.63 |
| residual_train | 3sat | 425 | 3sat_229.cnf | positive | 1729 | 14 | 19.93 |
| residual_train | 3sat | 440 | 3sat_119.cnf | positive | 1729 | 3 | 34.69 |
| residual_train | 3sat | 440 | 3sat_119.cnf | positive | 1729 | 4 | 36.07 |
| residual_train | 3sat | 425 | 3sat_229.cnf | positive | 1729 | 10 | 38.39 |
| residual_train | 3sat | 410 | 3sat_247.cnf | positive | 1729 | 14 | 54.79 |
| residual_train | 3sat | 410 | 3sat_160.cnf | positive | 1729 | 14 | 54.97 |
| residual_train | 3sat | 425 | 3sat_280.cnf | positive | 1729 | 2 | 55.09 |
| residual_train | 3sat | 410 | 3sat_13.cnf | positive | 1729 | 2 | 55.46 |
| residual_train | 3sat | 410 | 3sat_13.cnf | positive | 1729 | 12 | 55.5 |
| residual_train | 3sat | 425 | 3sat_44.cnf | positive | 1729 | 8 | 55.99 |
| residual_train | 3sat | 425 | 3sat_110.cnf | positive | 1729 | 11 | 56.12 |
| residual_train | 3sat | 425 | 3sat_46.cnf | positive | 1729 | 6 | 56.16 |
