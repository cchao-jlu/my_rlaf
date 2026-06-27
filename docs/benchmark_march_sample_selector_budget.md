# March Sample Selector Budget Simulation

Scope: offline budget simulation over the focused March sampled-portfolio
artifacts. It does not run new SAT solving. Each policy ranks the 16
sampled guidances for an instance/seed group, executes only top-k in that
rank order, caps each attempt at nominal 60 seconds, and stops after the
first strict-60 solve.

This is a deployability gate for the oracle sampled-portfolio signal: if
cheap ranking cannot recover complement cases at small k, the evidence
remains an oracle diagnostic rather than a top-conference performance
claim.

## Top-k Summary

| policy | top_k | oracle_positive_groups | positive_recovered_groups | positive_recall | mean_stop_cpu_capped | mean_stop_cpu_capped_positive | mean_first_hit_rank_positive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| combined_low_logprob_high_weightstd | 2 | 5 | 4.000 | 0.800 | 90.928 | 50.227 | 1.250 |
| low_log_prob | 2 | 5 | 4.000 | 0.800 | 91.675 | 52.020 | 1.250 |
| high_weight_std | 2 | 5 | 4.000 | 0.800 | 94.539 | 58.894 | 1.250 |
| combined_low_logprob_high_weightstd | 4 | 5 | 4.000 | 0.800 | 170.928 | 74.227 | 1.250 |
| low_log_prob | 4 | 5 | 4.000 | 0.800 | 171.675 | 76.020 | 1.250 |
| high_weight_std | 4 | 5 | 4.000 | 0.800 | 174.539 | 82.894 | 1.250 |
| high_log_weight_abs_mean | 4 | 5 | 4.000 | 0.800 | 181.627 | 99.904 | 1.750 |
| random | 4 | 5 | 3.882 | 0.776 | 184.515 | 106.836 | 1.760 |
| random | 2 | 5 | 3.259 | 0.652 | 100.497 | 73.193 | 1.319 |
| combined_low_logprob_high_weightstd | 1 | 5 | 3.000 | 0.600 | 50.817 | 37.961 | 1.000 |
| high_weight_std | 1 | 5 | 3.000 | 0.600 | 50.817 | 37.961 | 1.000 |
| low_log_prob | 1 | 5 | 3.000 | 0.600 | 51.564 | 39.754 | 1.000 |
| high_phase_mode_match | 1 | 5 | 3.000 | 0.600 | 53.386 | 44.125 | 1.000 |
| high_phase_mode_match | 2 | 5 | 3.000 | 0.600 | 98.386 | 68.125 | 1.000 |
| high_log_weight_abs_mean | 2 | 5 | 3.000 | 0.600 | 100.817 | 73.961 | 1.333 |
| high_phase_mode_match | 4 | 5 | 3.000 | 0.600 | 188.386 | 116.125 | 1.000 |
| random | 1 | 5 | 2.453 | 0.491 | 54.475 | 46.739 | 1.000 |
| high_log_weight_abs_mean | 1 | 5 | 2.000 | 0.400 | 52.691 | 42.459 | 1.000 |

## Instance-Level Recovery

| policy | top_k | size | file_key | oracle_positive_seed_groups | recovered_positive_seed_groups | instance_hit_any_seed | mean_stop_cpu_capped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high_phase_mode_match | 1 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 33.542 |
| high_phase_mode_match | 2 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 33.542 |
| high_phase_mode_match | 4 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 33.542 |
| high_weight_std | 1 | 410 | 3sat_2.cnf | 3 | 2.000 | True | 30.764 |
| high_weight_std | 2 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 45.653 |
| high_weight_std | 4 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 45.653 |
| low_log_prob | 1 | 410 | 3sat_2.cnf | 3 | 2.000 | True | 33.753 |
| low_log_prob | 2 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 34.196 |
| low_log_prob | 4 | 410 | 3sat_2.cnf | 3 | 3.000 | True | 34.196 |
| random | 1 | 410 | 3sat_2.cnf | 3 | 2.198 | True | 39.781 |
| random | 2 | 410 | 3sat_2.cnf | 3 | 2.780 | True | 50.647 |
| random | 4 | 410 | 3sat_2.cnf | 3 | 2.993 | True | 53.755 |
| high_phase_mode_match | 1 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 60.000 |
| high_phase_mode_match | 2 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 120.000 |
| high_phase_mode_match | 4 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 240.000 |
| high_weight_std | 1 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 60.000 |
| high_weight_std | 2 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 120.000 |
| high_weight_std | 4 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 240.000 |
| low_log_prob | 1 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 60.000 |
| low_log_prob | 2 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 120.000 |
| low_log_prob | 4 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 240.000 |
| random | 1 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 60.000 |
| random | 2 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 120.000 |
| random | 4 | 410 | 3sat_3.cnf | 0 | 0.000 | False | 240.000 |
| high_phase_mode_match | 1 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 60.000 |
| high_phase_mode_match | 2 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 120.000 |
| high_phase_mode_match | 4 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 240.000 |
| high_weight_std | 1 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 60.000 |
| high_weight_std | 2 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 120.000 |
| high_weight_std | 4 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 240.000 |
| low_log_prob | 1 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 60.000 |
| low_log_prob | 2 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 120.000 |
| low_log_prob | 4 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 240.000 |
| random | 1 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 60.000 |
| random | 2 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 120.000 |
| random | 4 | 410 | 3sat_8.cnf | 0 | 0.000 | False | 240.000 |
| high_phase_mode_match | 1 | 440 | 3sat_8.cnf | 2 | 0.000 | False | 60.000 |
| high_phase_mode_match | 2 | 440 | 3sat_8.cnf | 2 | 0.000 | False | 120.000 |
| high_phase_mode_match | 4 | 440 | 3sat_8.cnf | 2 | 0.000 | False | 240.000 |
| high_weight_std | 1 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 52.504 |
| high_weight_std | 2 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 92.504 |
| high_weight_std | 4 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 172.504 |
| low_log_prob | 1 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 52.504 |
| low_log_prob | 2 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 92.504 |
| low_log_prob | 4 | 440 | 3sat_8.cnf | 2 | 1.000 | True | 172.504 |
| random | 1 | 440 | 3sat_8.cnf | 2 | 0.255 | True | 58.118 |
| random | 2 | 440 | 3sat_8.cnf | 2 | 0.479 | True | 111.342 |
| random | 4 | 440 | 3sat_8.cnf | 2 | 0.889 | True | 204.305 |

## Decision

- Cheap static ranking is not yet a deployable top-conference result.
  It recovers most strict-60 positive seed groups at top-2/top-4,
  but random top-4 is close on this small focused set.
- The signal is strong enough only for the next experimental gate: a
  real fixed-budget runner on the focused complement cases, generating
  samples, ranking before solving, and executing only fixed top-k
  without per-instance tuning.
- If the real runner does not preserve the complement hits under a
  fixed wall-clock budget, the next method step should add early
  solver-trace features or retrain toward strong-union-unsolved cases.

Artifacts:

```text
runs/analysis/benchmark_march_sample_selector_features/budgeted_selector_simulation.csv
runs/analysis/benchmark_march_sample_selector_features/budgeted_selector_summary.csv
runs/analysis/benchmark_march_sample_selector_features/budgeted_selector_instance_summary.csv
```
