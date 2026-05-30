# End-to-End Local-5s / CaDiCaL-55s Portfolio Stability

Scope: repeated full400 end-to-end portfolio audit. The model, selector,
Local Boundary Correction rule, CaDiCaL binary, and time split are fixed.
Each repeat runs Local Boundary Correction for at most 5s, then CaDiCaL
for at most 55s on unsolved instances.

Inputs:

```text
runs/analysis/portfolio_e2e_local5_cadical55/full_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_repeat1_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_repeat2_raw.csv
runs/analysis/cadical_neural_overlap/combined.csv
```

## Repeat Summary

| repeat | portfolio_solved | local_first_stage_solved | cadical_second_stage_solved | cadical_60s_baseline_solved | delta_vs_cadical_60s | portfolio_only_vs_cadical | cadical_only_vs_portfolio | mean_portfolio_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 79 | 40 | 39 | 75 | 4 | 4 | 0 | 41.121 |
| 1 | 80 | 40 | 40 | 75 | 5 | 5 | 0 | 41.118 |
| 2 | 80 | 40 | 40 | 75 | 5 | 5 | 0 | 41.134 |

## Aggregate

| repeats | portfolio_solved_mean | portfolio_solved_std | portfolio_solved_min | portfolio_solved_max | delta_vs_cadical_min | delta_vs_cadical_max | cadical_only_vs_portfolio_max | local_errors_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 79.667 | 0.471 | 79 | 80 | 4 | 5 | 0 | 0 |

## Stable Portfolio-Only Instances

| file_key | portfolio_only_vs_cadical_repeats | local_first_stage_solved_repeats | cadical_second_stage_solved_repeats | cadical_60s_time | portfolio_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_111.cnf | 3 | 0 | 3 | 60.000 | 58.805 | 0000 |
| 3sat_132.cnf | 3 | 3 | 0 | 60.000 | 0.315 | 1111 |
| 3sat_140.cnf | 3 | 3 | 0 | 60.000 | 4.157 | 1111 |
| 3sat_25.cnf | 3 | 3 | 0 | 60.000 | 1.209 | 1111 |

## Boundary-Sensitive Portfolio-Only Instances

| file_key | portfolio_only_vs_cadical_repeats | local_first_stage_solved_repeats | cadical_second_stage_solved_repeats | cadical_60s_time | portfolio_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_48.cnf | 2 | 0 | 2 | 60.000 | 59.748 | 0000 |

## Any CaDiCaL-Only Losses

_None._

## Decision

- The true end-to-end portfolio solves 79-80/200 over three full400
  repeats, compared with 75/200 for CaDiCaL 60s.
- Portfolio improvement over CaDiCaL is +4 to +5 solved instances, with
  zero CaDiCaL-only losses in all repeats.
- Local first stage is stable at 40 solves across repeats. Among the four
  stable portfolio-only instances, 3 are solved by Local
  within 5s and 1 is solved by the second-stage 55s
  CaDiCaL run despite the independent 60s CaDiCaL baseline timing out.
- Boundary-sensitive portfolio-only evidence is 1
  second-stage CaDiCaL cutoff/runtime boundary case.
- Stable portfolio-only instances are `3sat_111.cnf`, `3sat_132.cnf`,
  `3sat_140.cnf`, and `3sat_25.cnf`; `3sat_48.cnf` is boundary-sensitive
  and appears in two of three repeats.
- This supports a cautious portfolio/complementarity claim. The strongest
  neural-first contribution is the stable 5s Local solves; the second-stage
  CaDiCaL-only cutoff cases should be reported as runtime-boundary evidence,
  not as neural solves.

Generated artifacts:

```text
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_aggregate.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stable_portfolio_only_vs_cadical.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_boundary_portfolio_only_vs_cadical.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_any_cadical_only_vs_portfolio.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_unstable_portfolio_solved.csv
```
