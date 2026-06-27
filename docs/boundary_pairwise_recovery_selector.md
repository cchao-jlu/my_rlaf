# Pairwise Recovery Selector

该实验固定旧 compact 的 risk gate，只替换 recovery detector。
训练目标由 BCE 和 pairwise ranking 组成，明确要求 hard recovery / hard speedup 的 recovery score 高于 easy slowdown / lost solution。

## 特征

- warmup_c500_decisions
- warmup_c1000_decisions
- warmup_c2000_decisions
- warmup_c500_propagations
- warmup_c1000_propagations
- warmup_c2000_propagations
- warmup_c2000_cpu_time
- warmup_c2000_base_rho_mean
- warmup_c2000_delta_abs_mean
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c2000_rho_event_corr
- warmup_c1000_minus_warmup_c500_event_top10_mass
- warmup_c2000_minus_warmup_c1000_event_top10_mass

## Boundary 标签计数

| boundary_source | size | boundary_reason | count |
| --- | --- | --- | --- |
| counterfactual_trace | 300 | easy_slowdown | 30 |
| counterfactual_trace | 300 | hard_speedup | 1 |
| counterfactual_trace | 300 | slowdown | 7 |
| counterfactual_trace | 350 | easy_slowdown | 15 |
| counterfactual_trace | 350 | hard_recovery | 5 |
| counterfactual_trace | 350 | hard_speedup | 2 |
| counterfactual_trace | 350 | lost_solution | 3 |
| counterfactual_trace | 350 | slowdown | 8 |
| counterfactual_trace | 400 | easy_slowdown | 6 |
| counterfactual_trace | 400 | hard_recovery | 8 |
| counterfactual_trace | 400 | hard_speedup | 4 |
| counterfactual_trace | 400 | lost_solution | 5 |
| counterfactual_trace | 400 | slowdown | 3 |
| full400_audit | 400 | easy_slowdown | 22 |
| full400_audit | 400 | hard_recovery | 6 |
| full400_audit | 400 | hard_speedup | 6 |
| full400_audit | 400 | slowdown | 3 |

## 训练集选择情况

| threshold | labelled | positive | negative | selected_fraction | selected_positive | selected_negative |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5569 | 134.0000 | 32.0000 | 102.0000 | 0.1567 | 15.0000 | 6.0000 |

## Full400 重点样本审计

| file_key | pairwise_risk_prob | pairwise_recovery_prob | pairwise_risk_threshold | pairwise_recovery_threshold | pairwise_use_adapter |
| --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | 0.2927 | 0.5159 | 0.7953 | 0.5569 | 0 |
| 3sat_163.cnf | 0.6994 | 0.7182 | 0.7953 | 0.5569 | 1 |
| 3sat_25.cnf | 0.5259 | 0.2164 | 0.7953 | 0.5569 | 0 |
| 3sat_82.cnf | 0.7791 | 0.6002 | 0.7953 | 0.5569 | 1 |
| 3sat_88.cnf | 0.5932 | 0.3956 | 0.7953 | 0.5569 | 0 |

## Full400 Offline 估算

| policy | selected | base_solved | old_solved_est | pairwise_solved_est | lost_solution_est | recovered_timeout_est | pairwise_mean_est | delta_mean_vs_old_est | opened_vs_old | closed_vs_old |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pairwise_boundary_recovery_offline | 37 | 50 | 56 | 55 | 0 | 5 | 46.5707 | 0.3241 | 9 | 16 |

## 当前判断

- pairwise ranking 已经修复目标边界：`3sat_163.cnf` 被打开，`3sat_25.cnf` 和 `3sat_88.cnf` 被关闭。
- 但它也关闭了 `3sat_89.cnf` 这类强 recovery，offline 估算解出数仍低于旧 compact。
- 因此该 checkpoint 暂时不替换主线；它应作为 recovery score 可被排序约束修复的诊断实验。

## 输出文件

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecovery/best.pt`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecovery/config.yaml`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecovery/pairwise_recovery_training_frame.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecovery/pairwise_recovery_focus_audit.csv`
