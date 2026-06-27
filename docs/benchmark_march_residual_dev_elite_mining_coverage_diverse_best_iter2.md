# March Sample-Portfolio Multiseed Gate

Scope: expanded stochastic-sampling gate for the existing March-trained
policy on transition-band instances unsolved by the March/CaDiCaL union.
This is an oracle-sample diagnostic, not a trained selector.

Sample seeds: [1729]; solver seed: 1729; samples per seed: 16.

Partial summary: False.

## Input Subset

| family | size | file_key |
| --- | --- | --- |
| 3sat | 410 | 3sat_170.cnf |
| 3sat | 410 | 3sat_242.cnf |
| 3sat | 410 | 3sat_243.cnf |
| 3sat | 410 | 3sat_251.cnf |
| 3sat | 410 | 3sat_30.cnf |
| 3sat | 410 | 3sat_4.cnf |
| 3sat | 410 | 3sat_40.cnf |
| 3sat | 410 | 3sat_58.cnf |
| 3sat | 410 | 3sat_61.cnf |
| 3sat | 410 | 3sat_71.cnf |
| 3sat | 410 | 3sat_76.cnf |
| 3sat | 410 | 3sat_78.cnf |
| 3sat | 425 | 3sat_106.cnf |
| 3sat | 425 | 3sat_108.cnf |
| 3sat | 425 | 3sat_121.cnf |
| 3sat | 425 | 3sat_129.cnf |
| 3sat | 425 | 3sat_134.cnf |
| 3sat | 425 | 3sat_135.cnf |
| 3sat | 425 | 3sat_169.cnf |
| 3sat | 425 | 3sat_172.cnf |
| 3sat | 425 | 3sat_177.cnf |
| 3sat | 425 | 3sat_179.cnf |
| 3sat | 425 | 3sat_192.cnf |
| 3sat | 425 | 3sat_207.cnf |
| 3sat | 425 | 3sat_212.cnf |
| 3sat | 425 | 3sat_216.cnf |
| 3sat | 425 | 3sat_222.cnf |
| 3sat | 425 | 3sat_225.cnf |
| 3sat | 425 | 3sat_235.cnf |
| 3sat | 425 | 3sat_24.cnf |
| 3sat | 425 | 3sat_243.cnf |
| 3sat | 425 | 3sat_273.cnf |
| 3sat | 425 | 3sat_274.cnf |
| 3sat | 425 | 3sat_279.cnf |
| 3sat | 425 | 3sat_286.cnf |
| 3sat | 425 | 3sat_289.cnf |
| 3sat | 425 | 3sat_29.cnf |
| 3sat | 425 | 3sat_292.cnf |
| 3sat | 425 | 3sat_293.cnf |
| 3sat | 425 | 3sat_30.cnf |
| 3sat | 425 | 3sat_38.cnf |
| 3sat | 425 | 3sat_43.cnf |
| 3sat | 425 | 3sat_47.cnf |
| 3sat | 425 | 3sat_61.cnf |
| 3sat | 425 | 3sat_76.cnf |
| 3sat | 425 | 3sat_88.cnf |
| 3sat | 425 | 3sat_92.cnf |
| 3sat | 440 | 3sat_107.cnf |
| 3sat | 440 | 3sat_110.cnf |
| 3sat | 440 | 3sat_130.cnf |
| 3sat | 440 | 3sat_132.cnf |
| 3sat | 440 | 3sat_137.cnf |
| 3sat | 440 | 3sat_140.cnf |
| 3sat | 440 | 3sat_158.cnf |
| 3sat | 440 | 3sat_163.cnf |
| 3sat | 440 | 3sat_168.cnf |
| 3sat | 440 | 3sat_17.cnf |
| 3sat | 440 | 3sat_179.cnf |
| 3sat | 440 | 3sat_180.cnf |
| 3sat | 440 | 3sat_193.cnf |
| 3sat | 440 | 3sat_204.cnf |
| 3sat | 440 | 3sat_206.cnf |
| 3sat | 440 | 3sat_209.cnf |
| 3sat | 440 | 3sat_210.cnf |
| 3sat | 440 | 3sat_223.cnf |
| 3sat | 440 | 3sat_232.cnf |
| 3sat | 440 | 3sat_234.cnf |
| 3sat | 440 | 3sat_235.cnf |
| 3sat | 440 | 3sat_242.cnf |
| 3sat | 440 | 3sat_243.cnf |
| 3sat | 440 | 3sat_249.cnf |
| 3sat | 440 | 3sat_266.cnf |
| 3sat | 440 | 3sat_279.cnf |
| 3sat | 440 | 3sat_284.cnf |
| 3sat | 440 | 3sat_285.cnf |
| 3sat | 440 | 3sat_286.cnf |
| 3sat | 440 | 3sat_291.cnf |
| 3sat | 440 | 3sat_293.cnf |
| 3sat | 440 | 3sat_295.cnf |
| 3sat | 440 | 3sat_3.cnf |
| 3sat | 440 | 3sat_38.cnf |
| 3sat | 440 | 3sat_44.cnf |
| 3sat | 440 | 3sat_54.cnf |
| 3sat | 440 | 3sat_55.cnf |
| 3sat | 440 | 3sat_62.cnf |
| 3sat | 440 | 3sat_66.cnf |
| 3sat | 440 | 3sat_84.cnf |
| 3sat | 440 | 3sat_85.cnf |
| 3sat | 440 | 3sat_87.cnf |
| 3sat | 440 | 3sat_88.cnf |
| 3sat | 440 | 3sat_89.cnf |
| 3sat | 440 | 3sat_94.cnf |
| 3sat | 440 | 3sat_99.cnf |

## Per-Seed Size Summary

| family | size | sample_seed | instances | num_samples | solved_any | mean_solved_samples | max_solved_samples |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 1729 | 12 | 16 | 3 | 2.667 | 16 |
| 3sat | 425 | 1729 | 35 | 16 | 0 | 0.000 | 0 |
| 3sat | 440 | 1729 | 46 | 16 | 4 | 0.174 | 4 |

## Oracle Size Summary

| family | size | instances | sample_seeds | samples_per_seed | total_samples_per_instance | oracle_solved_any | mean_solved_samples | max_solved_samples | max_solved_seeds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 12 | 1 | 16 | 16 | 3 | 2.667 | 16 | 1 |
| 3sat | 425 | 35 | 1 | 16 | 16 | 0 | 0.000 | 0 | 0 |
| 3sat | 440 | 46 | 1 | 16 | 16 | 4 | 0.174 | 4 | 1 |

## Oracle Instance Summary

| family | size | file_key | sample_seeds | samples_per_seed | total_samples | solved_samples | solved_seeds | solved_any | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_170.cnf | 1 | 16 | 16 | 16 | 1 | True | 51.787 | 1729 | 4 |
| 3sat | 410 | 3sat_242.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_243.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_251.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_30.cnf | 1 | 16 | 16 | 1 | 1 | True | 59.424 | 1729 | 8 |
| 3sat | 410 | 3sat_4.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_40.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_58.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_61.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_71.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_76.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 410 | 3sat_78.cnf | 1 | 16 | 16 | 15 | 1 | True | 54.891 | 1729 | 12 |
| 3sat | 425 | 3sat_106.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_108.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_121.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_129.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_134.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_135.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_169.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_172.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_177.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_179.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_192.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_207.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_212.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_216.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_222.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_225.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_235.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_24.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_243.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_273.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_274.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_279.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_286.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_289.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_29.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_292.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_293.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_30.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_38.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_43.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_47.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_61.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_76.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_88.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 425 | 3sat_92.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_107.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_110.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_130.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_132.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_137.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_140.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_158.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_163.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_168.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_17.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_179.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_180.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_193.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_204.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_206.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_209.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_210.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_223.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_232.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_234.cnf | 1 | 16 | 16 | 1 | 1 | True | 11.456 | 1729 | 7 |
| 3sat | 440 | 3sat_235.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_242.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_243.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_249.cnf | 1 | 16 | 16 | 2 | 1 | True | 59.402 | 1729 | 0 |
| 3sat | 440 | 3sat_266.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_279.cnf | 1 | 16 | 16 | 1 | 1 | True | 32.699 | 1729 | 4 |
| 3sat | 440 | 3sat_284.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_285.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_286.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_291.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_293.cnf | 1 | 16 | 16 | 4 | 1 | True | 3.443 | 1729 | 15 |
| 3sat | 440 | 3sat_295.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_3.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_38.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_44.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_54.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_55.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_62.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_66.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_84.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_85.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_87.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_88.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_89.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_94.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |
| 3sat | 440 | 3sat_99.cnf | 1 | 16 | 16 | 0 | 0 | False | 60.000 | -1 | -1 |

## Budget Summary

| family | size | instances | capped_solver_cpu_total | neural_generation_wall_time |
| --- | --- | --- | --- | --- |
| 3sat | 410 | 12 | 11417.324 | 16.021 |
| 3sat | 425 | 35 | 33600.000 | 53.128 |
| 3sat | 440 | 46 | 43950.946 | 70.070 |

## Decision

- Oracle sampled March guidance solves 7/93
  strong-union both-unknown transition instances.
- This is diagnostic coverage only. For the all-49 pilot, apply
  the pre-registered thresholds: `<=2/49` fails, `>=5/49` passes.

Generated artifacts:

```text
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw/
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/instances/
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/instance_seed_summary.csv
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/instance_oracle_summary.csv
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/size_seed_summary.csv
runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/size_oracle_summary.csv
```
