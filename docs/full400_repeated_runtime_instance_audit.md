# Full400 Repeated Runtime Per-Instance Audit

This audit uses only the committed full400 repeated-runtime artifacts.
It does not run new solver evaluations and does not change model, threshold, or solver configuration.

Solved pattern order: `One-shot / Online-Consistent / Old Compact / + Local Boundary Correction`.
All four methods have stable per-instance repeat outcomes: every instance is either solved in all 3 repeats or timed out in all 3 repeats for a given method.

Outputs:

- `runs/analysis/full400_repeated_runtime/solved_pattern_overlap.csv`
- `runs/analysis/full400_repeated_runtime/solved_pattern_summary.csv`
- `runs/analysis/full400_repeated_runtime/solved_difference_audit.csv`
- `runs/analysis/full400_repeated_runtime/local_vs_old_time_audit.csv`

## Solved Pattern Summary

| pattern | count | interpretation |
| --- | ---: | --- |
| 0000 | 146 | no method solves |
| 0011 | 1 | Old Compact and Local Correction solve; One-shot and Online timeout |
| 0111 | 5 | all guided variants solve; One-shot times out |
| 1111 | 48 | all methods solve |

## Key Solved Difference

- Old Compact has exactly one all-repeat solved instance that Online-Consistent Selector does not solve.
- + Local Boundary Correction has exactly one all-repeat solved instance that Online-Consistent Selector does not solve.
- These are the same boundary instance.

| comparison | instance | pattern | one-shot mean | online mean | old compact mean | local correction mean |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Old Compact over Online | 3sat_188.cnf | 0011 | 60.2801 | 60.3722 | 31.8350 | 32.0581 |
| Local Correction over Online | 3sat_188.cnf | 0011 | 60.2801 | 60.3722 | 31.8350 | 32.0581 |

## Local Correction Versus Old Compact

- Solved-pattern mismatch count: 0.
- Same-solved instances with Local Correction slower than Old Compact by >0.1s: 7.
- Same-solved instances with Local Correction slower than Old Compact by >0.5s: 2.
- Same-solved instances with Local Correction slower than Old Compact by >1.0s: 0.
- Maximum same-solved slowdown is 0.8234s on `3sat_163.cnf`.

Top same-solved Local Correction slowdowns relative to Old Compact:

| instance | pattern | old solved repeats | old mean | local mean | local-old delta |
| --- | --- | ---: | ---: | ---: | ---: |
| 3sat_163.cnf | 0111 | 3 | 34.8483 | 35.6718 | 0.8234 |
| 3sat_86.cnf | 1111 | 3 | 3.5725 | 4.2076 | 0.6352 |
| 3sat_157.cnf | 1111 | 3 | 33.7287 | 34.1179 | 0.3893 |
| 3sat_188.cnf | 0011 | 3 | 31.8350 | 32.0581 | 0.2231 |
| 3sat_189.cnf | 0111 | 3 | 17.2275 | 17.3832 | 0.1558 |
| 3sat_63.cnf | 1111 | 3 | 5.4485 | 5.5818 | 0.1333 |
| 3sat_54.cnf | 1111 | 3 | 22.1821 | 22.3061 | 0.1240 |
| 3sat_20.cnf | 1111 | 3 | 12.6668 | 12.7610 | 0.0942 |
| 3sat_192.cnf | 0000 | 0 | 60.3442 | 60.4185 | 0.0743 |
| 3sat_195.cnf | 0000 | 0 | 60.3389 | 60.4124 | 0.0735 |

## Paper-Facing Reading

This audit supports the narrower claim that guarded Local Boundary Correction reaches the Old Compact solved count on repeated full400 while reducing mean runtime.
It does not support the claim that Online-Consistent Selector alone exceeds Old Compact in solved count.
`3sat_188.cnf` is the single boundary instance explaining both the Old Compact-over-Online and Local-over-Online solved-count gap.
