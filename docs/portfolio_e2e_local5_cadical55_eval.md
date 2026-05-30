# End-to-End Local-5s / CaDiCaL-55s Portfolio Evaluation

This document records the current end-to-end portfolio evaluation status.
The paper-relevant claim should use the three-repeat stability audit in
`docs/portfolio_e2e_local5_cadical55_stability.md`, not a single repeat.

This runner loads the Local Boundary Correction checkpoint once, then
executes the Local workflow per instance under a 5s wall-clock budget.
Warmup and final weighted-Glucose calls are externally capped by the
remaining first-stage budget. Unsolved instances are then sent to
CaDiCaL for 55s.

Smoke mode is only a runner validation artifact. Full mode is the
paper-relevant end-to-end interrupted schedule over full400.

## Stability Summary

| Repeat | Portfolio solved | Local first-stage solved | CaDiCaL second-stage solved | Delta vs CaDiCaL 60s | CaDiCaL-only losses |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 79 | 40 | 39 | +4 | 0 |
| 1 | 80 | 40 | 40 | +5 | 0 |
| 2 | 80 | 40 | 40 | +5 | 0 |

CaDiCaL 60s baseline solves 75/200. The true end-to-end portfolio solves
79-80/200 over three full400 repeats, with zero CaDiCaL-only losses.

## Portfolio-Only Evidence

Stable portfolio-only instances across all three repeats:

| file_key | source in portfolio | interpretation |
| --- | --- | --- |
| 3sat_132.cnf | Local first stage | Neural-first complementary solve within 5s. |
| 3sat_140.cnf | Local first stage | Neural-first complementary solve within 5s. |
| 3sat_25.cnf | Local first stage | Neural-first complementary solve within 5s. |
| 3sat_111.cnf | CaDiCaL second stage | Runtime-boundary evidence: solved by 55s second-stage CaDiCaL but not by the independent 60s CaDiCaL baseline run. |

Boundary-sensitive portfolio-only instance:

| file_key | source in portfolio | interpretation |
| --- | --- | --- |
| 3sat_48.cnf | CaDiCaL second stage | Appears in two of three repeats; treat as cutoff/runtime boundary evidence. |

## Decision

- The true end-to-end portfolio supports a cautious neural/CDCL
  complementarity claim: 79-80/200 vs CaDiCaL 75/200 over three repeats.
- The strongest neural-first contribution is the three stable Local 5s
  portfolio-only solves.
- Second-stage CaDiCaL-only cutoff cases should not be described as neural
  solves; they show runtime-boundary sensitivity of the sequential schedule.
- Local Boundary Correction remains an internal neural-workflow component,
  while the current strongest top-conference direction is the portfolio
  framing.

Generated artifacts:

```text
runs/analysis/portfolio_e2e_local5_cadical55/full_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_repeat1_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/full_repeat2_raw.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_aggregate.csv
runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv
```
