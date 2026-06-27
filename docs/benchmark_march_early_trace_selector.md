# March Early-Trace Selector Gate

Scope: non-oracle selector gate for sampled March guidance. Each sampled
guidance first runs under a short internal March CPU budget to collect
progress counters; the selector ranks candidates by those counters and
only reruns fixed top-k candidates under the nominal 60s budget.

Sample seeds: [1729, 1730, 1731].

## Instances

| size | file_key |
| --- | --- |
| 410 | 3sat_2.cnf |
| 440 | 3sat_8.cnf |

## Aggregate

| selector_policy | top_k | probe_cpu_lim | groups | instances | sample_seeds | solved_groups | solved_instances_any_seed | probe_stage_solves | full_stage_solves | mean_attempts_used | mean_total_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| probe_solved_then_high_deadends | 2 | 1.000 | 6 | 2 | 3 | 4 | 2 | 0 | 4 | 1.333 | 79.219 |

## Per Group

| size | file_key | sample_seed | selector_policy | top_k | probe_solved_samples | attempts_used | solved_any_strict60 | solved_stage | first_solved_rank | total_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 410 | 3sat_2.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 1 | True | full | 1 | 18.251 |
| 410 | 3sat_2.cnf | 1730 | probe_solved_then_high_deadends | 2 | 0 | 1 | True | full | 1 | 68.196 |
| 410 | 3sat_2.cnf | 1731 | probe_solved_then_high_deadends | 2 | 0 | 1 | True | full | 1 | 63.517 |
| 440 | 3sat_8.cnf | 1729 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 136.000 |
| 440 | 3sat_8.cnf | 1730 | probe_solved_then_high_deadends | 2 | 0 | 2 | False | none | -1 | 136.000 |
| 440 | 3sat_8.cnf | 1731 | probe_solved_then_high_deadends | 2 | 0 | 1 | True | full | 1 | 53.347 |

Artifacts:

```text
runs/analysis/benchmark_march_early_trace_selector/early_trace_probe_raw.csv
runs/analysis/benchmark_march_early_trace_selector/early_trace_selector_raw.csv
runs/analysis/benchmark_march_early_trace_selector/early_trace_selector_candidates.csv
runs/analysis/benchmark_march_early_trace_selector/early_trace_selector_summary.csv
```
