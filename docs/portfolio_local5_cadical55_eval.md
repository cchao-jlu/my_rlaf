# Local-5s / CaDiCaL-55s Portfolio Evaluation

Mode: `full`.

Scope: this evaluates the concrete schedule suggested by the portfolio
feasibility audit: first allocate 5s to + Local Boundary Correction, then
run CaDiCaL for the remaining 55s on instances not solved by the first
stage.

Important limitation: the first-stage Local result is imported from the
existing full400 3-seed mean table by counting instances solved by Local
within 5s. The second-stage CaDiCaL 55s results are actually rerun. This
is stronger than the pure feasibility simulation for CaDiCaL stability,
but it is still not a complete interrupted end-to-end neural portfolio
run.

## Summary

| Metric | Value |
| --- | ---: |
| solved | 79/200 |
| CaDiCaL alone solved | 75/200 |
| delta vs CaDiCaL solved | +4 |
| portfolio-only solved vs CaDiCaL | 4 |
| CaDiCaL-only solved vs portfolio | 0 |
| local stage-1 solved within 5s | 37 |
| CaDiCaL stage-2 solved within 55s | 42 |
| mean portfolio time | 41.661s |
| median portfolio time | 60.000s |

## Portfolio-Only Instances

| file_key | local_stage1_solved | stage2_solved | portfolio_time | local_correction_time_mean | cadical_time | pattern |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_111.cnf | False | True | 59.188 | 60.420 | 60.000 | 0000 |
| 3sat_132.cnf | True | False | 0.471 | 0.471 | 60.000 | 1111 |
| 3sat_25.cnf | True | False | 1.556 | 1.556 | 60.000 | 1111 |
| 3sat_48.cnf | False | True | 59.383 | 60.389 | 60.000 | 0000 |

## CaDiCaL-Only Instances

_None._

## Decision

- This hybrid schedule reaches 79/200, +4
  over the CaDiCaL 60s baseline, and loses no CaDiCaL-solved
  instances under the current rerun.
- The portfolio direction is now empirically supported enough to
  justify a true end-to-end interrupted runner.
- This is not yet a paper-ready portfolio result because the 5s Local
  first stage is imported from existing full400 3-seed mean times
  rather than executed as an interrupted solver process.

Generated artifacts:

```text
runs/analysis/portfolio_local5_cadical55/full_cadical55_raw.csv
runs/analysis/portfolio_local5_cadical55/full_combined.csv
runs/analysis/portfolio_local5_cadical55/full_summary.csv
runs/analysis/portfolio_local5_cadical55/full_portfolio_only_vs_cadical.csv
runs/analysis/portfolio_local5_cadical55/full_cadical_only_vs_portfolio.csv
```
