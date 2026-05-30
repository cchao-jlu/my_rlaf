# End-to-End Local-5s / CaDiCaL-55s Portfolio Evaluation

Mode: `full`.

This runner loads the Local Boundary Correction checkpoint once, then
executes the Local workflow per instance under a 5s wall-clock budget.
Warmup and final weighted-Glucose calls are externally capped by the
remaining first-stage budget. Unsolved instances are then sent to
CaDiCaL for 55s.

Smoke mode is only a runner validation artifact. Full mode is the
paper-relevant end-to-end interrupted schedule over full400.

## Summary

| Metric | Value |
| --- | ---: |
| instances | 200 |
| portfolio solved | 79 |
| CaDiCaL 60s baseline solved | 75 |
| delta vs CaDiCaL 60s | +4 |
| portfolio-only vs CaDiCaL | 4 |
| CaDiCaL-only vs portfolio | 0 |
| Local first-stage solved | 40 |
| CaDiCaL second-stage solved | 39 |
| mean portfolio time | 41.121s |
| median portfolio time | 60.000s |
| Local errors | 0 |

## Portfolio-Only Instances

| file_key | local_result | local_solved | local_wall_time | cadical_result | cadical_time | portfolio_time | local_correction_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_111.cnf | TIMEOUT | False | 5.000 | SATISFIABLE | 54.281 | 59.281 | 60.420 | 0000 |
| 3sat_132.cnf | SATISFIABLE | True | 0.328 |  |  | 0.328 | 0.471 | 1111 |
| 3sat_140.cnf | SATISFIABLE | True | 4.198 |  |  | 4.198 | 5.465 | 1111 |
| 3sat_25.cnf | SATISFIABLE | True | 1.185 |  |  | 1.185 | 1.556 | 1111 |

## CaDiCaL-Only Instances

_None._

## Decision

- The true end-to-end schedule improves over CaDiCaL 60s by +4
  solved instances.
- This supports a real neural/CDCL complementarity portfolio result.

Generated artifacts:

```text
runs/analysis/portfolio_e2e_local5_cadical55/full_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_summary.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_portfolio_only_vs_cadical.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_cadical_only_vs_portfolio.csv
```
