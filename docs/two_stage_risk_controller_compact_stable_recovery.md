# 双阶段风险控制器

该 selector 分成两个 head：

- easy-risk gate：预测 adapter 是否可能造成 lost/slowdown，触发后直接 fallback；
- hard-recovery detector：预测 adapter 是否可能恢复 timeout 或明显加速 hard instance。

最终策略是：`use_adapter = recovery_detector && !risk_gate`。

训练作用域：`risk_all_recovery_focused`。
阶段模型：`linear`。

recovery 标签模式：`timeout_recovery_with_speedup_aux`。
risk 训练 size filter：`all`。
recovery 训练 size filter：`350,400`。
recovered_timeout 稳定性标注：`runs/analysis/recovered_timeout_stability_summary.csv`。

## 阶段训练样本计数

| stage | n | positive | negative |
| --- | --- | --- | --- |
| risk | 298 | 61 | 237 |
| recovery | 164 | 19 | 145 |

## recovered_timeout 稳定性权重

| size | n | stable_recovered | recovered_rate_mean | stability_weight_mean |
| --- | --- | --- | --- | --- |
| 350 | 5 | 5 | 1.0000 | 1.0000 |
| 400 | 8 | 8 | 1.0000 | 1.0000 |

## Risk Gate 特征

- warmup_c500_solved
- warmup_c1000_solved
- warmup_c2000_base_rho_std
- warmup_c2000_base_rho_range
- warmup_c2000_event_conf_learnt_log_max
- warmup_c2000_minus_warmup_c1000_delta_abs_mean
- warmup_c2000_minus_warmup_c1000_delta_mu_abs_mean
- warmup_c2000_minus_warmup_c1000_propagations
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c1000_minus_warmup_c500_rho_event_top10_overlap
- warmup_c2000_minus_warmup_c1000_event_top05_mass

## Recovery Detector 特征

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

## 标签计数

| size | n | eligible | positive | negative | neutral | warmup_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 100 | 89 | 1 | 29 | 59 | 11 |
| 350 | 100 | 91 | 7 | 20 | 64 | 9 |
| 400 | 120 | 118 | 12 | 12 | 94 | 2 |

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
| 400 | neutral | 94 |
| 400 | recovered_timeout | 8 |
| 400 | lost_solution | 5 |
| 400 | easy_slowdown | 4 |
| 400 | hard_speedup | 4 |
| 400 | slowdown | 3 |
| 400 | warmup_solved | 2 |

## 全数据拟合

| risk_threshold | recovery_threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5957 | 0.5170 | 0.1174 | 158.0000 | 163.0000 | 164.0000 | 6.0000 | 0.0000 | 6.0000 | 32.1308 | -1.0655 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.1035 | 0.7200 | 0.3600 | 1.0800 | -0.3019 | 0.8800 | 0.7600 |
| 300 | 0.0240 | 0.0000 | 0.0000 | 0.0000 | 0.0327 | 1.0000 | 0.0800 |
| 350 | 0.0751 | 0.0600 | 0.1000 | 0.1600 | -0.0083 | 0.9000 | 0.2000 |
| 400 | 0.1858 | 0.6600 | 0.2600 | 0.9200 | -0.7811 | 0.9000 | 0.8000 |

