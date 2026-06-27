# March Sample-Portfolio Multiseed Gate

Scope: expanded stochastic-sampling gate for the existing March-trained
policy on transition-band instances unsolved by the March/CaDiCaL union.
This is an oracle-sample diagnostic, not a trained selector.

Sample seeds: [1729]; solver seed: 1729; samples per seed: 16.

Partial summary: False.

## Input Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf |
| 3sat | 410 | 3sat_15.cnf |
| 3sat | 410 | 3sat_24.cnf |
| 3sat | 410 | 3sat_29.cnf |
| 3sat | 410 | 3sat_38.cnf |
| 3sat | 425 | 3sat_0.cnf |
| 3sat | 425 | 3sat_12.cnf |
| 3sat | 425 | 3sat_15.cnf |
| 3sat | 425 | 3sat_16.cnf |
| 3sat | 425 | 3sat_19.cnf |
| 3sat | 425 | 3sat_22.cnf |
| 3sat | 425 | 3sat_23.cnf |
| 3sat | 425 | 3sat_28.cnf |
| 3sat | 425 | 3sat_35.cnf |
| 3sat | 425 | 3sat_41.cnf |
| 3sat | 425 | 3sat_44.cnf |
| 3sat | 425 | 3sat_48.cnf |
| 3sat | 425 | 3sat_7.cnf |
| 3sat | 425 | 3sat_9.cnf |
| 3sat | 440 | 3sat_0.cnf |
| 3sat | 440 | 3sat_10.cnf |
| 3sat | 440 | 3sat_11.cnf |
| 3sat | 440 | 3sat_12.cnf |
| 3sat | 440 | 3sat_14.cnf |
| 3sat | 440 | 3sat_15.cnf |
| 3sat | 440 | 3sat_16.cnf |
| 3sat | 440 | 3sat_17.cnf |
| 3sat | 440 | 3sat_19.cnf |
| 3sat | 440 | 3sat_2.cnf |
| 3sat | 440 | 3sat_21.cnf |
| 3sat | 440 | 3sat_22.cnf |
| 3sat | 440 | 3sat_24.cnf |
| 3sat | 440 | 3sat_27.cnf |
| 3sat | 440 | 3sat_28.cnf |
| 3sat | 440 | 3sat_29.cnf |
| 3sat | 440 | 3sat_31.cnf |
| 3sat | 440 | 3sat_35.cnf |
| 3sat | 440 | 3sat_36.cnf |
| 3sat | 440 | 3sat_38.cnf |
| 3sat | 440 | 3sat_4.cnf |
| 3sat | 440 | 3sat_42.cnf |
| 3sat | 440 | 3sat_46.cnf |
| 3sat | 440 | 3sat_47.cnf |
| 3sat | 440 | 3sat_48.cnf |
| 3sat | 440 | 3sat_49.cnf |
| 3sat | 440 | 3sat_5.cnf |
| 3sat | 440 | 3sat_6.cnf |
| 3sat | 440 | 3sat_7.cnf |
| 3sat | 440 | 3sat_9.cnf |

## Per-Seed Size Summary

| family | size | sample_seed | instances | num_samples | solved_any | mean_solved_samples | max_solved_samples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 1729 | 5 | 16 | 1 | 1.800 | 9 |
| 3sat | 425 | 1729 | 14 | 16 | 1 | 0.071 | 1 |
| 3sat | 440 | 1729 | 30 | 16 | 0 | 0.000 | 0 |

## Oracle Size Summary

| family | size | instances | sample_seeds | samples_per_seed | total_samples_per_instance | oracle_solved_any | mean_solved_samples | max_solved_samples | max_solved_seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 5 | 1 | 16 | 16 | 1 | 1.800 | 9 | 1 |
| 3sat | 425 | 14 | 1 | 16 | 16 | 1 | 0.071 | 1 | 1 |
| 3sat | 440 | 30 | 1 | 16 | 16 | 0 | 0.000 | 0 | 0 |

## Oracle Instance Summary

| family | size | file_key | sample_seeds | samples_per_seed | total_samples | solved_samples | solved_seeds | solved_any | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 1 | 16 | 16 | 9 | 1 | True | 1.412 | 1729 | 15 |
| 3sat | 410 | 3sat_15.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_24.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_29.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_38.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_0.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_12.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_15.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_16.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_19.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_22.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_23.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_28.cnf | 1 | 16 | 16 | 1 | 1 | True | 59.844 | 1729 | 15 |
| 3sat | 425 | 3sat_35.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_41.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_44.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_48.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_7.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_9.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_0.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_10.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_11.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_12.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_14.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_15.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_16.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_17.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_19.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_2.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_21.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_22.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_24.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_27.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_28.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_29.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_31.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_35.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_36.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_38.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_4.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_42.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_46.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_47.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_48.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_49.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_5.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_6.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_7.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_9.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |

## Budget Summary

| family | size | instances | capped_solver_cpu_total | neural_generation_wall_time |
| --- | --- | --- | --- | --- |
| 3sat | 410 | 5 | 4455.837 | 7.514 |
| 3sat | 425 | 14 | 13439.844 | 20.930 |
| 3sat | 440 | 30 | 28800.000 | 44.349 |

## Decision

- Oracle sampled March guidance solves 2/49
  strong-union both-unknown transition instances.
- This fails the pre-registered all-49 pilot gate (`<=2/49`).
- Do not tune the selector on this checkpoint. The first-pass coverage/diversity
  objective still only reaches 2/49, so the next route is a stronger model-side
  objective change, then rerun the same oracle gate for that exact checkpoint.

Generated artifacts:

```text
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/raw/
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instances/
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/raw_samples_all.csv
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instance_seed_summary.csv
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instance_oracle_summary.csv
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/size_seed_summary.csv
runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/size_oracle_summary.csv
```
