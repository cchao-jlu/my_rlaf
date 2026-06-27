# March-Guided Transition-Band Triage

Scope: frozen March-trained one-shot guidance on transition-band
instances that unguided March and CaDiCaL both left unsolved. This
uses the existing `runs/GNN_March_3SAT/best.pt` checkpoint and
`solvers/march_weighted/march_nh`; it does not train or tune models.

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
| 3sat | 410 | March-Guided One-shot | 3 | 0.000 | 0 | 0 | 60.153 |
| 3sat | 425 | March-Guided One-shot | 3 | 0.000 | 0 | 0 | 60.146 |
| 3sat | 440 | March-Guided One-shot | 3 | 0.000 | 0 | 0 | 60.281 |

## Strict Complement Summary

Solved means solved in all requested seeds.

| family | size | n | strict_solved |
| --- | --- | --- | --- |
| 3sat | 410 | 3 | 0 |
| 3sat | 425 | 2 | 0 |
| 3sat | 440 | 6 | 0 |

## Decision

- Frozen March-guided one-shot solves no transition-band instance that
  unguided March and CaDiCaL both left unsolved.
- Existing March-guided artifacts therefore do not rescue the current
  performance/complementarity route.

Generated artifacts:

```text
runs/analysis/benchmark_march_guidance_transition_triage/both_unknown_subset.csv
runs/analysis/benchmark_march_guidance_transition_triage/combined.csv
runs/analysis/benchmark_march_guidance_transition_triage/summary.csv
runs/analysis/benchmark_march_guidance_transition_triage/overlap.csv
```
