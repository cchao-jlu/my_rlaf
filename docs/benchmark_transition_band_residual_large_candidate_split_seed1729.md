# Candidate Split Manifest

Scope: immutable train/dev/held-out split over the full transition-band
candidate denominator, before March/CaDiCaL residual filtering and before
any neural selector or non-neural rerun schedule tuning.

## Source

- CNF root: `data/benchmark_transition_band_residual_large`
- sizes: `410, 425, 440`
- instances per size: `300`
- generation seed: `2041`
- split seed: `1729`
- train fraction: `0.5`
- dev fraction: `0.25`
- missing CNF files at manifest time: `300`
- manifest sha256: `c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc`

## Split Totals

| split | instances |
| --- | --- |
| candidate_dev | 225 |
| candidate_heldout | 225 |
| candidate_train | 450 |

## Split By Size

| split | size | instances |
| --- | --- | --- |
| candidate_dev | 410 | 75 |
| candidate_dev | 425 | 75 |
| candidate_dev | 440 | 75 |
| candidate_heldout | 410 | 75 |
| candidate_heldout | 425 | 75 |
| candidate_heldout | 440 | 75 |
| candidate_train | 410 | 150 |
| candidate_train | 425 | 150 |
| candidate_train | 440 | 150 |

## Artifacts

```text
runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv
runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_train.csv
runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_dev.csv
runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_heldout.csv
runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json
```
