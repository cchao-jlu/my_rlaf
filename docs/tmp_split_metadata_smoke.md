# Residual Split Manifest

Scope: immutable train/dev/held-out split for March/CaDiCaL both-unknown
transition-band residual instances. This split is created before selector
thresholds, adaptive budget rules, or non-neural schedules are tuned.

## Source

- input CSV: `runs/analysis/tmp_split_metadata_smoke/both_unknown_subset.csv`
- input sha256: `8ba127c079b4c0fa1927fede2c7feb14c7622eab7dc866603b181bcbc63c5bb7`
- CNF root: `runs/analysis/tmp_split_metadata_smoke/cnf`
- excluded CSV: `runs/analysis/tmp_split_metadata_smoke/exclude.csv`
- excluded rows: `1`
- split seed: `1729`
- train fraction: `0.34`
- dev fraction: `0.33`
- materialized CNFs: `symlink`

## Split Totals

| split | instances |
| --- | --- |
| residual_dev | 1 |
| residual_heldout | 1 |
| residual_train | 1 |

## Split By Size

| split | size | instances |
| --- | --- | --- |
| residual_dev | 410 | 1 |
| residual_heldout | 410 | 1 |
| residual_train | 410 | 1 |

## Artifacts

```text
runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/manifest.csv
runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/residual_train.csv
runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/residual_dev.csv
runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/residual_heldout.csv
runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/cnf
```
