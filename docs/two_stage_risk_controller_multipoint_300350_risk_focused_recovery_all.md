# Two-Stage Risk Controller

该 selector 分成两个线性头：

- easy-risk gate：预测 adapter 是否可能造成 lost/slowdown，触发后直接 fallback；
- hard-recovery detector：预测 adapter 是否可能恢复 timeout 或明显加速 hard instance。

最终策略是：`use_adapter = recovery_detector && !risk_gate`。

训练作用域：`risk_focused_recovery_all`。

## Stage 训练样本计数

| stage | n | positive | negative |
| --- | --- | --- | --- |
| risk | 122 | 45 | 77 |
| recovery | 180 | 8 | 172 |

## Risk Gate 特征

- warmup_c500_decisions
- warmup_c1000_decisions
- warmup_c2000_decisions
- warmup_c500_cpu_time
- warmup_c1000_cpu_time
- warmup_c2000_cpu_time
- warmup_c2000_delta_abs_mean
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c1000_minus_warmup_c500_event_entropy_norm
- warmup_c2000_minus_warmup_c1000_event_entropy_norm

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

## 全数据拟合

| risk_threshold | recovery_threshold | selected_fraction | base_solved | adapter_solved | selector_solved | delta_solved_vs_base | lost_solution | recovered_timeout | selector_mean | delta_vs_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.9534 | 0.3586 | 0.1111 | 132.0000 | 134.0000 | 135.0000 | 3.0000 | 0.0000 | 3.0000 | 22.2997 | -0.7383 |

## Repeated-Split 诊断

| heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | keeps_base_solved_rate | beats_base_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300+350 | 0.1038 | 0.3800 | 0.1000 | 0.4800 | -0.0193 | 0.9200 | 0.3400 |
| 300 | 0.0284 | 0.0000 | 0.0000 | 0.0000 | 0.0047 | 1.0000 | 0.1200 |
| 350 | 0.1791 | 0.3800 | 0.1000 | 0.4800 | -0.0432 | 0.9200 | 0.3600 |

