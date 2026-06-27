# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_targeted_iter22_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22/instance_oracle_summary.csv`
- source sha256: `680018d0b331089c831194c7ce55f2abb3149162544a00999a4a7acc5dbff865`
- checkpoint: `runs/GNN_March_3SAT_ResidualTargetedIter22/last.pt`
- checkpoint sha256: `4cf7537b86c86d8caec832d064ee4704388ec881874d30950930d832fa329058`
- expected residual instances: `49`
- total residual instances: `49`
- oracle solved: `2`
- fail if oracle solved <= `2`
- pass if oracle solved >= `5`
- decision: `fail`
- action: Stop selector tuning for this checkpoint and switch to model-side coverage/diversity training.

## By Size

| size | instances | oracle_solved |
| --- | --- | --- |
| 410 | 5 | 1 |
| 425 | 14 | 1 |
| 440 | 30 | 0 |

## Oracle Positives

| family | size | file_key | solved_samples | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 6 | 1.050 | 1729 | 11 |
| 3sat | 425 | 3sat_28.cnf | 1 | 59.237 | 1729 | 3 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance model under
the residual portfolio protocol. The residual large split already exists; the
next work item is a new model-side objective, currently
`configs/config_train_rlaf_march_residual_coverage_diverse.yaml`, before any
return to selector experiments.
