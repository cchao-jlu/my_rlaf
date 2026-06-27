# Non-Neural Schedule From Neural Budget

Scope: derive a fixed same-budget non-neural rerun schedule from the
allocated residual CPU budget of the frozen neural portfolio. Use this
schedule before held-out evaluation; do not tune it on held-out results.

Neural summary: `runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/expanded_early_trace_summary.csv`.
Neural summary SHA256: `1c7f02883ab0114505d7b25ba08f5db2009b98805652158d1f726259533d6096`.
Source split: `dev`.
Budget aggregation: `mean`.
Attempt limit: 60.
Solver order: march, cadical.

## Schedule

```text
march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16
```

## Budget Summary

| instances | neural_summary | neural_summary_sha256 | source_split | selector_spec | selector_spec_sha256 | aggregation | neural_budget_min | neural_budget_mean | neural_budget_max | selected_budget | schedule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | runs/analysis/tmp_residual_audit_smoke/neural_selector_dev_seed1729/expanded_early_trace_summary.csv | 1c7f02883ab0114505d7b25ba08f5db2009b98805652158d1f726259533d6096 | dev | runs/analysis/tmp_residual_audit_smoke/selector_spec.json | 06fe7227a196d91be49c6196316a9fe17b960b1cd33a924513d9f72490fb526f | mean | 496.000 | 496.000 | 496.000 | 496.000 | march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16 |

