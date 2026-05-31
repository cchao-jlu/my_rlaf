# Failure-Boundary Solved-Set Lattice Audit

Scope: quantify where the current neural-guided Glucose workflow sits
relative to Glucose default, CaDiCaL repeats, March strict-60 repeats,
and the Local5 -> CaDiCaL55 portfolio. This is an analysis artifact only;
it does not change models, thresholds, selectors, or solver configs.

## Method Counts

| method | solved |
| --- | --- |
| Glucose default | 13 |
| One-shot | 48 |
| Online-Consistent Selector | 53 |
| Old Compact | 54 |
| + Local Boundary Correction | 54 |
| CaDiCaL any-repeat | 80 |
| CaDiCaL all-repeat | 75 |
| March strict-60 all-repeat | 184 |
| Local5 -> CaDiCaL55 any-repeat | 80 |
| Local5 -> CaDiCaL55 all-repeat | 79 |

## Pairwise Containment

| comparison | left_solved | right_solved | left_only | right_only | both | union |
| --- | --- | --- | --- | --- | --- | --- |
| Online vs One-shot | 53 | 48 | 5 | 0 | 48 | 53 |
| Local vs Online | 54 | 53 | 1 | 0 | 53 | 54 |
| Local vs Glucose | 54 | 13 | 42 | 1 | 12 | 55 |
| Local vs CaDiCaL-all | 54 | 75 | 5 | 26 | 49 | 80 |
| Local vs March-all | 54 | 184 | 0 | 130 | 54 | 184 |
| Online vs March-all | 53 | 184 | 0 | 131 | 53 | 184 |
| CaDiCaL-all vs March-all | 75 | 184 | 0 | 109 | 75 | 184 |
| Portfolio-all vs March-all | 79 | 184 | 0 | 105 | 79 | 184 |

## Key Boundary Sets

- Online recovers 5 One-shot timeouts; all are solved by March strict-60 all-repeat and CaDiCaL all-repeat.
- Local Boundary Correction has 1 Local-only gain over Online: `3sat_188.cnf`; March solves it in all strict-60 repeats.
- Glucose default has 1 instance solved that Local does not solve.
- Local has 0 solved instance outside repeated March strict-60.
- Repeated March strict-hard has 16 instances; current neural, CaDiCaL, and portfolio methods solve none of them.

## Decision

- The Online-Consistent Selector and Local Boundary Correction form a real
  improvement inside the neural-guided Glucose workflow: Online strictly
  contains One-shot, and Local strictly contains Online by one boundary
  instance.
- That improvement does not transfer into strong-solver complementarity.
  Both Online and Local are strict subsets of repeated March strict-60.
- The defensible top-conference story is therefore a solved-set boundary
  and risk-control study: when neural feedback helps a weak/medium
  neural-guided workflow, and where it is completely dominated by a
  stronger solver family.
- A performance route requires a new benchmark protocol or an external
  stronger-solver gate showing stable neural solves outside the stronger
  solver's repeated solved set.

Generated artifacts:

```text
runs/analysis/failure_boundary_lattice/combined.csv
runs/analysis/failure_boundary_lattice/method_summary.csv
runs/analysis/failure_boundary_lattice/pair_summary.csv
runs/analysis/failure_boundary_lattice/online_recovered_from_oneshot.csv
runs/analysis/failure_boundary_lattice/local_only_over_online.csv
runs/analysis/failure_boundary_lattice/glucose_only_vs_local.csv
runs/analysis/failure_boundary_lattice/local_only_vs_march.csv
runs/analysis/failure_boundary_lattice/march_strict_hard.csv
```
