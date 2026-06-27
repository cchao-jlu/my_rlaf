# Residual Contrastive Replay Manifest

This manifest contains solved sampled-March restarts and same-CNF failed
samples for model-side contrastive residual-policy training. It is a
training artifact, not an oracle-selector result.

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- split csv: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv`
- max positives per instance: `2`
- max negatives per instance: `4`
- negative selection: `low_progress`
- min positive instances: `4`
- require raw complete: `True`
- expected sample seeds: `1729`
- expected num samples: `16`
- manifest rows: `30`
- positive instances: `6`
- contrastive groups: `6`

## Raw Sources

| source_raw_csv | source_raw_sha256 |
| --- | --- |
| /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv | d4bba8eb74b68554739ed41fc89ed7eecb808b6df72e779fb4043045ecb1deb2 |

## Role Summary

| split | family | size | sample_role | rows | instances |
| --- | --- | --- | --- | --- | --- |
| residual_dev | 3sat | 410 | negative | 5 | 2 |
| residual_dev | 3sat | 410 | positive | 3 | 2 |
| residual_dev | 3sat | 440 | negative | 16 | 4 |
| residual_dev | 3sat | 440 | positive | 6 | 4 |

## Selected Samples

| split | family | size | file_key | sample_role | sample_seed | sample_id | CPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| residual_dev | 3sat | 440 | 3sat_293.cnf | positive | 1729 | 15 | 3.443 |
| residual_dev | 3sat | 440 | 3sat_234.cnf | positive | 1729 | 7 | 11.46 |
| residual_dev | 3sat | 440 | 3sat_293.cnf | positive | 1729 | 4 | 19.65 |
| residual_dev | 3sat | 440 | 3sat_279.cnf | positive | 1729 | 4 | 32.7 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | positive | 1729 | 12 | 54.89 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | positive | 1729 | 0 | 56.53 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | positive | 1729 | 0 | 59.4 |
| residual_dev | 3sat | 410 | 3sat_30.cnf | positive | 1729 | 8 | 59.42 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | positive | 1729 | 6 | 59.68 |
| residual_dev | 3sat | 410 | 3sat_30.cnf | negative | 1729 | 10 | 60 |
| residual_dev | 3sat | 410 | 3sat_30.cnf | negative | 1729 | 3 | 60 |
| residual_dev | 3sat | 410 | 3sat_30.cnf | negative | 1729 | 0 | 60 |
| residual_dev | 3sat | 410 | 3sat_78.cnf | negative | 1729 | 5 | 60 |
| residual_dev | 3sat | 440 | 3sat_234.cnf | negative | 1729 | 6 | 60 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | negative | 1729 | 13 | 60 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | negative | 1729 | 5 | 60 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | negative | 1729 | 3 | 60 |
| residual_dev | 3sat | 440 | 3sat_249.cnf | negative | 1729 | 2 | 60 |
| residual_dev | 3sat | 440 | 3sat_279.cnf | negative | 1729 | 9 | 60 |
| residual_dev | 3sat | 440 | 3sat_279.cnf | negative | 1729 | 1 | 60 |
