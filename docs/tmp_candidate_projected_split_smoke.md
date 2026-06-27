# Residual Split Manifest

Scope: immutable train/dev/held-out split for March/CaDiCaL both-unknown
transition-band residual instances. This split is created before selector
thresholds, adaptive budget rules, or non-neural schedules are tuned.

## Source

- input CSV: `runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv`
- input sha256: `7291d6c2a148ddf6965cbebb446bc52bfd3a7473d32ae9375f5a8050ab76b15c`
- CNF root: `data/benchmark_transition_band_expanded`
- excluded CSV: `none`
- excluded rows: `0`
- exclude mode: `none`
- split seed: `1729`
- train fraction: `0.5`
- dev fraction: `0.25`
- split source: `candidate_manifest`
- candidate manifest: `runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv`
- candidate manifest sha256: `c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc`
- materialized CNFs: `none`

## Split Totals

| split | instances |
| --- | --- |
| residual_dev | 11 |
| residual_heldout | 13 |
| residual_train | 25 |

## Split By Size

| split | size | instances |
| --- | --- | --- |
| residual_dev | 425 | 3 |
| residual_dev | 440 | 8 |
| residual_heldout | 410 | 2 |
| residual_heldout | 425 | 4 |
| residual_heldout | 440 | 7 |
| residual_train | 410 | 3 |
| residual_train | 425 | 7 |
| residual_train | 440 | 15 |

## Artifacts

```text
runs/analysis/tmp_candidate_projected_split_smoke/manifest.csv
runs/analysis/tmp_candidate_projected_split_smoke/residual_train.csv
runs/analysis/tmp_candidate_projected_split_smoke/residual_dev.csv
runs/analysis/tmp_candidate_projected_split_smoke/residual_heldout.csv
runs/analysis/tmp_candidate_projected_split_smoke/cnf
```
