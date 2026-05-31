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
runner. Each raw run used a 65s external guard. The paper-relevant count
below reports a strict 60s solved count, treating solutions with wall time
greater than 60s as timeouts.

## Repeated Strict-60 Summary

| solver | total | repeats | solved_external65 | solved_external65_std | solved_strict60 | solved_strict60_std | solved_strict60_min | solved_strict60_max | solved_after_60_before_65 | mean_time_strict60 | mean_time_strict60_std | median_time_strict60 | external_timeouts | strict60_stable_instances |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| March | 200 | 3 | 192.000 | 0.000 | 184.000 | 0.000 | 184 | 184 | 8.000 | 26.713 | 0.010 | 28.844 | 8.000 | 200 |

## Per-Repeat Strict-60 Results

| repeat | total | solved_external65 | solved_strict60 | solved_after_60_before_65 | mean_time_strict60 | median_time_strict60 | external_timeouts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 200 | 192 | 184 | 8 | 26.702 | 28.759 | 8 |
| 1 | 200 | 192 | 184 | 8 | 26.726 | 28.838 | 8 |
| 2 | 200 | 192 | 184 | 8 | 26.710 | 28.936 | 8 |

## Neural / March Overlap

| method | method_solved | march_strict60_all_solved | union_vs_march_all | method_only_vs_march_all | march_all_only_vs_method | both_unsolved_vs_march_all |
| --- | --- | --- | --- | --- | --- | --- |
| One-shot | 48 | 184 | 184 | 0 | 136 | 16 |
| Online-Consistent Selector | 53 | 184 | 184 | 0 | 131 | 16 |
| Old Compact | 54 | 184 | 184 | 0 | 130 | 16 |
| + Local Boundary Correction | 54 | 184 | 184 | 0 | 130 | 16 |

## Former CaDiCaL-Strict Complement Keys

| file_key | online_solved | local_correction_solved | cadical_solved_repeats | march_solved_strict60_repeats | march_solved_strict60_all | march_wall_time_mean | pattern |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | yes | yes | 0 | 3 | yes | 8.171 | 1111 |
| 3sat_147.cnf | yes | yes | 0 | 3 | yes | 35.815 | 1111 |
| 3sat_188.cnf | no | yes | 0 | 3 | yes | 15.555 | 0011 |

## Decision

- March strict-60 solves 184/200 in each of three repeats, far above
  CaDiCaL repeats (75, 80, 80), the Local5 -> CaDiCaL55 portfolio
  (79-80/200), and all neural-stage Glucose-guided methods (48-54/200).
- March strict-60 solved status is stable on all 200 instances across the
  three repeats: 184 instances are solved in all repeats and 16 are
  unsolved in all repeats.
- March solves all three instances that were Local-solved and CaDiCaL
  unsolved in all repeated CaDiCaL runs: `3sat_140.cnf`, `3sat_147.cnf`,
  and `3sat_188.cnf`, in all three strict-60 repeats.
- Local Boundary Correction has no strict solved-count complement against
  repeated March strict-60: Local solved / March unsolved-all is
  0 instances.
- Therefore, the current evidence cannot support a top-conference claim of
  complementarity against strong SAT baselines. Unless March is excluded by
  a clearly justified benchmark protocol, the paper should pivot further
  toward neural-guidance failure boundary analysis, risk control, or a
  workshop/negative-results framing.

Generated artifacts:

```text
runs/analysis/march_full400_cpu60/strict60_summary.csv
runs/analysis/march_full400_cpu60/strict60_repeat_summary.csv
runs/analysis/march_full400_cpu60/strict60_instance_summary.csv
runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv
runs/analysis/march_full400_cpu60/strict_complement_keys.csv
runs/analysis/march_full400_cpu60/local_solved_march_unsolved.csv
runs/analysis/march_full400_cpu60/march_solved_local_unsolved.csv
```
