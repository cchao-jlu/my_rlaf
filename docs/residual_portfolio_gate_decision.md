# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `all-49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/instance_oracle_summary.csv`
- expected residual instances: `49`
- total residual instances: `49`
- oracle solved: `1`
- fail if oracle solved <= `2`
- pass if oracle solved >= `5`
- decision: `fail`
- action: Stop selector tuning for this checkpoint and switch to residual-targeted training.

## By Size

| size | instances | oracle_solved |
| --- | --- | --- |
| 410 | 5 | 1 |
| 425 | 14 | 0 |
| 440 | 30 | 0 |

## Oracle Positives

| family | size | file_key | solved_samples | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 7 | 5.355 | 1729 | 1 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance
model under the residual portfolio protocol. The next work item is
to generate a larger residual pool and train on residual-targeted
objectives before returning to selector experiments.
