# 3SAT-450 Strong-Solver Gate

Scope: moderate 3SAT-450 benchmark gate using existing March and CaDiCaL
artifacts under the same nominal 60s protocol. This does not train
neural models, tune selectors, or change solver code.

Inputs:

```text
data/benchmark_3sat450_gate/3sat/450/*.cnf
runs/analysis/benchmark_3sat450_gate/raw/march_repeat0.csv
runs/analysis/benchmark_3sat450_gate/raw/march_repeat1.csv
runs/analysis/benchmark_3sat450_gate/raw/march_repeat2.csv
runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat0.csv
runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat1.csv
runs/analysis/benchmark_3sat450_gate/raw/cadical_repeat2.csv
```

## Solver Summary

| solver | repeat | total | solved | unknown | mean_time | median_time | max_time | external_timeouts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cadical | 0 | 24 | 11 | 13 | 38.994 | 60.000 | 60.000 | 0 |
| cadical | 1 | 24 | 11 | 13 | 38.974 | 60.000 | 60.000 | 0 |
| cadical | 2 | 24 | 11 | 13 | 38.951 | 60.000 | 60.000 | 0 |
| march | 0 | 24 | 6 | 18 | 46.196 | 60.000 | 60.000 | 18 |
| march | 1 | 24 | 6 | 18 | 46.198 | 60.000 | 60.000 | 18 |
| march | 2 | 24 | 6 | 18 | 46.209 | 60.000 | 60.000 | 18 |

## March / CaDiCaL Overlap By Repeat

| repeat | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 24 | 6 | 0 | 5 | 13 | 11 |
| 1 | 24 | 6 | 0 | 5 | 13 | 11 |
| 2 | 24 | 6 | 0 | 5 | 13 | 11 |

## Stable March / CaDiCaL Overlap

| repeats | total | both_solved_any | march_only_any | cadical_only_any | both_unsolved_all | union_solved_any |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | 24 | 6 | 0 | 5 | 13 | 11 |

## Strong-Solver-Hard Subset

| file_key | cadical | march |
| --- | --- | --- |
| 3sat_0.cnf | False | False |
| 3sat_1.cnf | False | False |
| 3sat_11.cnf | False | False |
| 3sat_15.cnf | False | False |
| 3sat_16.cnf | False | False |
| 3sat_17.cnf | False | False |
| 3sat_2.cnf | False | False |
| 3sat_20.cnf | False | False |
| 3sat_23.cnf | False | False |
| 3sat_4.cnf | False | False |
| 3sat_6.cnf | False | False |
| 3sat_8.cnf | False | False |
| 3sat_9.cnf | False | False |

## Decision

- 3SAT-450 remains nontrivial beyond the 8-instance smoke: March and
  CaDiCaL both leave a nonempty hard subset under the 60s gate.
- This gate currently has 3 repeat(s). The repeated
  March/CaDiCaL solved patterns are stable in the current run.
- The frozen neural workflow has now been evaluated on the repeated
  strong-solver-hard subset; see `docs/benchmark_3sat450_neural_gate.md`.
  It solves 0/13 with One-shot and 0/13 with Online-Consistent Selector
  across seeds 1/2/3, so this subset does not support a frozen-neural
  complementarity claim.

Generated artifacts:

```text
runs/analysis/benchmark_3sat450_gate/combined.csv
runs/analysis/benchmark_3sat450_gate/summary.csv
runs/analysis/benchmark_3sat450_gate/solver_overlap_by_repeat.csv
runs/analysis/benchmark_3sat450_gate/solver_overlap_stable.csv
runs/analysis/benchmark_3sat450_gate/solver_instance_repeats.csv
runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv
```
