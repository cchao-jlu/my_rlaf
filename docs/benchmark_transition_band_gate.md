# Transition-Band Strong-Solver Gate

Scope: random 3SAT transition-band gate for benchmark triage. This
generates small fixed sets around the 400-to-450 region and runs March
and CaDiCaL under the nominal 60s / external 65s protocol. It does not
train or tune neural models.

Sizes: 410, 425, 440; instances per size: 12.

## Solver Summary

| family | size | solver | total | solved | unknown | mean_time | median_time | max_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | cadical | 12 | 4 | 8 | 40.754 | 60.000 | 60.000 |
| 3sat | 410 | march | 12 | 9 | 3 | 32.112 | 33.277 | 60.000 |
| 3sat | 425 | cadical | 12 | 9 | 3 | 20.958 | 11.455 | 60.000 |
| 3sat | 425 | march | 12 | 9 | 3 | 29.228 | 20.289 | 63.892 |
| 3sat | 440 | cadical | 12 | 6 | 6 | 40.403 | 57.193 | 60.000 |
| 3sat | 440 | march | 12 | 4 | 8 | 49.480 | 60.000 | 60.000 |

## March / CaDiCaL Overlap

| family | size | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 12 | 4 | 5 | 0 | 3 | 9 |
| 3sat | 425 | 12 | 8 | 1 | 1 | 2 | 10 |
| 3sat | 440 | 12 | 4 | 0 | 2 | 6 | 6 |

## Both-Unknown Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 410 | 3sat_2.cnf |
| 3sat | 410 | 3sat_3.cnf |
| 3sat | 410 | 3sat_8.cnf |
| 3sat | 425 | 3sat_10.cnf |
| 3sat | 425 | 3sat_11.cnf |
| 3sat | 440 | 3sat_0.cnf |
| 3sat | 440 | 3sat_11.cnf |
| 3sat | 440 | 3sat_2.cnf |
| 3sat | 440 | 3sat_7.cnf |
| 3sat | 440 | 3sat_8.cnf |
| 3sat | 440 | 3sat_9.cnf |

## Decision

- This gate found transition-band both-unknown instances while retaining
  nonzero strong-solver solves. The next low-cost check is frozen neural
  triage only on the both-unknown subset.

Generated artifacts:

```text
runs/analysis/benchmark_transition_band/combined.csv
runs/analysis/benchmark_transition_band/summary.csv
runs/analysis/benchmark_transition_band/solver_overlap.csv
runs/analysis/benchmark_transition_band/both_unknown_subset.csv
```
