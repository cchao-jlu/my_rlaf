# March Budgeted Sample Selector Gate

Scope: real fixed-budget gate for sampled March guidance. The runner
generates stochastic guidances, ranks them using a cheap pre-solver
metric, solves only top-k candidates, and stops after the first strict-60
solve. This is not an oracle sample selection result.

Sample seeds: [1729, 1730, 1731].

## Instances

| size | file_key |
| --- | --- |
| 410 | 3sat_2.cnf |
| 440 | 3sat_8.cnf |

## Aggregate

| selector_policy | top_k | groups | instances | sample_seeds | solved_groups | solved_instances_any_seed | mean_attempts_used | mean_stop_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_low_logprob_high_weightstd | 2 | 6 | 2 | 3 | 4 | 2 | 1.333 | 64.563 |

## Per Group

| size | file_key | sample_seed | selector_policy | top_k | attempts_used | solved_any_strict60 | first_solved_rank | stop_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 410 | 3sat_2.cnf | 1729 | combined_low_logprob_high_weightstd | 2 | 1 | True | 1 | 57.134 |
| 410 | 3sat_2.cnf | 1730 | combined_low_logprob_high_weightstd | 2 | 1 | True | 1 | 39.463 |
| 410 | 3sat_2.cnf | 1731 | combined_low_logprob_high_weightstd | 2 | 1 | True | 1 | 15.290 |
| 440 | 3sat_8.cnf | 1729 | combined_low_logprob_high_weightstd | 2 | 2 | False | -1 | 120.000 |
| 440 | 3sat_8.cnf | 1730 | combined_low_logprob_high_weightstd | 2 | 2 | False | -1 | 120.000 |
| 440 | 3sat_8.cnf | 1731 | combined_low_logprob_high_weightstd | 2 | 1 | True | 1 | 35.491 |

Artifacts:

```text
runs/analysis/benchmark_march_budgeted_sample_selector/budgeted_selector_raw.csv
runs/analysis/benchmark_march_budgeted_sample_selector/budgeted_selector_candidates.csv
runs/analysis/benchmark_march_budgeted_sample_selector/budgeted_selector_summary.csv
```
