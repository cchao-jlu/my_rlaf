# End-to-End Local-5s / CaDiCaL-55s Portfolio Smoke

Mode: `smoke`.

This runner loads the Local Boundary Correction checkpoint once, then
executes the Local workflow per instance under a 5s wall-clock budget.
Warmup and final weighted-Glucose calls are externally capped by the
remaining first-stage budget. Unsolved instances are then sent to
CaDiCaL for 55s.

This is a smoke artifact, not the final full400 table.

## Summary

| Metric | Value |
| --- | ---: |
| instances | 8 |
| portfolio solved | 4 |
| Local first-stage solved | 2 |
| CaDiCaL second-stage solved | 2 |
| Local errors | 0 |

## Per Instance

| file_key | local_result | local_wall_time | local_stage | cadical_result | portfolio_solved | portfolio_time |
| --- | --- | ---: | --- | --- | --- | ---: |
| 3sat_25.cnf | SATISFIABLE | 1.233 | final |  | True | 1.233 |
| 3sat_132.cnf | SATISFIABLE | 0.354 | final |  | True | 0.354 |
| 3sat_111.cnf | TIMEOUT | 5.000 | final | SATISFIABLE | True | 59.129 |
| 3sat_48.cnf | TIMEOUT | 5.000 | final | UNKNOWN | False | 60.000 |
| 3sat_10.cnf | TIMEOUT | 5.000 | final | SATISFIABLE | True | 5.495 |
| 3sat_188.cnf | TIMEOUT | 5.000 | final | UNKNOWN | False | 60.000 |
| 3sat_66.cnf | TIMEOUT | 5.000 | final | UNKNOWN | False | 60.000 |
| 3sat_0.cnf | TIMEOUT | 5.000 | final | UNKNOWN | False | 60.000 |

Generated artifacts:

```text
runs/analysis/portfolio_e2e_local5_cadical55/smoke_raw.csv
```
