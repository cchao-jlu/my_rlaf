# March Sample Selector Feature Audit

Scope: cheap selector-feature audit for sampled March guidance. It joins
policy-sampling features with focused sampled-portfolio outcomes. This
does not train a selector and does not run additional SAT solving.

## Ranking Summary

| metric | ascending | groups | positive_groups | positive_top1_hits | positive_top2_hits | positive_top4_hits | mean_first_hit_rank_positive |
| --- | --- | --- | --- | --- | --- | --- | --- |
| log_prob | True | 12 | 5 | 3 | 4 | 4 | 2.200 |
| weight_std | False | 12 | 5 | 3 | 4 | 4 | 2.200 |
| phase_mode_match | False | 12 | 5 | 3 | 3 | 3 | 4.000 |
| log_weight_abs_mean | False | 12 | 5 | 2 | 3 | 4 | 3.000 |
| log_weight_abs_mean | True | 12 | 5 | 2 | 2 | 4 | 3.400 |
| log_prob | False | 12 | 5 | 1 | 2 | 3 | 4.600 |
| weight_std | True | 12 | 5 | 1 | 2 | 3 | 3.600 |
| phase_mode_match | True | 12 | 5 | 0 | 2 | 4 | 3.200 |

## Interpretation

- At least one cheap policy-derived metric ranks strict-60 successful
  samples near the top on the focused complement cases.
- This supports trying a learned sample selector / stopping rule before
  changing the March checkpoint objective.

Artifacts:

```text
runs/analysis/benchmark_march_sample_selector_features/focused_sample_features.csv
runs/analysis/benchmark_march_sample_selector_features/focused_selector_ranking.csv
runs/analysis/benchmark_march_sample_selector_features/focused_selector_summary.csv
```
