# CaDiCaL Full400 Repeat Stability

Scope: repeat standalone CaDiCaL 60s on full400 to audit whether the
portfolio advantage and portfolio-only claim split are stable against
CaDiCaL runtime variance. This does not modify any neural model, selector,
threshold, or portfolio schedule.

Inputs:

```text
runs/cadical/solver_stats_full400_cpu60.csv
runs/cadical/solver_stats_full400_cpu60_repeat1.csv
runs/cadical/solver_stats_full400_cpu60_repeat2.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv
runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv
```

## CaDiCaL Repeat Summary

| repeat | cadical_solved | unknown | mean_time | median_time | external_timeouts |
| --- | --- | --- | --- | --- | --- |
| 0 | 75 | 125 | 42.924 | 60.000 | 0 |
| 1 | 80 | 120 | 41.718 | 60.000 | 0 |
| 2 | 80 | 120 | 41.696 | 60.000 | 0 |

## Matched Portfolio Delta

| repeat | portfolio_solved | cadical_solved | delta_vs_same_repeat_cadical | local_first_stage_solved | cadical_second_stage_solved | cadical_only_vs_portfolio |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 79 | 75 | 4 | 40 | 39 | 0 |
| 1 | 80 | 80 | 0 | 40 | 40 | 0 |
| 2 | 80 | 80 | 0 | 40 | 40 | 0 |

## Key Boundary Audit

| file_key | cadical_solved_repeats | cadical_results | cadical_time_min | cadical_time_max | previous_claim_class |
| --- | --- | --- | --- | --- | --- |
| 3sat_111.cnf | 2 | UNKNOWN,SATISFIABLE,SATISFIABLE | 52.633 | 60 | stable_second_stage_runtime_boundary |
| 3sat_132.cnf | 2 | UNKNOWN,SATISFIABLE,SATISFIABLE | 54.033 | 60 | stable_neural_first_complement |
| 3sat_140.cnf | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 60 | 60 | stable_neural_first_complement |
| 3sat_25.cnf | 2 | UNKNOWN,SATISFIABLE,SATISFIABLE | 49.359 | 60 | stable_neural_first_complement |
| 3sat_48.cnf | 2 | UNKNOWN,SATISFIABLE,SATISFIABLE | 54.630 | 60 | unstable_second_stage_runtime_boundary |

## Decision

- Standalone CaDiCaL 60s is not a fixed 75/200 baseline under repeated
  wall-clock runs; repeats solve 75, 80, 80 instances.
- Against matched same-repeat CaDiCaL counts, the portfolio deltas are
  +4, +0, +0. The +4/+5 claim versus the original single CaDiCaL run
  is not repeated-baseline robust and should be demoted.
- Previously strict neural-first complement is weakened by CaDiCaL repeat
  variance: `3sat_132.cnf` and `3sat_25.cnf` are solved by CaDiCaL in
  repeat1 and repeat2. The repeated-baseline strict neural-first
  complement count is 1.
- `3sat_111.cnf` and `3sat_48.cnf` are confirmed CaDiCaL runtime-boundary
  cases: both are solved by repeated standalone CaDiCaL 60s runs.
- Paper wording must distinguish the original CaDiCaL-run comparison
  from matched repeated-CaDiCaL robustness.

Generated artifacts:

```text
runs/analysis/cadical_repeat_stability/repeat_summary.csv
runs/analysis/cadical_repeat_stability/aggregate.csv
runs/analysis/cadical_repeat_stability/instance_summary.csv
runs/analysis/cadical_repeat_stability/unstable_instances.csv
runs/analysis/cadical_repeat_stability/portfolio_vs_cadical_repeats.csv
runs/analysis/cadical_repeat_stability/key_boundary_audit.csv
```
