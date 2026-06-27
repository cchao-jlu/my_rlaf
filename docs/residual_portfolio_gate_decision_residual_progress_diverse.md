# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_progress_diverse_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse/instance_oracle_summary.csv`
- source sha256: `0455d8b6111213d576198bf121cb7afa2afc970a3dbe2797472d06df1da76653`
- checkpoint: `runs/GNN_March_3SAT_ResidualProgressDiverse/best.pt`
- checkpoint sha256: `f9ac184722fe5785c3b084c2e173e8d799ae13a7d2b1a151887e66d4d662997a`
- oracle checkpoint sha256: `f9ac184722fe5785c3b084c2e173e8d799ae13a7d2b1a151887e66d4d662997a`
- oracle checkpoint provenance check: `pass`
- training config audit: `not-provided`
- training config audit sha256: `not-provided`
- training config audit checks: `not-provided`
- training config audit failures: `not-provided`
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
| 3sat | 410 | 3sat_12.cnf | 8 | 6.510 | 1729 | 2 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance
model under the residual portfolio protocol. The next work item is
to generate a larger residual pool and train on residual-targeted
objectives before returning to selector experiments.
