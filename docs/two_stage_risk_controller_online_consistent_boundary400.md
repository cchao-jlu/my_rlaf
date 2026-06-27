# 双阶段风险控制器

该 selector 分成两个 head：

- easy-risk gate：预测 adapter 是否可能造成 lost/slowdown，触发后直接 fallback；
- hard-recovery detector：预测 adapter 是否可能恢复 timeout 或明显加速 hard instance。

最终策略是：`use_adapter = recovery_detector && !risk_gate`。

训练作用域：`risk_all_recovery_focused`。
阶段模型：`linear`。

recovery 标签模式：`timeout_recovery_with_speedup_aux`。
risk 训练 size filter：`all`。
recovery 训练 size filter：`all`。
recovered_timeout 稳定性标注：`未使用`。

## 阶段训练样本计数

| stage | n | positive | negative |
| --- | --- | --- | --- |
| risk | 346 | 77 | 269 |
| recovery | 221 | 29 | 192 |

## recovered_timeout 稳定性权重

_未接入稳定性标注_

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
- warmup_c2000_base_rho_std
- warmup_c2000_base_rho_range
- warmup_c2000_delta_abs_mean
- warmup_c2000_delta_abs_max
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c2000_rho_event_corr
- warmup_c2000_rho_event_top10_overlap
- warmup_c2000_event_conf_learnt_log_mean
- warmup_c2000_event_conf_learnt_log_max
- warmup_c1000_minus_warmup_c500_event_top10_mass
- warmup_c2000_minus_warmup_c1000_event_top10_mass
- warmup_c1000_minus_warmup_c500_rho_event_corr
- warmup_c2000_minus_warmup_c1000_rho_event_corr

## 标签计数

| size | n | eligible | positive | negative | neutral | warmup_solved |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 100 | 89 | 1 | 29 | 59 | 11 |
| 350 | 100 | 91 | 7 | 20 | 64 | 9 |
| 400 | 170 | 166 | 21 | 28 | 117 | 4 |

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
| 400 | neutral | 117 |
| 400 | recovered_timeout | 15 |
| 400 | easy_slowdown | 11 |
| 400 | lost_solution | 10 |
| 400 | slowdown | 7 |
| 400 | hard_speedup | 6 |
| 400 | warmup_solved | 4 |

## 全数据拟合

| risk_threshold | recovery_threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.7645 | 0.7578 | 0.1156 | 185.0000 | 192.0000 | 196.0000 | 11.0000 | 0.0000 | 11.0000 | 30.9422 | -1.9610 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.1094 | 1.7000 | 0.7800 | 2.4800 | -0.6340 | 0.9400 | 0.9000 |
| 300 | 0.0191 | 0.0000 | 0.0000 | 0.0000 | 0.0205 | 1.0000 | 0.0600 |
| 350 | 0.0796 | 0.1400 | 0.2200 | 0.3600 | -0.2538 | 0.8600 | 0.3800 |
| 400 | 0.1745 | 1.5600 | 0.5600 | 2.1200 | -1.1950 | 0.9600 | 0.9000 |

