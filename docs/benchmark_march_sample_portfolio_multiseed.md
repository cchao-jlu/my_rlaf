# March Sample-Portfolio Multiseed Gate

Scope: expanded stochastic-sampling gate for the existing March-trained
policy on transition-band instances unsolved by the March/CaDiCaL union.
This is an oracle-sample diagnostic, not a trained selector.

Sample seeds: [1730, 1731]; solver seed: 1729; samples per seed: 16.

## Input Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 440 | 3sat_8.cnf |

## Per-Seed Size Summary

| family | size | sample_seed | instances | num_samples | solved_any | mean_solved_samples | max_solved_samples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 440 | 1730 | 1 | 16 | 1 | 1.000 | 1 |
| 3sat | 440 | 1731 | 1 | 16 | 1 | 2.000 | 2 |

## Oracle Size Summary

| family | size | instances | sample_seeds | samples_per_seed | total_samples_per_instance | oracle_solved_any | mean_solved_samples | max_solved_samples | max_solved_seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 440 | 1 | 2 | 16 | 32 | 1 | 3.000 | 3 | 2 |

## Oracle Instance Summary

| family | size | file_key | sample_seeds | samples_per_seed | total_samples | solved_samples | solved_seeds | solved_any | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 440 | 3sat_8.cnf | 2 | 16 | 32 | 3 | 2 | True | 37.512 | 1731 | 0 |

## Decision

- Oracle sampled March guidance solves 1/1
  strong-union both-unknown transition instances.
- This is the model-side route to pursue: increase sample coverage and
  learn a cheap selector or stopping rule for sampled guidances.

Generated artifacts:

```text
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw_samples_all.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/instance_seed_summary.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/instance_oracle_summary.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/size_seed_summary.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/size_oracle_summary.csv
```
