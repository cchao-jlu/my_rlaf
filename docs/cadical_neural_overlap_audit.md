# CaDiCaL / Neural Full400 Overlap Audit

Scope: decision audit only. This does not modify the model, selector,
thresholds, Local Boundary Correction rule, or solver configuration.

Inputs:

```text
runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv
runs/cadical/solver_stats_full400_cpu60.csv
```

## Summary

| Question | Count | Interpretation |
| --- | ---: | --- |
| CaDiCaL solved / Local unsolved | 26 | CaDiCaL covers many instances missed by the neural-guided Glucose workflow. |
| Local solved / CaDiCaL unsolved | 5 | Nonzero complementarity for a neural/CaDiCaL portfolio. |
| Online solved / CaDiCaL unsolved | 4 | Online alone has nonzero complementarity, but these are all already One-shot solved. |
| One-shot timeout recovered by Online | 5 | CaDiCaL solved 5/5 of these. |
| Local Correction open set | 4 | CaDiCaL solved 2/4 open-set instances. |

## Portfolio Union Counts

| Method | Method solved | CaDiCaL solved | Union solved | Method only | CaDiCaL only | Both unsolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| One-shot | 48 | 75 | 79 | 4 | 31 | 121 |
| Online-Consistent Selector | 53 | 75 | 79 | 4 | 26 | 121 |
| Old Compact | 54 | 75 | 80 | 5 | 26 | 120 |
| + Local Boundary Correction | 54 | 75 | 80 | 5 | 26 | 120 |

## Local Solved / CaDiCaL Unsolved

| file_key | one_shot_solved | online_solved | old_compact_solved | local_correction_solved | cadical_solved | cadical_time | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_132.cnf | yes | yes | yes | yes | no | 60.000 | 1111 |
| 3sat_140.cnf | yes | yes | yes | yes | no | 60.000 | 1111 |
| 3sat_147.cnf | yes | yes | yes | yes | no | 60.000 | 1111 |
| 3sat_188.cnf | no | no | yes | yes | no | 60.000 | 0011 |
| 3sat_25.cnf | yes | yes | yes | yes | no | 60.000 | 1111 |

## Online Solved / CaDiCaL Unsolved

| file_key | one_shot_solved | online_solved | cadical_solved | cadical_time | pattern |
| --- | --- | --- | --- | --- | --- |
| 3sat_132.cnf | yes | yes | no | 60.000 | 1111 |
| 3sat_140.cnf | yes | yes | no | 60.000 | 1111 |
| 3sat_147.cnf | yes | yes | no | 60.000 | 1111 |
| 3sat_25.cnf | yes | yes | no | 60.000 | 1111 |

## One-Shot Timeout Recovered By Online

| file_key | one_shot_solved | online_solved | cadical_solved | cadical_time | pattern |
| --- | --- | --- | --- | --- | --- |
| 3sat_163.cnf | no | yes | yes | 18.501 | 0111 |
| 3sat_189.cnf | no | yes | yes | 18.623 | 0111 |
| 3sat_85.cnf | no | yes | yes | 18.392 | 0111 |
| 3sat_89.cnf | no | yes | yes | 6.692 | 0111 |
| 3sat_97.cnf | no | yes | yes | 35.709 | 0111 |

## Local Correction Open Set

| file_key | one_shot_solved | online_solved | old_compact_solved | local_correction_solved | cadical_solved | cadical_time | local_minus_online_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | no | no | yes | yes | no | 60.000 | -28.407 | 0011 |
| 3sat_196.cnf | yes | yes | yes | yes | yes | 2.941 | -19.479 | 1111 |
| 3sat_46.cnf | yes | yes | yes | yes | yes | 1.460 | -36.851 | 1111 |
| 3sat_66.cnf | no | no | no | no | no | 60.000 | -0.000 | 0000 |

## Decision

- There is stable nonzero neural/CaDiCaL complementarity: + Local Boundary
  Correction solves 5 instances that CaDiCaL does not solve, and Online
  alone solves 4 instances that CaDiCaL does not solve.
- However, Online's 5 one-shot-timeout recoveries are all solved by
  CaDiCaL. The Online complementarity instances are already One-shot solved,
  so they do not support a strong recovery-over-CDCL story.
- Local Correction's open set is mixed: CaDiCaL solves `3sat_46.cnf` and
  `3sat_196.cnf` quickly, does not solve `3sat_188.cnf`, and also does not
  solve neutral timeout `3sat_66.cnf`.
- The best paper direction is complementarity / portfolio framing, not
  standalone performance dominance. Local Boundary Correction remains an
  internal neural-workflow ablation, with `3sat_188.cnf` as the only
  open-set solved complementarity point against CaDiCaL.

Generated artifacts:

```text
runs/analysis/cadical_neural_overlap/combined.csv
runs/analysis/cadical_neural_overlap/summary.csv
runs/analysis/cadical_neural_overlap/portfolio_union_summary.csv
runs/analysis/cadical_neural_overlap/cadical_solved_local_unsolved.csv
runs/analysis/cadical_neural_overlap/local_solved_cadical_unsolved.csv
runs/analysis/cadical_neural_overlap/online_solved_cadical_unsolved.csv
runs/analysis/cadical_neural_overlap/oneshot_timeout_recovered_by_online.csv
runs/analysis/cadical_neural_overlap/local_open_set.csv
```
