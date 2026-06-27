# Expanded Transition-Band Strong-Solver Gate

Scope: larger strong-solver gate for finding March/CaDiCaL union-unsolved
random 3SAT instances. This is the candidate source for expanded sampled
March guidance experiments.

Sizes: 410, 425, 440; instances per size: 50.
Data root: `data/benchmark_transition_band_expanded/3sat`.
Output dir: `runs/analysis/benchmark_transition_band_expanded_strict60_smoke`.

## Solver Summary

| family | size | solver | total | solved | solved_after_nominal_limit | unknown | mean_time | median_time | max_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | cadical | 50 | 27 | 0 | 23 | 31.838 | 25.964 | 60.000 |
| 3sat | 410 | march | 50 | 42 | 1 | 8 | 27.389 | 26.700 | 60.838 |
| 3sat | 425 | cadical | 50 | 27 | 0 | 23 | 33.945 | 40.866 | 60.000 |
| 3sat | 425 | march | 50 | 31 | 3 | 19 | 30.597 | 24.064 | 64.031 |
| 3sat | 440 | cadical | 50 | 13 | 0 | 37 | 47.045 | 60.000 | 60.000 |
| 3sat | 440 | march | 50 | 19 | 0 | 31 | 41.030 | 60.000 | 60.000 |

## March / CaDiCaL Overlap

| family | size | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 50 | 25 | 17 | 2 | 6 | 44 |
| 3sat | 425 | 50 | 24 | 7 | 3 | 16 | 34 |
| 3sat | 440 | 50 | 12 | 7 | 1 | 30 | 20 |

## Both-Unknown Count

Total both-unknown instances: 52

Artifacts:

```text
runs/analysis/benchmark_transition_band_expanded_strict60_smoke/combined.csv
runs/analysis/benchmark_transition_band_expanded_strict60_smoke/summary.csv
runs/analysis/benchmark_transition_band_expanded_strict60_smoke/solver_overlap.csv
runs/analysis/benchmark_transition_band_expanded_strict60_smoke/both_unknown_subset.csv
```
