# March-Guided Full Transition-Band Overlap

Scope: diagnostic comparison of frozen March-guided one-shot against
unguided March and CaDiCaL on the 36-instance transition-band set.
This is model-result evidence, not paper polishing.

## Summary

| size | n | march_solved | cadical_solved | strong_union_solved | march_guided_solved | guided_only_vs_union | union_only_vs_guided | guided_only_vs_march | march_only_vs_guided | mean_guided_minus_march_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 410.000 | 12.000 | 9.000 | 4.000 | 9.000 | 9.000 | 0.000 | 0.000 | 0.000 | 0.000 | -2.986 |
| 425.000 | 12.000 | 9.000 | 9.000 | 10.000 | 10.000 | 0.000 | 0.000 | 1.000 | 0.000 | -0.045 |
| 440.000 | 12.000 | 4.000 | 6.000 | 6.000 | 5.000 | 0.000 | 1.000 | 2.000 | 1.000 | -11.347 |

## Guided-Only vs Strong Union

_None._

## Guided-Only vs Unguided March

| size | file_key | result_march_guided | time_march_guided | time_march | time_cadical |
| --- | --- | --- | --- | --- | --- |
| 425 | 3sat_5.cnf | SATISFIABLE | 31.915 | 60.000 | 7.746 |
| 440 | 3sat_1.cnf | SATISFIABLE | 1.077 | 60.000 | 5.353 |
| 440 | 3sat_10.cnf | SATISFIABLE | 1.642 | 60.000 | 5.583 |

## Unguided March-Only vs Guided

| size | file_key | time_march | time_march_guided | time_cadical |
| --- | --- | --- | --- | --- |
| 440 | 3sat_3.cnf | 55.675 | 60.337 | 54.289 |

## Decision

- March-guided one-shot has no complementarity against the March/CaDiCaL
  union on this transition-band set.
- If it helps relative to unguided March, that help is still covered by
  CaDiCaL and does not create a top-conference performance path yet.

Generated artifacts:

```text
runs/analysis/benchmark_march_guidance_transition_full/strong_solver_overlap.csv
runs/analysis/benchmark_march_guidance_transition_full/strong_solver_overlap_summary.csv
```
