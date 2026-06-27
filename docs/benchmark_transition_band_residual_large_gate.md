# Expanded Transition-Band Strong-Solver Gate

Scope: larger strong-solver gate for finding March/CaDiCaL union-unsolved
random 3SAT instances. This is the candidate source for expanded sampled
March guidance experiments.

Sizes: 410, 425, 440; instances per size: 300.
Data root: `data/benchmark_transition_band_residual_large/3sat`.
Output dir: `runs/analysis/benchmark_transition_band_residual_large`.

## Solver Summary

| family | size | solver | total | solved | solved_after_nominal_limit | unknown | mean_time | median_time | max_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | cadical | 300 | 119 | 0 | 181 | 41.480 | 60.000 | 60.000 |
| 3sat | 410 | march | 300 | 237 | 15 | 63 | 32.915 | 35.579 | 64.829 |
| 3sat | 425 | cadical | 300 | 122 | 0 | 178 | 40.713 | 60.000 | 60.000 |
| 3sat | 425 | march | 300 | 160 | 12 | 140 | 39.913 | 55.416 | 64.483 |
| 3sat | 440 | cadical | 300 | 123 | 0 | 177 | 40.683 | 60.000 | 60.000 |
| 3sat | 440 | march | 300 | 121 | 7 | 179 | 42.438 | 60.000 | 64.774 |

## March / CaDiCaL Overlap

| family | size | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 300 | 119 | 118 | 0 | 63 | 237 |
| 3sat | 425 | 300 | 113 | 47 | 9 | 131 | 169 |
| 3sat | 440 | 300 | 100 | 21 | 23 | 156 | 144 |

## Both-Unknown Count

Total both-unknown instances: 350

Artifacts:

```text
runs/analysis/benchmark_transition_band_residual_large/combined.csv
runs/analysis/benchmark_transition_band_residual_large/summary.csv
runs/analysis/benchmark_transition_band_residual_large/solver_overlap.csv
runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv
```
