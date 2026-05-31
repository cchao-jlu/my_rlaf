# March Full400 Baseline Audit

Scope: evaluate the existing unweighted March binary as an additional
solver-family baseline on full400. This does not change the neural model,
selector, Local Boundary Correction rule, or portfolio schedule.

Inputs:

```text
runs/march/solver_stats_full400_cpu60.csv
runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv
runs/analysis/cadical_repeat_stability/instance_summary.csv
```

Important timing note: March has no internal 60s flag in the current
runner. The raw run used a 65s external guard. The paper-relevant count
below therefore reports a strict 60s solved count, treating solutions with
wall time greater than 60s as timeouts.

## Summary

| solver | total | solved_external65 | solved_strict60 | solved_after_60_before_65 | mean_time_strict60 | median_time_strict60 | external_timeouts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| March | 200 | 192 | 184 | 8 | 26.702 | 28.759 | 8 |

## Neural / March Overlap

| method | method_solved | march_strict60_solved | union_solved | method_only_vs_march | march_only_vs_method | both_unsolved |
| --- | --- | --- | --- | --- | --- | --- |
| One-shot | 48 | 184 | 184 | 0 | 136 | 16 |
| Online-Consistent Selector | 53 | 184 | 184 | 0 | 131 | 16 |
| Old Compact | 54 | 184 | 184 | 0 | 130 | 16 |
| + Local Boundary Correction | 54 | 184 | 184 | 0 | 130 | 16 |

## Former CaDiCaL-Strict Complement Keys

| file_key | online_solved | local_correction_solved | cadical_solved_repeats | march_solved_strict60 | march_wall_time | pattern |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | yes | yes | 0 | yes | 8.050 | 1111 |
| 3sat_147.cnf | yes | yes | 0 | yes | 35.587 | 1111 |
| 3sat_188.cnf | no | yes | 0 | yes | 15.664 | 0011 |

## Decision

- March strict-60 solves 184/200, far above CaDiCaL repeats (75, 80, 80),
  the Local5 -> CaDiCaL55 portfolio (79-80/200), and all neural-stage
  Glucose-guided methods (48-54/200).
- March solves all three instances that were Local-solved and CaDiCaL
  unsolved in all repeated CaDiCaL runs: `3sat_140.cnf`, `3sat_147.cnf`,
  and `3sat_188.cnf`.
- Local Boundary Correction has no strict solved-count complement against
  March under this single strict-60 run: Local solved / March unsolved is
  0 instances.
- Therefore, the current evidence cannot support a top-conference claim of
  complementarity against strong SAT baselines. Unless March is excluded by
  a clearly justified benchmark protocol, the paper should pivot further
  toward neural-guidance failure boundary analysis, risk control, or a
  workshop/negative-results framing.

Generated artifacts:

```text
runs/analysis/march_full400_cpu60/strict60_summary.csv
runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv
runs/analysis/march_full400_cpu60/strict_complement_keys.csv
runs/analysis/march_full400_cpu60/local_solved_march_unsolved.csv
runs/analysis/march_full400_cpu60/march_solved_local_unsolved.csv
```
