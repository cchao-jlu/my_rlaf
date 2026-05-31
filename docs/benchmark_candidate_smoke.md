# Benchmark Candidate Smoke

Scope: search for candidate benchmark regimes where the current strong
solver artifacts are not trivially dominant. This is a small smoke gate
only. It does not train neural models, change selectors, or tune thresholds.

Generated candidates:

```text
data/benchmark_candidates/3sat/450/*.cnf
data/benchmark_candidates/3sat/500/*.cnf
data/benchmark_candidates/coloring/400/*.cnf
data/benchmark_candidates/coloring/500/*.cnf
```

## Solver Summary

| family | size | solver | total | solved | unknown | mean_time | median_time | max_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 450 | cadical | 8 | 5 | 3 | 28.651 | 14.709 | 60.000 |
| 3sat | 450 | march | 8 | 2 | 6 | 46.052 | 60.000 | 60.000 |
| 3sat | 500 | cadical | 8 | 1 | 7 | 53.201 | 60.000 | 60.000 |
| 3sat | 500 | march | 8 | 2 | 6 | 50.718 | 60.000 | 60.000 |
| coloring | 400 | cadical | 8 | 8 | 0 | 0.866 | 0.528 | 2.215 |
| coloring | 400 | march | 8 | 8 | 0 | 1.839 | 1.007 | 4.849 |
| coloring | 500 | cadical | 8 | 8 | 0 | 8.194 | 2.555 | 37.689 |
| coloring | 500 | march | 8 | 7 | 1 | 11.391 | 3.338 | 60.000 |

## March / CaDiCaL Overlap

| family | size | total | both_solved | march_only | cadical_only | both_unknown | union_solved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 450 | 8 | 2 | 0 | 3 | 3 | 5 |
| 3sat | 500 | 8 | 1 | 1 | 0 | 6 | 2 |
| coloring | 400 | 8 | 8 | 0 | 0 | 0 | 8 |
| coloring | 500 | 8 | 7 | 0 | 1 | 0 | 8 |

## Decision

- Coloring 400 is too easy for both solver families in this smoke gate.
- Coloring 500 creates one March timeout, but CaDiCaL solves all 8 smoke
  instances; this is a solver-family difference, not a strong-solver-hard
  benchmark.
- Random 3SAT-450 is the first useful candidate: March solves 2/8,
  CaDiCaL solves 5/8, and 3 instances are unsolved by both within the
  60s gate. This is a plausible next benchmark-regime probe.
- Random 3SAT-500 is harder: March solves 2/8 and CaDiCaL solves 1/8.
  It may be too hard for the current neural workflow, but it is useful
  as a strong-solver-hard stress test.
- The next top-conference-oriented experiment should not tune selectors.
  It should generate a moderate 3SAT-450 candidate set, run March and
  CaDiCaL repeats, then test whether the frozen neural workflow solves
  any repeated-strong-solver-hard instances.

Generated artifacts:

```text
runs/analysis/benchmark_candidate_smoke/combined.csv
runs/analysis/benchmark_candidate_smoke/summary.csv
runs/analysis/benchmark_candidate_smoke/solver_overlap.csv
```
