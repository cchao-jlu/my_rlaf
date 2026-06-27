# Counterfactual Risk Selector

这个 selector 使用 same-evidence counterfactual outcome labels 训练。
它是保守策略：negative labels 被加权放大，threshold 的选择顺序是
先看 solved count，再看 lost solved instances，然后看 recovered
timeouts，最后才看 runtime。

特征：

- base_rho_mean
- delta_mu_abs_mean
- event_gate_mean
- event_top10_mass
- rho_event_corr

## 标签计数

| size | n | eligible | positive | negative | neutral | warmup_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 100 | 92 | 1 | 16 | 75 | 8 |
| 350 | 100 | 94 | 6 | 18 | 70 | 6 |

## 标签原因计数

| size | reason | count |
| --- | --- | --- |
| 300 | neutral | 75 |
| 300 | easy_slowdown | 16 |
| 300 | warmup_solved | 8 |
| 300 | hard_speedup | 1 |
| 350 | neutral | 70 |
| 350 | easy_slowdown | 9 |
| 350 | warmup_solved | 6 |
| 350 | recovered_timeout | 5 |
| 350 | slowdown | 5 |
| 350 | lost_solution | 4 |
| 350 | hard_speedup | 1 |

## 全数据拟合 Selector

| threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | delta_solved_vs_adapter | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.2017 | 0.0968 | 135.0000 | 136.0000 | 136.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | 22.7591 | -0.1287 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_adapter_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.0783 | -0.1200 | -0.8600 | 0.1400 | 0.0200 | 0.0780 | 0.8600 | 0.4200 |
| 300 | 0.0730 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0127 | 1.0000 | 0.5400 |
| 350 | 0.0834 | -0.1200 | -0.8600 | 0.1400 | 0.0200 | 0.1420 | 0.8600 | 0.1800 |

## 解读

这应该作为 risk controller 使用，而不是作为 always-enable adapter
的证据。拟合得到的 threshold 应写入 selector checkpoint，
然后在 disjoint instances 上继续评估。
