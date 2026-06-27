# Multi-Window Outcome 诊断

这个诊断检查 multi-short-rollout evidence 是否能提升 outcome predictiveness。它在 conflict budgets `100`、`500` 和 `1000` 提取 warmup features，并加入相邻窗口之间的 drift features。这里不运行最终 60s solver evaluation。

## 标签计数

| size | positive | negative | neutral | n |
| --- | --- | --- | --- | --- |
| 300 | 5 | 35 | 160 | 200 |
| 350 | 13 | 17 | 170 | 200 |

## 最佳单变量区分度

| feature | auc | separability_auc | positive_mean | negative_mean |
| --- | --- | --- | --- | --- |
| d100_500_rho_event_corr | 0.7276 | 0.7276 | 0.0276 | -0.0064 |
| d100_500_event_top05_mass | 0.6923 | 0.6923 | 0.0050 | -0.0067 |
| base_rho_mean | 0.6816 | 0.6816 | -0.1345 | -0.2107 |
| mw_1000_rho_event_corr | 0.6741 | 0.6741 | 0.1138 | 0.0243 |
| mw_500_rho_event_corr | 0.6624 | 0.6624 | 0.1050 | 0.0251 |
| d100_500_event_top10_mass | 0.6464 | 0.6464 | -0.0020 | -0.0141 |
| d500_1000_rho_event_corr | 0.6458 | 0.6458 | 0.0088 | -0.0008 |
| d100_500_rho_event_top10_overlap | 0.6442 | 0.6442 | 0.0516 | 0.0228 |
| mw_500_rho_event_top10_overlap | 0.6207 | 0.6207 | 0.4328 | 0.4129 |
| mw_100_rho_event_corr | 0.6090 | 0.6090 | 0.0774 | 0.0315 |
| mw_1000_event_top10_mass | 0.6058 | 0.6058 | 0.4857 | 0.4520 |
| mw_1000_rho_event_top10_overlap | 0.6020 | 0.6020 | 0.4347 | 0.4169 |
| d100_500_event_entropy_norm | 0.4006 | 0.5994 | 0.0107 | 0.0144 |
| mw_500_event_top10_mass | 0.5983 | 0.5983 | 0.4850 | 0.4527 |
| mw_500_event_top05_mass | 0.5780 | 0.5780 | 0.2936 | 0.2730 |

## Repeated-Split Selector 结果

| feature_set | heldout | heldout_separability_auc_mean | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_fixed_rho_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_fixed_rho_mean | beats_fixed_rho_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_rho | 300+350 | 0.6775 | 0.2699 | -0.1800 | 1.2400 | 0.8800 | 0.7000 | 0.0084 | 0.5600 |
| base_rho | 300 | 0.6775 | 0.2756 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0377 | 0.4400 |
| base_rho | 350 | 0.6775 | 0.2642 | -0.1800 | 1.2400 | 0.8800 | 0.7000 | -0.0209 | 0.5800 |
| best_drift_corr | 300+350 | 0.7286 | 0.2643 | -0.5000 | 0.9200 | 0.9600 | 0.4600 | 0.0009 | 0.4800 |
| best_drift_corr | 300 | 0.7286 | 0.2736 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0609 | 0.2800 |
| best_drift_corr | 350 | 0.7286 | 0.2550 | -0.5000 | 0.9200 | 0.9600 | 0.4600 | -0.0591 | 0.4800 |
| base_plus_best_drift_corr | 300+350 | 0.7228 | 0.2506 | -0.4400 | 0.9800 | 0.9400 | 0.5000 | 0.0095 | 0.4400 |
| base_plus_best_drift_corr | 300 | 0.7228 | 0.2542 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0395 | 0.3800 |
| base_plus_best_drift_corr | 350 | 0.7228 | 0.2470 | -0.4400 | 0.9800 | 0.9400 | 0.5000 | -0.0205 | 0.4400 |
| single_500 | 300+350 | 0.5903 | 0.2177 | -0.7000 | 0.7200 | 0.9400 | 0.2400 | 0.1840 | 0.1600 |
| single_500 | 300 | 0.5903 | 0.1928 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1343 | 0.1600 |
| single_500 | 350 | 0.5903 | 0.2426 | -0.7000 | 0.7200 | 0.9400 | 0.2400 | 0.2336 | 0.1600 |
| multi_abs | 300+350 | 0.6583 | 0.2000 | -0.9800 | 0.4400 | 1.2400 | 0.2600 | 0.1494 | 0.2400 |
| multi_abs | 300 | 0.6583 | 0.1640 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0660 | 0.2600 |
| multi_abs | 350 | 0.6583 | 0.2360 | -0.9800 | 0.4400 | 1.2400 | 0.2600 | 0.2328 | 0.2800 |
| multi_drift | 300+350 | 0.6519 | 0.2966 | -0.6800 | 0.7400 | 1.0800 | 0.4000 | 0.0569 | 0.3600 |
| multi_drift | 300 | 0.6519 | 0.3102 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0997 | 0.1800 |
| multi_drift | 350 | 0.6519 | 0.2830 | -0.6800 | 0.7400 | 1.0800 | 0.4000 | 0.0142 | 0.4400 |
| multi_full | 300+350 | 0.6333 | 0.2202 | -0.8400 | 0.5800 | 1.1000 | 0.2600 | 0.1369 | 0.2400 |
| multi_full | 300 | 0.6333 | 0.1982 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1002 | 0.2600 |
| multi_full | 350 | 0.6333 | 0.2422 | -0.8400 | 0.5800 | 1.1000 | 0.2600 | 0.1736 | 0.3200 |

## 当前结论

- `d100_500_rho_event_corr` 是这个诊断中最强的单变量 temporal signal，separability AUC 约为 `0.73`。
- conservative `best_drift_corr` 和 `base_plus_best_drift_corr` selectors 提升了 held-out label separability，但在 solved-count safety 上没有超过简单的 `base_rho` risk controller。
- 因此下一瓶颈是 rollout/label evidence，而不是继续堆 selector feature engineering。

## 解读

- 如果 `multi_abs`、`multi_drift` 或 `multi_full` 相对 `single_500` 不能改善 AUC 和 held-out solved/time metrics，那么当前 warmup evidence 对 selector 的预测性不足。
- 关键指标不是 selected fraction 本身；有用 evidence 必须在减少 lost solved instances 的同时保住 recovered timeouts。
