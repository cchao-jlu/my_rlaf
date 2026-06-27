# Non-Neural Schedule From Neural Budget

Scope: derive a fixed same-budget non-neural rerun schedule from the
allocated residual CPU budget of the frozen neural portfolio. Use this
schedule before held-out evaluation; do not tune it on held-out results.

Neural summary: `runs/analysis/tmp_residual_audit_smoke/neural.csv`.
Budget aggregation: `mean`.
Attempt limit: 60.
Solver order: march, cadical.

## Schedule

```text
march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16
```

## Budget Summary

| instances | aggregation | neural_budget_min | neural_budget_mean | neural_budget_max | selected_budget | schedule |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | mean | 496.000 | 496.000 | 496.000 | 496.000 | march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:60,cadical:60,march:16 |

