# Ultra-Conservative Counterfactual Risk Selector

这个 selector 使用 same-evidence counterfactual outcome labels 训练，是当前主线 risk-controller 候选。

它比 balanced conservative 更保守：negative labels 权重更高，且最多只允许选择 10% eligible instances。目标是先压住 lost base-solved 风险，而不是追求更高 adapter 使用率。

特征：

- `base_rho_mean`
- `delta_mu_abs_mean`
- `event_gate_mean`
- `event_top10_mass`
- `rho_event_corr`

## 标签计数

| size | n | eligible | positive | negative | neutral | warmup_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 50 | 48 | 6 | 9 | 33 | 2 |
| 350 | 50 | 46 | 5 | 12 | 29 | 4 |

## 全数据拟合 Selector

| threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | delta_solved_vs_adapter | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.1378 | 0.0851 | 73.0000 | 71.0000 | 73.0000 | 0.0000 | 2.0000 | 0.0000 | 0.0000 | 21.0363 | -0.1261 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_adapter_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.0477 | -0.0200 | 0.9800 | 0.0200 | 0.0000 | -0.0312 | 0.9800 | 0.3200 |
| 300 | 0.0458 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0017 | 1.0000 | 0.2000 |
| 350 | 0.0496 | -0.0200 | 0.9800 | 0.0200 | 0.0000 | -0.0656 | 0.9800 | 0.2000 |

## 解读

这应该作为 risk controller 使用，而不是作为 always-enable adapter 的证据。它的当前价值是几乎不丢 base-solved 实例，并在 repeated split 平均时间上略优于 base。下一步应把该 threshold 写入 checkpoint，并在 disjoint 300/350/400 上评估。
