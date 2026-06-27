# Residual Non-Neural Budget Control

Scope: fixed same-budget non-neural rerun portfolio for the residual
March/CaDiCaL both-unknown transition-band set. This is the required
control for the residual neural restart portfolio mainline.

Input residual instances: 1.
Fixed schedule: cadical:0.1s.

This file currently records a smoke test of the runner, not a paper result.
The formal pilot/control run must overwrite it with a pre-registered
same-budget schedule, for example with `--force` after the schedule is frozen.

## Summary

Solved residual instances: 0 / 1

| family | size | file_key | attempts | budget_cpu_total | used_capped_cpu_total | wall_time_total | solved_any | first_solved_attempt | first_solved_solver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 1 | 0.100 | 0.100 | 0.004 | False | -1 |  |

Artifacts:

```text
runs/analysis/benchmark_residual_non_neural_budget_control/attempts/
runs/analysis/benchmark_residual_non_neural_budget_control/raw_attempts.csv
runs/analysis/benchmark_residual_non_neural_budget_control/instance_summary.csv
runs/analysis/benchmark_residual_non_neural_budget_control/schedule.csv
```
