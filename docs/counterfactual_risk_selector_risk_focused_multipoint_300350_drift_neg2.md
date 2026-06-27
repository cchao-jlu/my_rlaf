# Counterfactual Risk Selector

这个 selector 使用 same-evidence counterfactual outcome labels 训练。
它是保守策略：negative labels 被加权放大，threshold 的选择顺序是
先看 solved count，再看 lost solved instances，然后看 recovered
timeouts，最后才看 runtime。

特征：

- warmup_c2000_base_rho_mean
- warmup_c2000_delta_abs_mean
- warmup_c2000_event_gate_mean
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c2000_rho_event_corr
- warmup_c2000_rho_event_top10_overlap
- warmup_c1000_minus_warmup_c500_delta_abs_mean
- warmup_c1000_minus_warmup_c500_event_entropy_norm
- warmup_c1000_minus_warmup_c500_event_top10_mass
- warmup_c1000_minus_warmup_c500_rho_event_corr
- warmup_c2000_minus_warmup_c1000_delta_abs_mean
- warmup_c2000_minus_warmup_c1000_event_entropy_norm
- warmup_c2000_minus_warmup_c1000_event_top10_mass
- warmup_c2000_minus_warmup_c1000_rho_event_corr

## 标签计数

| size | n | eligible | positive | negative | neutral | warmup_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 100 | 89 | 1 | 29 | 59 | 11 |
| 350 | 100 | 91 | 7 | 20 | 64 | 9 |

## 标签原因计数

| size | reason | count |
| --- | --- | --- |
| 300 | neutral | 59 |
| 300 | easy_slowdown | 19 |
| 300 | warmup_solved | 11 |
| 300 | slowdown | 10 |
| 300 | hard_speedup | 1 |
| 350 | neutral | 64 |
| 350 | easy_slowdown | 11 |
| 350 | warmup_solved | 9 |
| 350 | slowdown | 6 |
| 350 | recovered_timeout | 5 |
| 350 | lost_solution | 3 |
| 350 | hard_speedup | 2 |

## 全数据拟合 Selector

| threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | delta_solved_vs_adapter | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.2082 | 0.0944 | 132.0000 | 134.0000 | 136.0000 | 4.0000 | 2.0000 | 0.0000 | 4.0000 | 22.2213 | -0.8167 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_adapter_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.0987 | 0.0400 | -0.9200 | 0.1400 | 0.1800 | 0.0268 | 0.8800 | 0.2400 |
| 300 | 0.0804 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0642 | 1.0000 | 0.1000 |
| 350 | 0.1169 | 0.0400 | -0.9200 | 0.1400 | 0.1800 | -0.0106 | 0.8800 | 0.3000 |

## 解读

这应该作为 risk controller 使用，而不是作为 always-enable adapter
的证据。拟合得到的 threshold 应写入 selector checkpoint，
然后在 disjoint instances 上继续评估。
