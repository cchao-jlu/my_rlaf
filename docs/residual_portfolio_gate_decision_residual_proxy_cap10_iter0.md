# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_proxy_cap10_iter0_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0/instance_oracle_summary.csv`
- source sha256: `53e98fde8c82321cc3004391e08345ffa3fe704ca278336ba344f769014f50c0`
- checkpoint: `runs/GNN_March_3SAT_ResidualProxyCap10/last.pt`
- checkpoint sha256: `95ef6cdd8d4c9de38de044018f2d072f64c5eb6f1abebbb530067e22b52a39b2`
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
| 3sat | 410 | 3sat_12.cnf | 8 | 10.875 | 1729 | 5 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance
model under the residual portfolio protocol. The next work item is
to generate a larger residual pool and train on residual-targeted
objectives before returning to selector experiments.
