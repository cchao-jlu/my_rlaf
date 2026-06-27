# Residual Oracle Union Diagnostic

This diagnostic unions oracle coverage across checkpoint-specific all-49
sample-portfolio diagnostics. It is not a deployable selector result.

- checkpoint diagnostics: `6`
- residual instances: `49`
- union oracle solved: `2`

## Sources

| tag | path |
| --- | --- |
| residual_proxy_cap10_iter0 | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0/instance_oracle_summary.csv |
| residual_targeted_iter22 | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22/instance_oracle_summary.csv |
| residual_coverage_diverse_best_iter2 | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instance_oracle_summary.csv |
| residual_elite_replay_coverage_diverse_best_iter2 | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv |
| residual_progress_diverse | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse/instance_oracle_summary.csv |
| residual_contrastive_replay_coverage_diverse_best_iter2 | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv |

## Per Checkpoint

| tag | total | oracle_solved | solved_samples |
| --- | --- | --- | --- |
| residual_contrastive_replay_coverage_diverse_best_iter2 | 49 | 2 | 8 |
| residual_coverage_diverse_best_iter2 | 49 | 2 | 10 |
| residual_elite_replay_coverage_diverse_best_iter2 | 49 | 2 | 10 |
| residual_targeted_iter22 | 49 | 2 | 7 |
| residual_progress_diverse | 49 | 1 | 8 |
| residual_proxy_cap10_iter0 | 49 | 1 | 8 |

## By Size

| tag | size | total | oracle_solved | solved_samples |
| --- | --- | --- | --- | --- |
| residual_contrastive_replay_coverage_diverse_best_iter2 | 410 | 5 | 1 | 7 |
| residual_contrastive_replay_coverage_diverse_best_iter2 | 425 | 14 | 1 | 1 |
| residual_contrastive_replay_coverage_diverse_best_iter2 | 440 | 30 | 0 | 0 |
| residual_coverage_diverse_best_iter2 | 410 | 5 | 1 | 9 |
| residual_coverage_diverse_best_iter2 | 425 | 14 | 1 | 1 |
| residual_coverage_diverse_best_iter2 | 440 | 30 | 0 | 0 |
| residual_elite_replay_coverage_diverse_best_iter2 | 410 | 5 | 1 | 9 |
| residual_elite_replay_coverage_diverse_best_iter2 | 425 | 14 | 1 | 1 |
| residual_elite_replay_coverage_diverse_best_iter2 | 440 | 30 | 0 | 0 |
| residual_progress_diverse | 410 | 5 | 1 | 8 |
| residual_progress_diverse | 425 | 14 | 0 | 0 |
| residual_progress_diverse | 440 | 30 | 0 | 0 |
| residual_proxy_cap10_iter0 | 410 | 5 | 1 | 8 |
| residual_proxy_cap10_iter0 | 425 | 14 | 0 | 0 |
| residual_proxy_cap10_iter0 | 440 | 30 | 0 | 0 |
| residual_targeted_iter22 | 410 | 5 | 1 | 6 |
| residual_targeted_iter22 | 425 | 14 | 1 | 1 |
| residual_targeted_iter22 | 440 | 30 | 0 | 0 |

## Union Positives

| family | size | file_key | total_solved_samples | min_best_time |
| --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 47 | 1.05 |
| 3sat | 425 | 3sat_28.cnf | 4 | 39.52 |
