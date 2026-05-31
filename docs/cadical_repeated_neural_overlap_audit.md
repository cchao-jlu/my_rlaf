# Repeated CaDiCaL / Neural Overlap Audit

Scope: decision audit only. This uses the existing full400 3-seed neural
summary and the existing three CaDiCaL 60s repeats. It does not modify
models, selectors, thresholds, Local Boundary Correction, or solver configs.

Inputs:

```text
runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv
runs/analysis/cadical_repeat_stability/instance_summary.csv
```

Definitions:

- Neural solved means solved in all three solver-seed runs for that method.
- CaDiCaL solved-any means solved in at least one of three 60s repeats.
- CaDiCaL solved-all means solved in all three 60s repeats.
- Strict neural complementarity means neural solved and CaDiCaL unsolved in all three repeats.

## Summary

| Question | Count | Interpretation |
| --- | ---: | --- |
| CaDiCaL solved in any repeat / Local unsolved | 29 | CaDiCaL covers these neural-workflow misses in at least one 60s repeat. |
| CaDiCaL solved in all repeats / Local unsolved | 26 | Stable CaDiCaL-only coverage against Local Boundary Correction. |
| Local solved / CaDiCaL unsolved in all repeats | 3 | Strict repeated-baseline neural complementarity. |
| Local solved / CaDiCaL not solved in all repeats | 5 | Boundary-sensitive complementarity including CaDiCaL variance cases. |
| Online solved / CaDiCaL unsolved in all repeats | 2 | Strict repeated-baseline complementarity for the selector alone. |
| Online solved / CaDiCaL not solved in all repeats | 4 | Selector complementarity if CaDiCaL runtime-boundary cases are included. |
| Local-only over Online / CaDiCaL unsolved in all repeats | 1 | Strict boundary-correction contribution beyond Online and repeated CaDiCaL. |
| One-shot timeout recovered by Online | 5 | CaDiCaL solved 5/5 in at least one repeat and 5/5 in all repeats. |
| Local Correction open set | 4 | CaDiCaL solved 2/4 in at least one repeat and 2/4 in all repeats. |

## Portfolio Union Under Repeated CaDiCaL

| Method | Method solved | CaDiCaL any | Union vs any | Method only vs any | CaDiCaL any only | CaDiCaL all | Union vs all | Method only vs all | CaDiCaL all only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| One-shot | 48 | 80 | 82 | 2 | 34 | 75 | 79 | 4 | 31 |
| Online-Consistent Selector | 53 | 80 | 82 | 2 | 29 | 75 | 79 | 4 | 26 |
| Old Compact | 54 | 80 | 83 | 3 | 29 | 75 | 80 | 5 | 26 |
| + Local Boundary Correction | 54 | 80 | 83 | 3 | 29 | 75 | 80 | 5 | 26 |

## Local Solved / CaDiCaL Unsolved In All Repeats

| file_key | one_shot_solved | online_solved | local_correction_solved | cadical_solved_repeats | results | pattern |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | yes | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 1111 |
| 3sat_147.cnf | yes | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 1111 |
| 3sat_188.cnf | no | no | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 0011 |

## Online Solved / CaDiCaL Unsolved In All Repeats

| file_key | one_shot_solved | online_solved | cadical_solved_repeats | results | pattern |
| --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 1111 |
| 3sat_147.cnf | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 1111 |

## Local-Only Boundary Complement

| file_key | one_shot_solved | online_solved | old_compact_solved | local_correction_solved | cadical_solved_repeats | results | local_minus_online_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | no | no | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | -28.407 | 0011 |

## One-Shot Timeout Recovered By Online

| file_key | one_shot_solved | online_solved | cadical_solved_repeats | results | cadical_time_min | cadical_time_max | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_163.cnf | no | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 14.888 | 18.501 | 0111 |
| 3sat_189.cnf | no | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 14.812 | 18.623 | 0111 |
| 3sat_85.cnf | no | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 14.950 | 18.392 | 0111 |
| 3sat_89.cnf | no | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 5.329 | 6.692 | 0111 |
| 3sat_97.cnf | no | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 29.717 | 35.709 | 0111 |

## Local Correction Open Set

| file_key | one_shot_solved | online_solved | old_compact_solved | local_correction_solved | cadical_solved_repeats | results | cadical_time_min | cadical_time_max | local_minus_online_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | no | no | yes | yes | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 60.000 | 60.000 | -28.407 | 0011 |
| 3sat_196.cnf | yes | yes | yes | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 2.284 | 2.941 | -19.479 | 1111 |
| 3sat_46.cnf | yes | yes | yes | yes | 3 | SATISFIABLE,SATISFIABLE,SATISFIABLE | 1.133 | 1.460 | -36.851 | 1111 |
| 3sat_66.cnf | no | no | no | no | 0 | UNKNOWN,UNKNOWN,UNKNOWN | 60.000 | 60.000 | -0.000 | 0000 |

## Decision

- Strict neural/CaDiCaL complementarity is nonzero but small. Local solves
  3 instances that CaDiCaL times out on in all three repeats:
  `3sat_140.cnf`, `3sat_147.cnf`, and `3sat_188.cnf`. Online solves
  2 such instances: `3sat_140.cnf` and `3sat_147.cnf`.
- The strict boundary-correction contribution beyond Online and repeated
  CaDiCaL is one instance: `3sat_188.cnf`. This supports cautious
  complementarity / portfolio framing, not robust solved-count
  dominance over CaDiCaL.
- The larger boundary-sensitive complementarity count comes from CaDiCaL
  runtime variance. Local solves 5 instances that CaDiCaL does not solve
  in all repeats, but 2 of the 5 are solved by CaDiCaL in at least one
  repeat.
- Online's recovered one-shot timeouts do not establish complementarity
  against CaDiCaL: CaDiCaL solves all 5 in all three repeats.
- Local Boundary Correction's open set is mixed. CaDiCaL solves
  `3sat_46.cnf` and `3sat_196.cnf` in all repeats, solves neither
  `3sat_188.cnf` nor `3sat_66.cnf`, and Local only solves `3sat_188.cnf`
  among those CaDiCaL-strict-unsolved points.
- Therefore Local Boundary Correction should remain a neural-workflow
  boundary ablation. The top-conference path, if pursued, should be
  framed as boundary-sensitive neural/CDCL complementarity and risk
  control, not standalone performance superiority over CaDiCaL.

Generated artifacts:

```text
runs/analysis/cadical_repeated_neural_overlap/combined.csv
runs/analysis/cadical_repeated_neural_overlap/summary.csv
runs/analysis/cadical_repeated_neural_overlap/portfolio_union_repeated_cadical.csv
runs/analysis/cadical_repeated_neural_overlap/cadical_any_solved_local_unsolved.csv
runs/analysis/cadical_repeated_neural_overlap/cadical_all_solved_local_unsolved.csv
runs/analysis/cadical_repeated_neural_overlap/local_solved_cadical_unsolved_all.csv
runs/analysis/cadical_repeated_neural_overlap/local_solved_cadical_not_all.csv
runs/analysis/cadical_repeated_neural_overlap/online_solved_cadical_unsolved_all.csv
runs/analysis/cadical_repeated_neural_overlap/online_solved_cadical_not_all.csv
runs/analysis/cadical_repeated_neural_overlap/local_only_solved_cadical_unsolved_all.csv
runs/analysis/cadical_repeated_neural_overlap/oneshot_timeout_recovered_by_online.csv
runs/analysis/cadical_repeated_neural_overlap/local_open_set.csv
```
