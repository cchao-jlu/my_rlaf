# CaDiCaL / Neural Portfolio Feasibility Audit

Scope: decision audit only. This does not run new solvers and does not
modify the neural model, selector, thresholds, or Local Boundary Correction.
It asks whether the observed CaDiCaL/neural complementarity can support a
portfolio-style top-conference claim.

Inputs:

```text
runs/analysis/cadical_neural_overlap/combined.csv
```

Important limitation: neural times are 3-seed means from the full400 seed
robustness table, while CaDiCaL is a single 60s run. Sequential schedules
are simulated from full-budget observed times by treating a method as solved
within a sub-budget only when its observed solve time is within that
sub-budget. This is suitable for deciding whether a portfolio claim is worth
a real run, not for replacing a real portfolio experiment.

## Single-Method Reference

| paper_name | solved | actual_mean_time | capped_mean_time |
| --- | --- | --- | --- |
| One-shot | 48 | 47.665 | 47.434 |
| Online-Consistent Selector | 53 | 46.324 | 46.036 |
| Old Compact | 54 | 46.278 | 45.994 |
| + Local Boundary Correction | 54 | 45.914 | 45.632 |
| CaDiCaL | 75 | 42.924 | 42.924 |

## Parallel Two-Core Oracle Portfolio With CaDiCaL

This table starts CaDiCaL and the neural workflow together and takes the
first solver to finish. It is a two-core oracle portfolio, not a same-core
runtime result.

| paper_name | parallel_union_solved | method_only | cadical_only | parallel_mean_time | gain_vs_cadical_solved |
| --- | --- | --- | --- | --- | --- |
| One-shot | 79 | 4 | 31 | 40.902 | 4 |
| Online-Consistent Selector | 79 | 4 | 26 | 40.461 | 4 |
| Old Compact | 80 | 5 | 26 | 40.545 | 5 |
| + Local Boundary Correction | 80 | 5 | 26 | 40.320 | 5 |

## Best Simulated Same-Core Split Schedules

These schedules keep a 60s total budget and split it between CaDiCaL and
a neural workflow. They are conservative simulations from observed full-run
times, not interrupted solver measurements.

| first_name | second_name | first_cap | second_cap | solved | mean_time |
| --- | --- | --- | --- | --- | --- |
| + Local Boundary Correction | CaDiCaL | 5.000 | 55.000 | 77 | 42.507 |
| Online-Consistent Selector | CaDiCaL | 5.000 | 55.000 | 77 | 42.536 |
| CaDiCaL | Online-Consistent Selector | 55.000 | 5.000 | 77 | 42.893 |
| CaDiCaL | + Local Boundary Correction | 55.000 | 5.000 | 77 | 42.893 |
| CaDiCaL | Online-Consistent Selector | 50.000 | 10.000 | 76 | 42.864 |
| CaDiCaL | + Local Boundary Correction | 50.000 | 10.000 | 76 | 42.865 |
| + Local Boundary Correction | CaDiCaL | 10.000 | 50.000 | 76 | 42.932 |
| Online-Consistent Selector | CaDiCaL | 10.000 | 50.000 | 76 | 42.983 |
| CaDiCaL | Online-Consistent Selector | 40.000 | 20.000 | 73 | 42.972 |
| CaDiCaL | + Local Boundary Correction | 40.000 | 20.000 | 73 | 42.974 |
| CaDiCaL | Online-Consistent Selector | 45.000 | 15.000 | 73 | 43.009 |
| CaDiCaL | + Local Boundary Correction | 45.000 | 15.000 | 73 | 43.010 |

## Local-Only Instances Against CaDiCaL

| file_key | one_shot_solved | online_solved | old_compact_solved | local_correction_solved | local_correction_time_mean | cadical_time | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_132.cnf | True | True | True | True | 0.471 | 60.000 | 1111 |
| 3sat_140.cnf | True | True | True | True | 5.465 | 60.000 | 1111 |
| 3sat_147.cnf | True | True | True | True | 13.594 | 60.000 | 1111 |
| 3sat_188.cnf | False | False | True | True | 31.987 | 60.000 | 0011 |
| 3sat_25.cnf | True | True | True | True | 1.556 | 60.000 | 1111 |

## Decision

- The strongest two-core oracle pair is + Local Boundary Correction + CaDiCaL with 80/200 solved.
- CaDiCaL + Local Boundary Correction reaches 80/200 solved, gaining 5 instances over CaDiCaL alone, but 26 CaDiCaL-only instances remain.
- The best simulated same-core 60s split solves 77/200 (+ Local Boundary Correction for 5s, then CaDiCaL for 55s), which is 2 above CaDiCaL alone.
- Therefore the current evidence supports a concrete portfolio follow-up:
  the simulated same-core split has a small but nonzero solved-count gain,
  and the two-core oracle portfolio has a larger complementarity upper bound.
- For a top-conference performance paper, this still requires a real
  interrupted schedule run. The current audit is strong enough to justify
  that experiment, but not to replace it.

Generated artifacts:

```text
runs/analysis/cadical_portfolio_feasibility/single_method_summary.csv
runs/analysis/cadical_portfolio_feasibility/parallel_portfolio_summary.csv
runs/analysis/cadical_portfolio_feasibility/parallel_portfolio_per_instance.csv
runs/analysis/cadical_portfolio_feasibility/sequential_split_schedule_summary.csv
runs/analysis/cadical_portfolio_feasibility/best_sequential_split_schedules.csv
runs/analysis/cadical_portfolio_feasibility/local_only_instances.csv
```
