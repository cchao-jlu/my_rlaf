# Expanded Transition-Band Strong-Solver Gate

Scope: larger strong-solver gate for finding March/CaDiCaL union-unsolved
random 3SAT instances. This is the candidate source for expanded sampled
March guidance experiments.

Sizes: 410, 425, 440; instances per size: 50.

## Solver Summary

| family | size | solver | total | solved | unknown | mean_time | median_time | max_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | cadical | 50 | 27 | 23 | 31.838 | 25.964 | 60.000 |
| 3sat | 410 | march | 50 | 43 | 7 | 27.389 | 26.700 | 60.838 |
| 3sat | 425 | cadical | 50 | 27 | 23 | 33.945 | 40.866 | 60.000 |
| 3sat | 425 | march | 50 | 34 | 16 | 30.597 | 24.064 | 64.031 |
| 3sat | 440 | cadical | 50 | 13 | 37 | 47.045 | 60.000 | 60.000 |
| 3sat | 440 | march | 50 | 19 | 31 | 41.030 | 60.000 | 60.000 |

## March / CaDiCaL Overlap

| family | size | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 50 | 25 | 18 | 2 | 5 | 45 |
| 3sat | 425 | 50 | 25 | 9 | 2 | 14 | 36 |
| 3sat | 440 | 50 | 12 | 7 | 1 | 30 | 20 |

## Both-Unknown Count

Total both-unknown instances: 49

Artifacts:

```text
runs/analysis/benchmark_transition_band_expanded/combined.csv
runs/analysis/benchmark_transition_band_expanded/summary.csv
runs/analysis/benchmark_transition_band_expanded/solver_overlap.csv
runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv
```
