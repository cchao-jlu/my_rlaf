# Residual Non-Neural Budget Control

Scope: fixed same-budget non-neural rerun portfolio for the residual
March/CaDiCaL both-unknown transition-band set. This is the required
control for the residual neural restart portfolio mainline.

Input CSV: `runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv`.
CNF root: `data/benchmark_transition_band_expanded`.
Input residual instances: 1.
Fixed schedule: march:0.1s, cadical_seed1:0.1s.
Schedule source: `runs/analysis/tmp_non_neural_per_instance_smoke/schedule.csv`.
Budget source: `runs/analysis/tmp_non_neural_per_instance_smoke/synthetic_neural_summary.csv per_instance_total_cpu_allocated`.

Budget enforcement:

- CaDiCaL uses its internal wall-clock limit (`-t`) plus an external timeout.
- CaDiCaL variants can fix seed/config options such as `--seed`, `--plain`,
  `--sat`, `--unsat`, and `--shuffle` through the frozen schedule.
- March has no internal limit in this unweighted binary, so the per-attempt
  budget is enforced by external wall-clock timeout and capped CPU accounting.

## Summary

Solved residual instances: 0 / 1

| family | size | file_key | attempts | budget_cpu_total | used_capped_cpu_total | wall_time_total | solved_any | first_solved_attempt | first_solved_solver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 2 | 0.200 | 0.200 | 5.111 | False | -1 |  |

Artifacts:

```text
runs/analysis/tmp_non_neural_per_instance_smoke/attempts/
runs/analysis/tmp_non_neural_per_instance_smoke/raw_attempts.csv
runs/analysis/tmp_non_neural_per_instance_smoke/instance_summary.csv
runs/analysis/tmp_non_neural_per_instance_smoke/schedule.csv
```
