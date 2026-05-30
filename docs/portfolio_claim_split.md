# Portfolio Claim Split

Scope: classify the end-to-end Local-5s / CaDiCaL-55s portfolio-only
instances into neural-first complementarity and second-stage runtime
boundary evidence. This document is meant to prevent over-claiming
portfolio-only solves as neural solves.

Inputs:

```text
runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv
```

## Summary

| claim_class | instances | total_portfolio_only_repeats | local_first_stage_solved_repeats | cadical_second_stage_solved_repeats |
| --- | --- | --- | --- | --- |
| stable_neural_first_complement | 3 | 9 | 9 | 0 |
| stable_second_stage_runtime_boundary | 1 | 3 | 0 | 3 |
| unstable_second_stage_runtime_boundary | 1 | 2 | 0 | 2 |

## Stable Neural-First Complement

| file_key | portfolio_only_vs_cadical_repeats | local_first_stage_solved_repeats | cadical_60s_time | portfolio_time_mean | pattern | paper_interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_132.cnf | 3 | 3 | 60.000 | 0.315 | 1111 | Strong neural-first portfolio complement: Local solves within 5s in all repeats while CaDiCaL 60s times out. |
| 3sat_140.cnf | 3 | 3 | 60.000 | 4.157 | 1111 | Strong neural-first portfolio complement: Local solves within 5s in all repeats while CaDiCaL 60s times out. |
| 3sat_25.cnf | 3 | 3 | 60.000 | 1.209 | 1111 | Strong neural-first portfolio complement: Local solves within 5s in all repeats while CaDiCaL 60s times out. |

## Stable Second-Stage Runtime Boundary

| file_key | portfolio_only_vs_cadical_repeats | cadical_second_stage_solved_repeats | cadical_60s_time | portfolio_time_mean | pattern | paper_interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_111.cnf | 3 | 3 | 60.000 | 58.805 | 0000 | Sequential-schedule runtime-boundary evidence: second-stage CaDiCaL 55s solves in all repeats while independent CaDiCaL 60s baseline times out. |

## Unstable Second-Stage Runtime Boundary

| file_key | portfolio_only_vs_cadical_repeats | cadical_second_stage_solved_repeats | cadical_60s_time | portfolio_time_mean | pattern | paper_interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_48.cnf | 2 | 2 | 60.000 | 59.748 | 0000 | Cutoff/runtime boundary evidence, not a neural solve. |

## Decision

- The strongest top-conference claim is not that neural guidance alone
  beats CaDiCaL. It is that a neural-first/CDCL-second schedule has
  stable complementarity with CaDiCaL 60s on full400.
- The strict neural-first complement consists of 3 stable instances:
  `3sat_132.cnf`, `3sat_140.cnf`, and `3sat_25.cnf`.
- `3sat_111.cnf` is stable portfolio-only evidence, but it is solved by
  the second-stage CaDiCaL run, so it should be described as a
  sequential-schedule runtime-boundary case.
- `3sat_48.cnf` appears in two of three repeats and is also a
  second-stage CaDiCaL cutoff/runtime boundary case.
- Paper tables may report total portfolio solved count, but explanatory
  text must split neural-first complement from second-stage runtime
  boundary evidence.

Generated artifacts:

```text
runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv
runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split_summary.csv
```
