# 3SAT-450 Neural Gate on Strong-Solver-Hard Subset

Scope: frozen neural workflow gate only. This evaluates One-shot and
Online-Consistent Selector on the 13 instances that repeated March and
CaDiCaL both failed to solve in `docs/benchmark_3sat450_gate.md`.
It does not train models, tune thresholds, or migrate Local Boundary
Correction to 450.

Inputs:

```text
runs/analysis/benchmark_3sat450_gate/strong_solver_hard_subset.csv
data/benchmark_3sat450_gate/strong_hard/3sat/450/*.cnf
```

## Method Summary

| paper_name | seeds | solved_mean | solved_std | solved_min | solved_max | mean_time_mean | mean_time_std |
| --- | --- | --- | --- | --- | --- | --- | --- |
| One-shot | 3 | 0.000 | 0.000 | 0 | 0 | 60.280 | 0.010 |
| Online-Consistent Selector | 3 | 0.000 | 0.000 | 0 | 0 | 60.363 | 0.004 |

## Per-Seed Summary

| paper_name | seed | n | solved | unknown | mean_time | median_time |
| --- | --- | --- | --- | --- | --- | --- |
| One-shot | 1 | 13 | 0 | 13 | 60.267 | 60.321 |
| Online-Consistent Selector | 1 | 13 | 0 | 13 | 60.363 | 60.421 |
| One-shot | 2 | 13 | 0 | 13 | 60.283 | 60.338 |
| Online-Consistent Selector | 2 | 13 | 0 | 13 | 60.368 | 60.428 |
| One-shot | 3 | 13 | 0 | 13 | 60.291 | 60.354 |
| Online-Consistent Selector | 3 | 13 | 0 | 13 | 60.358 | 60.413 |

## Solved Pattern Summary

Pattern order: `One-shot / Online-Consistent Selector`; solved means solved in all requested seeds.

| pattern | count |
| --- | --- |
| 00 | 13 |

## Strict Neural Complement on March+CaDiCaL-Hard Instances

- Strong-solver-hard subset size: 13.
- One-shot solved in all seeds: 0.
- Online-Consistent solved in all seeds: 0.
- Online-only over One-shot in all seeds: 0.

## Decision

- Frozen Online-Consistent guidance does not solve any repeated
  March+CaDiCaL-hard 3SAT-450 instance in this gate.
- The current frozen workflow should not be positioned as a strong
  performance/complementarity result without new benchmark evidence.

Generated artifacts:

```text
runs/analysis/benchmark_3sat450_neural_gate/combined.csv
runs/analysis/benchmark_3sat450_neural_gate/seed_summary.csv
runs/analysis/benchmark_3sat450_neural_gate/method_summary.csv
runs/analysis/benchmark_3sat450_neural_gate/strong_hard_neural_overlap.csv
```
