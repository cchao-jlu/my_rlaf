# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_coverage_diverse_best_iter2_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- source sha256: `8dca7175f0c6e700606981083a8074cfef7f7aa8db2006c7ce32fc393118a3bd`
- checkpoint: `runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f`
- expected residual instances: `49`
- total residual instances: `49`
- oracle solved: `2`
- fail if oracle solved <= `2`
- pass if oracle solved >= `5`
- decision: `fail`
- action: Stop selector tuning for this checkpoint and switch to stronger model-side objective changes.

## By Size

| size | instances | oracle_solved |
| --- | --- | --- |
| 410 | 5 | 1 |
| 425 | 14 | 1 |
| 440 | 30 | 0 |

## Oracle Positives

| family | size | file_key | solved_samples | best_time | best_sample_seed | best_sample_id |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat | 410 | 3sat_12.cnf | 9 | 1.412 | 1729 | 15 |
| 3sat | 425 | 3sat_28.cnf | 1 | 59.844 | 1729 | 15 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance model under
the residual portfolio protocol. The residual large split already exists and
the first-pass coverage/diversity objective did not improve oracle coverage
beyond `2/49`. Do not tune selectors or start same-budget non-neural control
for this checkpoint. The next work item is a stronger model-side objective
change, not another selector/top-k/dead_ends pass.
