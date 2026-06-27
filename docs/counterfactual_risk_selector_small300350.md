# Counterfactual Risk Selector

这个 selector 使用 same-evidence counterfactual outcome labels 训练。

它是保守策略：negative labels 被加权放大，threshold 选择顺序是先看 solved count，再看 lost solved instances，然后看 recovered timeouts，最后才看 runtime。

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
| 0.1947 | 0.1596 | 73.0000 | 71.0000 | 73.0000 | 0.0000 | 2.0000 | 0.0000 | 0.0000 | 20.5323 | -0.6301 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_adapter_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.1945 | -0.1400 | 0.8600 | 0.1400 | 0.0000 | 0.1087 | 0.8600 | 0.1800 |
| 300 | 0.1867 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0298 | 1.0000 | 0.1800 |
| 350 | 0.2026 | -0.1400 | 0.8600 | 0.1400 | 0.0000 | 0.1911 | 0.8600 | 0.2200 |

## 解读

这应该作为 risk controller 使用，而不是作为 always-enable adapter 的证据。拟合得到的 threshold 应写入 selector checkpoint，然后在 disjoint instances 上继续评估。
