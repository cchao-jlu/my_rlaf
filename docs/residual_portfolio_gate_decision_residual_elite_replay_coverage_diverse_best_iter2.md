# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_elite_replay_coverage_diverse_best_iter2_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- source sha256: `64307b510d37c937eb008a2c6ac25e43d45faebb30e3b942ecb9e348e8ab63a0`
- checkpoint: `runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c0d8fa922cfa84133eb7f00f08859da4eeee3442414ec8ab09bd66b437ba2a37`
- oracle checkpoint sha256: `c0d8fa922cfa84133eb7f00f08859da4eeee3442414ec8ab09bd66b437ba2a37`
- oracle checkpoint provenance check: `pass`
- training config audit: `runs/analysis/benchmark_transition_band_residual_large/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.csv`
- training config audit sha256: `486455f20d02b0cf4ac319ef32fc1d766ee1d52fb0961d386544e7c61b60b147`
- training config audit checks: `48`
- training config audit failures: `0`
- expected residual instances: `49`
- total residual instances: `49`
- oracle solved: `2`
- fail if oracle solved <= `2`
- pass if oracle solved >= `5`
- decision: `fail`
- action: Stop selector tuning for this checkpoint and switch to residual-targeted training.

## By Size

| size | instances | oracle_solved |
| --- | --- | --- |
| 410 | 5 | 1 |
| 425 | 14 | 1 |
| 440 | 30 | 0 |

## Oracle Positives

| family | size | file_key | solved_samples | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 9 | 8.146 | 1729 | 4 |
| 3sat | 425 | 3sat_28.cnf | 1 | 39.519 | 1729 | 14 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance
model under the residual portfolio protocol. The next work item is
to generate a larger residual pool and train on residual-targeted
objectives before returning to selector experiments.
