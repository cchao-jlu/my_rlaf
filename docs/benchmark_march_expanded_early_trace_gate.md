# Expanded March Early-Trace Gate

Scope: recoverable early-trace selector gate on the expanded
March/CaDiCaL both-unknown transition-band subset. This is still a
model/experiment gate, not a paper claim.

Input instances: 15; sample seeds: [1729].

## Aggregate

| selector_policy | top_k | probe_cpu_lim | groups | instances | sample_seeds | solved_groups | solved_instances_any_seed | probe_stage_solves | full_stage_solves | mean_attempts_used | mean_total_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| probe_solved_then_high_deadends | 2 | 1.000 | 15 | 15 | 1 | 1 | 1 | 0 | 1 | 1.933 | 120.969 |

## Per Group

| size | file_key | sample_seed | selector_policy | top_k | probe_solved_samples | attempts_used | solved_any_strict60 | solved_stage | first_solved_rank | total_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 410 | 3sat_12.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 1 | True | full | 1 | 22.535 |
| 410 | 3sat_15.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 410 | 3sat_24.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 410 | 3sat_29.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 410 | 3sat_38.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_0.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_12.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_15.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_16.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_19.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_22.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_23.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_28.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_35.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |
| 425 | 3sat_41.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 128.000 |

Artifacts:

```text
runs/analysis/benchmark_march_expanded_early_trace_gate/expanded_early_trace_probe_raw.csv
runs/analysis/benchmark_march_expanded_early_trace_gate/expanded_early_trace_raw.csv
runs/analysis/benchmark_march_expanded_early_trace_gate/expanded_early_trace_candidates.csv
runs/analysis/benchmark_march_expanded_early_trace_gate/expanded_early_trace_summary.csv
runs/analysis/benchmark_march_expanded_early_trace_gate/expanded_early_trace_aggregate.csv
runs/analysis/benchmark_march_expanded_early_trace_gate/groups/
```
