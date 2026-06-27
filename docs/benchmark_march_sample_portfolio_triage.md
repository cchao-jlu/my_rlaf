# March Sample-Portfolio Triage

Scope: stochastic sampling diagnostic for the existing March-trained
policy. It samples multiple weighted-March guidances per transition-band
strong-union both-unknown instance. This does not train or tune models.

Samples per instance: 4; sampling seed: 1729.

## Input Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 410 | 3sat_2.cnf |
| 3sat | 410 | 3sat_3.cnf |
| 3sat | 410 | 3sat_8.cnf |
| 3sat | 425 | 3sat_10.cnf |
| 3sat | 425 | 3sat_11.cnf |
| 3sat | 440 | 3sat_0.cnf |
| 3sat | 440 | 3sat_11.cnf |
| 3sat | 440 | 3sat_2.cnf |
| 3sat | 440 | 3sat_7.cnf |
| 3sat | 440 | 3sat_8.cnf |
| 3sat | 440 | 3sat_9.cnf |

## Size Summary

| family | size | instances | num_samples | solved_any | mean_solved_samples | max_solved_samples |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3 | 4 | 1 | 0.667 | 2 |
| 3sat | 425 | 2 | 4 | 0 | 0.000 | 0 |
| 3sat | 440 | 6 | 4 | 0 | 0.000 | 0 |

## Instance Summary

| family | size | file_key | samples | solved_samples | solved_any | best_time | best_sample_id | result_values |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_2.cnf | 4 | 2 | True | 31.813 | 3 | SATISFIABLE,TIMEOUT |
| 3sat | 410 | 3sat_3.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 410 | 3sat_8.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 425 | 3sat_10.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 425 | 3sat_11.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_0.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_11.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_2.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_7.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_8.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |
| 3sat | 440 | 3sat_9.cnf | 4 | 0 | False | 60.000 | -1 | TIMEOUT |

## Decision

- Sampled March guidance has nonzero solves on the strong-union
  both-unknown transition subset.
- This is a concrete model-side signal for a neural portfolio / sample
  selection route. The next step is to repeat the sample seed and train
  a selector for these sampled guidances.

Generated artifacts:

```text
runs/analysis/benchmark_march_sample_portfolio_triage/raw_samples.csv
runs/analysis/benchmark_march_sample_portfolio_triage/instance_summary.csv
runs/analysis/benchmark_march_sample_portfolio_triage/size_summary.csv
```
