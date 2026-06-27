# March Learned Sample Selector Diagnostic

Scope: offline cross-validated diagnostic for learned sample selection.
It uses existing sampled-guidance outcomes only; it does not run new SAT
solving and does not claim a deployable result.

Split mode: leave_instance; early-trace features: True.

## Summary

| selector | groups | positive_groups | positive_top1_hits | positive_top2_hits | positive_top4_hits | positive_top2_recall | mean_first_hit_rank_positive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_high_deadends | 12 | 5 | 4.000 | 5.000 | 5.000 | 1.000 | 1.200 |
| baseline_high_unitresolve | 12 | 5 | 4.000 | 4.000 | 5.000 | 0.800 | 1.400 |
| learned_rf | 12 | 5 | 4.000 | 4.000 | 4.000 | 0.800 | 1.800 |
| baseline_low_log_prob | 12 | 5 | 3.000 | 4.000 | 4.000 | 0.800 | 2.200 |
| baseline_high_weight_std | 12 | 5 | 3.000 | 4.000 | 4.000 | 0.800 | 2.200 |
| learned_logistic | 12 | 5 | 4.000 | 4.000 | 4.000 | 0.800 | 3.200 |

## Decision

- A simple early-trace baseline is stronger than the learned selector
  on this focused diagnostic.
- The next experiment should expand the strong-union-unsolved sampled
  set and test whether this early-trace signal generalizes before
  investing in a learned selector.

Artifacts:

```text
runs/analysis/benchmark_march_learned_sample_selector/learned_selector_predictions.csv
runs/analysis/benchmark_march_learned_sample_selector/learned_selector_summary.csv
```
