# Residual Split Manifest

Scope: immutable train/dev/held-out split for March/CaDiCaL both-unknown
transition-band residual instances. This split is created before selector
thresholds, adaptive budget rules, or non-neural schedules are tuned.

## Source

- input CSV: `runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv`
- input sha256: `b3de5c8119b28058fc706135ae69ffffd4831f293f5f61ca46f2d41fb58b07ee`
- CNF root: `data/benchmark_transition_band_residual_large`
- excluded CSV: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/both_unknown_subset.csv`
- excluded rows: `0`
- exclude mode: `cnf_sha256`
- split seed: `1729`
- train fraction: `0.5`
- dev fraction: `0.25`
- split source: `candidate_manifest`
- candidate manifest: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv`
- candidate manifest sha256: `c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc`
- materialized CNFs: `symlink`

## Split Totals

| split | instances |
| --- | --- |
| residual_dev | 93 |
| residual_heldout | 89 |
| residual_train | 168 |

## Split By Size

| split | size | instances |
| --- | --- | --- |
| residual_dev | 410 | 12 |
| residual_dev | 425 | 35 |
| residual_dev | 440 | 46 |
| residual_heldout | 410 | 16 |
| residual_heldout | 425 | 39 |
| residual_heldout | 440 | 34 |
| residual_train | 410 | 35 |
| residual_train | 425 | 57 |
| residual_train | 440 | 76 |

## Artifacts

```text
runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv
runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv
runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv
runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_heldout.csv
runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/cnf
```
