# Residual Portfolio Gate Decision

Scope: pre-registered oracle diagnostic `residual_contrastive_replay_coverage_diverse_best_iter2_all49` for the
current March-trained checkpoint on a March/CaDiCaL both-unknown
residual pilot.

- source: `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- source sha256: `4cd462a4ab9778ac9dbe1e69f1bd7bde42fe717168504902ef9b1ba5c750eb64`
- checkpoint: `runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2/best.pt`
- checkpoint sha256: `56dba0670da653bea7a8106c5db2ca34463928bd8f13c5bb302dd47da313562c`
- oracle checkpoint sha256: `56dba0670da653bea7a8106c5db2ca34463928bd8f13c5bb302dd47da313562c`
- oracle checkpoint provenance check: `pass`
- training config audit: `not-provided`
- training config audit sha256: `not-provided`
- training config audit checks: `not-provided`
- training config audit failures: `not-provided`
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
| 3sat | 410 | 3sat_12.cnf | 7 | 10.534 | 1729 | 11 |
| 3sat | 425 | 3sat_28.cnf | 1 | 50.646 | 1729 | 10 |

## Protocol Consequence

The current checkpoint is not a viable top-conference performance
model under the residual portfolio protocol. The next work item is
to generate a larger residual pool and train on residual-targeted
objectives before returning to selector experiments.
