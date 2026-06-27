# Contrastive Outcome Selector 结果

这是第一版 outcome-driven selector 实验。它只使用已有干净 CSV：one-shot 作为 base branch，fixed-rho 作为 adapter branch，selector 基于 counterfactual outcome labels 训练。

标签规则：

- positive：adapter 解出 base timeout，或 adapter time <= 0.80 * base time
- negative：adapter 丢失 base-solved 实例，或 adapter time >= 1.10 * base time
- neutral：classifier loss 忽略，但仍用于 threshold selection

## 标签计数

| size | positive | negative | neutral | n |
| --- | --- | --- | --- | --- |
| 300 | 5 | 35 | 160 | 200 |
| 350 | 13 | 17 | 170 | 200 |

## Repeated-Split 汇总

| feature_set | heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_fixed_rho_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | selector_delta_vs_fixed_rho_mean | beats_fixed_rho_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_rho_mean | 300+350 | 0.2699 | -0.1800 | 1.2400 | 0.8800 | 0.7000 | -0.1903 | 0.0084 | 0.5600 |
| base_rho_mean | 300 | 0.2756 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.2139 | 0.0377 | 0.4400 |
| base_rho_mean | 350 | 0.2642 | -0.1800 | 1.2400 | 0.8800 | 0.7000 | -0.1668 | -0.0209 | 0.5800 |
| base_rho_mean+num_vars_log | 300+350 | 0.1573 | -0.2000 | 1.2200 | 0.9200 | 0.7200 | -0.0926 | 0.1061 | 0.3000 |
| base_rho_mean+num_vars_log | 300 | 0.0300 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0222 | 0.2294 | 0.0600 |
| base_rho_mean+num_vars_log | 350 | 0.2846 | -0.2000 | 1.2200 | 0.9200 | 0.7200 | -0.1630 | -0.0172 | 0.5600 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 300+350 | 0.2177 | -0.7000 | 0.7200 | 0.9400 | 0.2400 | -0.0147 | 0.1840 | 0.1600 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 300 | 0.1928 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.1172 | 0.1343 | 0.1600 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 350 | 0.2426 | -0.7000 | 0.7200 | 0.9400 | 0.2400 | 0.0878 | 0.2336 | 0.1600 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 300+350 | 0.1659 | -0.9600 | 0.4600 | 1.2000 | 0.2400 | -0.0078 | 0.1909 | 0.1400 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 300 | 0.0758 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0691 | 0.1825 | 0.0800 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | 350 | 0.2560 | -0.9600 | 0.4600 | 1.2000 | 0.2400 | 0.0535 | 0.1993 | 0.2200 |

## 解读

- 该实验检查 outcome labels 是否优于手写 risk labels。关键对比对象是 `docs/risk_controller_selector_results.md` 中的 `base_rho_mean` risk controller。
- 最好的 contrastive 变体仍然只用简单的 `base_rho_mean` 特征，但略弱于之前的手写 risk controller：`delta_solved_vs_base=-0.18`，`delta_vs_fixed_rho=+0.0084s`。
- outcome labels 非常稀疏，尤其是 3SAT-300（`5` 个 positive 对 `35` 个 negative）。这会让线性 selector 对 split variance 很敏感，也解释了为什么更丰富的 micro features 反而过拟合。
- 如果 contrastive labels 不能改善 held-out solved/time tradeoff，瓶颈大概率是 rollout evidence 的可预测性，而不只是 objective。
