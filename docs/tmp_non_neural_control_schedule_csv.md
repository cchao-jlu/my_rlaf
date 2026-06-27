# Residual Non-Neural Budget Control

Scope: fixed same-budget non-neural rerun portfolio for the residual
March/CaDiCaL both-unknown transition-band set. This is the required
control for the residual neural restart portfolio mainline.

Input CSV: `runs/analysis/tmp_non_neural_control_schedule_csv/residual.csv`.
CNF root: `data/benchmark_transition_band_expanded`.
Input residual instances: 1.
Fixed schedule: march:60s, cadical:60s, march:60s, cadical:60s, march:60s, cadical:60s, march:60s, cadical:60s, march:16s.
Schedule source: `runs/analysis/tmp_residual_audit_smoke/non_neural_schedule_from_dev.csv`.

Budget enforcement:

- CaDiCaL uses its internal wall-clock limit (`-t`) plus an external timeout.
- March has no internal limit in this unweighted binary, so the per-attempt
  budget is enforced by external wall-clock timeout and capped CPU accounting.

## Summary

Solved residual instances: 0 / 1

| family | size | file_key | attempts | budget_cpu_total | used_capped_cpu_total | wall_time_total | solved_any | first_solved_attempt | first_solved_solver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | a.cnf | 9 | 496.000 | 496.000 | 496.000 | False | -1 |  |

Artifacts:

```text
runs/analysis/tmp_non_neural_control_schedule_csv/attempts/
runs/analysis/tmp_non_neural_control_schedule_csv/raw_attempts.csv
runs/analysis/tmp_non_neural_control_schedule_csv/instance_summary.csv
runs/analysis/tmp_non_neural_control_schedule_csv/schedule.csv
```
