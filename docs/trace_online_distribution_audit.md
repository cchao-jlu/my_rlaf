# Trace / Online Selector Feature 分布审计

本报告只使用最终 checkpoint 在线提取的 selector feature cache；旧 compact cache 不参与决策。
目的不是继续增加 selector 复杂度，而是检查 counterfactual trace 与真实 online rollout evidence 是否存在分布偏差。

## 输入

- online feature cache：`runs/analysis/positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv`
- instance audit：`runs/analysis/online_pairwise_veto_threshold_sweep_instance_audit.csv`
- training traces：
  - `data/counterfactual_trace/boundary_focused_pairwise_trace.csv`
  - `data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_outcomes.csv`
  - `data/counterfactual_trace/hard_recovery_400_train_outcomes.csv`
- selector feature 数：`25`

## Outcome 分组

| outcome_group | n | use_adapter | mean_max_abs_train_z | median_max_abs_train_z | mean_outside_features | mean_risk_prob | mean_recovery_prob | mean_slowdown_prob |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kept_solved | 49 | 12 | 2.270312 | 1.902389 | 3.612245 | 0.577113 | 0.296427 | 0.391969 |
| kept_timeout | 147 | 34 | 1.815601 | 1.738118 | 1.782313 | 0.514654 | 0.296023 | 0.422951 |
| lost_solution | 1 | 0 | 1.335411 | 1.335411 | 1.000000 | 0.796813 | 0.130861 | 0.287896 |
| recovered_timeout | 3 | 3 | 1.476124 | 1.585755 | 0.333333 | 0.545064 | 0.708929 | 0.054891 |

## 漂移最大的特征

| feature | train_mean | online_mean | mean_shift_z | train_p05 | train_p95 | online_min | online_max | online_outside_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warmup_c2000_cpu_time | 0.035522 | 0.038240 | 0.392294 | 0.025786 | 0.043228 | 0.004097 | 0.046853 | 0.135000 |
| warmup_c2000_minus_warmup_c1000_event_top10_mass | 0.000048 | 0.001208 | 0.087450 | -0.023578 | 0.020897 | -0.040375 | 0.037413 | 0.130000 |
| warmup_c2000_propagations | 110599.473810 | 120813.430000 | 0.477290 | 92328.000000 | 126791.950000 | 14565.000000 | 134180.000000 | 0.125000 |
| warmup_c1000_minus_warmup_c500_event_top10_mass | -0.001813 | -0.002413 | -0.042646 | -0.023966 | 0.021091 | -0.043741 | 0.034259 | 0.115000 |
| warmup_c2000_minus_warmup_c1000_event_top05_mass | 0.002662 | 0.002715 | 0.005609 | -0.011806 | 0.017950 | -0.028175 | 0.026370 | 0.115000 |
| warmup_c1000_propagations | 55910.705952 | 60673.615000 | 0.498921 | 48223.850000 | 63786.000000 | 14565.000000 | 68900.000000 | 0.110000 |
| warmup_c500_propagations | 28139.913095 | 30351.355000 | 0.530928 | 24090.000000 | 31719.000000 | 14565.000000 | 34952.000000 | 0.105000 |
| warmup_c500_decisions | 629.876190 | 646.210000 | 0.231386 | 600.000000 | 681.000000 | 339.000000 | 742.000000 | 0.105000 |
| warmup_c1000_decisions | 1207.938095 | 1242.930000 | 0.203111 | 1173.000000 | 1295.050000 | 339.000000 | 1363.000000 | 0.105000 |
| warmup_c2000_base_rho_std | 2.364665 | 2.364665 | 0.000000 | 2.043132 | 2.705456 | 1.799744 | 2.899756 | 0.100000 |
| warmup_c2000_base_rho_range | 28.458048 | 28.458048 | 0.000000 | 24.401823 | 32.877833 | 21.892002 | 34.617153 | 0.100000 |
| warmup_c2000_event_conf_learnt_log_max | 7.089349 | 7.089349 | 0.000000 | 6.985084 | 7.230744 | 4.990433 | 7.276556 | 0.100000 |

## 重点实例

| file_key | outcome_group | use_adapter | base_solved | selected_solved | risk_prob | recovery_prob | slowdown_prob | max_abs_train_z | max_abs_feature | outside_p05_p95_features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_25.cnf | kept_solved | 0 | 1 | 1 | 0.525899 | 0.166484 | 0.422137 | 2.280534 | warmup_c2000_base_rho_range | 5 |
| 3sat_88.cnf | kept_solved | 1 | 1 | 1 | 0.593232 | 0.641168 | 0.162272 | 2.015778 | warmup_c1000_minus_warmup_c500_event_top10_mass | 4 |
| 3sat_89.cnf | kept_timeout | 1 | 0 | 0 | 0.593619 | 0.459462 | 0.086555 | 2.002115 | warmup_c2000_minus_warmup_c1000_event_top10_mass | 2 |
| 3sat_122.cnf | lost_solution | 0 | 1 | 0 | 0.796813 | 0.130861 | 0.287896 | 1.335411 | warmup_c2000_base_rho_std | 1 |
| 3sat_163.cnf | recovered_timeout | 1 | 0 | 1 | 0.699415 | 0.798261 | 0.039995 | 1.585755 | recovery_prob | 0 |

## 结论

- 如果 `online_outside_fraction` 高，说明 online rollout evidence 已经明显偏离训练 trace；这种情况下继续调阈值意义有限。
- 如果 lost/recovered 实例的 `max_abs_train_z` 较高，说明边界样本处于训练分布尾部，需要改 trace 覆盖或 rollout 采样，而不是堆 selector 容量。
- 下一步应优先补在线一致的 counterfactual trace：使用与正式评估相同 checkpoint、相同 multi-point feature、相同 selector feature override 路径，并增加 full400 边界样本。

## 输出文件

- `runs/analysis/trace_online_distribution_audit_feature_summary.csv`
- `runs/analysis/trace_online_distribution_audit_instance_audit.csv`
- `runs/analysis/trace_online_distribution_audit_group_summary.csv`
