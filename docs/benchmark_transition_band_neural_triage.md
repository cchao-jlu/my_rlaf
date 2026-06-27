# Transition-Band Frozen-Neural Triage

Scope: frozen neural triage on random 3SAT transition-band instances
that March and CaDiCaL both left unsolved in the first strong-solver
gate. This does not train models, tune thresholds, or migrate Local
Boundary Correction.

## Both-Unknown Input Subset

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

## Method Summary

| family | size | paper_name | seeds | solved_mean | solved_min | solved_max | mean_time_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | One-shot | 3 | 0.000 | 0 | 0 | 60.126 |
| 3sat | 410 | Online-Consistent Selector | 3 | 0.000 | 0 | 0 | 60.187 |
| 3sat | 425 | One-shot | 3 | 0.000 | 0 | 0 | 60.094 |
| 3sat | 425 | Online-Consistent Selector | 3 | 0.000 | 0 | 0 | 60.186 |
| 3sat | 440 | One-shot | 3 | 0.000 | 0 | 0 | 60.232 |
| 3sat | 440 | Online-Consistent Selector | 3 | 0.000 | 0 | 0 | 60.309 |

## Strict Complement Summary

Solved means solved in all requested neural seeds. Pattern order is `One-shot / Online-Consistent Selector`.

| family | size | n | one_shot_strict | online_strict | online_only_strict |
| --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3 | 0 | 0 | 0 |
| 3sat | 425 | 2 | 0 | 0 | 0 |
| 3sat | 440 | 6 | 0 | 0 | 0 |

## Pattern Counts

| family | size | pattern | count |
| --- | --- | --- | --- |
| 3sat | 410 | 00 | 3 |
| 3sat | 425 | 00 | 2 |
| 3sat | 440 | 00 | 6 |

## Decision

- Frozen Online-Consistent guidance solves no transition-band instance
  that March and CaDiCaL both left unsolved.
- This further weakens the current frozen-workflow performance route.

Generated artifacts:

```text
runs/analysis/benchmark_transition_band_neural_triage/both_unknown_subset.csv
runs/analysis/benchmark_transition_band_neural_triage/combined.csv
runs/analysis/benchmark_transition_band_neural_triage/summary.csv
runs/analysis/benchmark_transition_band_neural_triage/overlap.csv
```
