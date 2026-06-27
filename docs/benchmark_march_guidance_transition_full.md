# March-Guided Transition-Band Triage

Scope: frozen March-trained one-shot guidance on transition-band
`full` instances. This
uses the existing `runs/GNN_March_3SAT/best.pt` checkpoint and
`solvers/march_weighted/march_nh`; it does not train or tune models.

## Both-Unknown Input Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 410 | 3sat_0.cnf |
| 3sat | 410 | 3sat_1.cnf |
| 3sat | 410 | 3sat_10.cnf |
| 3sat | 410 | 3sat_11.cnf |
| 3sat | 410 | 3sat_2.cnf |
| 3sat | 410 | 3sat_3.cnf |
| 3sat | 410 | 3sat_4.cnf |
| 3sat | 410 | 3sat_5.cnf |
| 3sat | 410 | 3sat_6.cnf |
| 3sat | 410 | 3sat_7.cnf |
| 3sat | 410 | 3sat_8.cnf |
| 3sat | 410 | 3sat_9.cnf |
| 3sat | 425 | 3sat_0.cnf |
| 3sat | 425 | 3sat_1.cnf |
| 3sat | 425 | 3sat_10.cnf |
| 3sat | 425 | 3sat_11.cnf |
| 3sat | 425 | 3sat_2.cnf |
| 3sat | 425 | 3sat_3.cnf |
| 3sat | 425 | 3sat_4.cnf |
| 3sat | 425 | 3sat_5.cnf |
| 3sat | 425 | 3sat_6.cnf |
| 3sat | 425 | 3sat_7.cnf |
| 3sat | 425 | 3sat_8.cnf |
| 3sat | 425 | 3sat_9.cnf |
| 3sat | 440 | 3sat_0.cnf |
| 3sat | 440 | 3sat_1.cnf |
| 3sat | 440 | 3sat_10.cnf |
| 3sat | 440 | 3sat_11.cnf |
| 3sat | 440 | 3sat_2.cnf |
| 3sat | 440 | 3sat_3.cnf |
| 3sat | 440 | 3sat_4.cnf |
| 3sat | 440 | 3sat_5.cnf |
| 3sat | 440 | 3sat_6.cnf |
| 3sat | 440 | 3sat_7.cnf |
| 3sat | 440 | 3sat_8.cnf |
| 3sat | 440 | 3sat_9.cnf |

## Method Summary

| family | size | paper_name | seeds | solved_mean | solved_min | solved_max | mean_time_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | March-Guided One-shot | 1 | 9.000 | 9 | 9 | 29.126 |
| 3sat | 425 | March-Guided One-shot | 1 | 10.000 | 10 | 10 | 29.182 |
| 3sat | 440 | March-Guided One-shot | 1 | 5.000 | 5 | 5 | 38.133 |

## Strict Complement Summary

Solved means solved in all requested seeds.

| family | size | n | strict_solved |
| --- | --- | --- | --- |
| 3sat | 410 | 12 | 9 |
| 3sat | 425 | 12 | 10 |
| 3sat | 440 | 12 | 5 |

## Decision

- Frozen March-guided one-shot has nonzero solves on the transition-band
  March/CaDiCaL both-unknown subset.
- This is the first low-cost performance signal in the current gate
  family. It requires repeated strong-solver confirmation and a larger
  benchmark before becoming a top-conference claim.
- Strict solved keys: `3sat-410/3sat_0.cnf`, `3sat-410/3sat_1.cnf`, `3sat-410/3sat_10.cnf`, `3sat-410/3sat_11.cnf`, `3sat-410/3sat_4.cnf`, `3sat-410/3sat_5.cnf`, `3sat-410/3sat_6.cnf`, `3sat-410/3sat_7.cnf`, `3sat-410/3sat_9.cnf`, `3sat-425/3sat_0.cnf`, `3sat-425/3sat_1.cnf`, `3sat-425/3sat_2.cnf`, `3sat-425/3sat_3.cnf`, `3sat-425/3sat_4.cnf`, `3sat-425/3sat_5.cnf`, `3sat-425/3sat_6.cnf`, `3sat-425/3sat_7.cnf`, `3sat-425/3sat_8.cnf`, `3sat-425/3sat_9.cnf`, `3sat-440/3sat_1.cnf`, `3sat-440/3sat_10.cnf`, `3sat-440/3sat_4.cnf`, `3sat-440/3sat_5.cnf`, `3sat-440/3sat_6.cnf`.

Generated artifacts:

```text
runs/analysis/benchmark_march_guidance_transition_full/full_subset.csv
runs/analysis/benchmark_march_guidance_transition_full/combined.csv
runs/analysis/benchmark_march_guidance_transition_full/summary.csv
runs/analysis/benchmark_march_guidance_transition_full/overlap.csv
```
