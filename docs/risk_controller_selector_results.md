# Risk-Controller Selector 结果

本文档记录 risk-controller selector 的离线 repeated-split 检查。实验从 3SAT-300 和 3SAT-350 中各取 100 个实例训练，然后在 held-out halves 上评估。脚本先抽取一次 conflict-budgeted warmup trace feature cache，再复用干净的 one-shot/fixed-rho CSV 做离线 repeated-split evaluation。

微观 trace 特征：

- `event_entropy_norm`
- `event_top05_mass`
- `event_top10_mass`
- `rho_event_corr`
- `rho_event_top10_overlap`

策略：

- `time_selector`：旧目标，预测 adapter runtime 更低时选择 adapter。
- `risk_controller`：加权标签加 threshold；优先最大化 solved count，其次最小化 lost solved instances，最后才看 mean time。

## 汇总

| feature_set | policy | heldout | selected_fraction_mean | selector_delta_solved_vs_base_mean | selector_delta_solved_vs_fixed_rho_mean | lost_solution_mean | recovered_timeout_mean | selector_delta_vs_base_mean | selector_delta_vs_fixed_rho_mean | beats_fixed_rho_time_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_rho_mean | time_selector | 300+350 | 0.3572 | -0.1800 | 1.2400 | 1.0600 | 0.8800 | -0.2203 | -0.0216 | 0.6400 |
| base_rho_mean | time_selector | 300 | 0.3640 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.2276 | 0.0240 | 0.5200 |
| base_rho_mean | time_selector | 350 | 0.3504 | -0.1800 | 1.2400 | 1.0600 | 0.8800 | -0.2130 | -0.0672 | 0.6000 |
| base_rho_mean | risk_controller | 300+350 | 0.2293 | 0.0000 | 1.4200 | 0.7800 | 0.7800 | -0.2038 | -0.0051 | 0.5800 |
| base_rho_mean | risk_controller | 300 | 0.2302 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.2048 | 0.0468 | 0.3400 |
| base_rho_mean | risk_controller | 350 | 0.2284 | 0.0000 | 1.4200 | 0.7800 | 0.7800 | -0.2029 | -0.0570 | 0.6200 |
| base_rho_mean+num_vars_log | time_selector | 300+350 | 0.3853 | -0.6200 | 0.8000 | 1.4600 | 0.8400 | -0.0815 | 0.1172 | 0.3200 |
| base_rho_mean+num_vars_log | time_selector | 300 | 0.2436 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0603 | 0.1913 | 0.2600 |
| base_rho_mean+num_vars_log | time_selector | 350 | 0.5270 | -0.6200 | 0.8000 | 1.4600 | 0.8400 | -0.1028 | 0.0430 | 0.3400 |
| base_rho_mean+num_vars_log | risk_controller | 300+350 | 0.1667 | -0.0800 | 1.3400 | 0.8400 | 0.7600 | -0.1503 | 0.0485 | 0.3400 |
| base_rho_mean+num_vars_log | risk_controller | 300 | 0.1008 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0845 | 0.1671 | 0.1200 |
| base_rho_mean+num_vars_log | risk_controller | 350 | 0.2326 | -0.0800 | 1.3400 | 0.8400 | 0.7600 | -0.2160 | -0.0702 | 0.5600 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 300+350 | 0.5628 | -1.0600 | 0.3600 | 1.6200 | 0.5600 | -0.0311 | 0.1676 | 0.3400 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 300 | 0.4738 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.1203 | 0.1313 | 0.3000 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 350 | 0.6518 | -1.0600 | 0.3600 | 1.6200 | 0.5600 | 0.0580 | 0.2039 | 0.3200 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 300+350 | 0.2000 | -0.7400 | 0.6800 | 0.9000 | 0.1600 | -0.0089 | 0.1898 | 0.1600 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 300 | 0.1700 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0936 | 0.1580 | 0.1000 |
| base_rho_mean+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 350 | 0.2300 | -0.7400 | 0.6800 | 0.9000 | 0.1600 | 0.0758 | 0.2216 | 0.2000 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 300+350 | 0.5265 | -1.2800 | 0.1400 | 1.8400 | 0.5600 | -0.0017 | 0.1970 | 0.2400 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 300 | 0.3744 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0828 | 0.1688 | 0.2400 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | time_selector | 350 | 0.6786 | -1.2800 | 0.1400 | 1.8400 | 0.5600 | 0.0794 | 0.2252 | 0.1400 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 300+350 | 0.1569 | -0.6600 | 0.7600 | 0.7800 | 0.1200 | 0.0024 | 0.2011 | 0.1600 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 300 | 0.1066 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | -0.0425 | 0.2091 | 0.1000 |
| base_rho_mean+num_vars_log+event_entropy_norm+event_top05_mass+event_top10_mass+rho_event_corr+rho_event_top10_overlap | risk_controller | 350 | 0.2072 | -0.6600 | 0.7600 | 0.7800 | 0.1200 | 0.0473 | 0.1932 | 0.2600 |

## 解读

- 加入 5 个 micro trace features 没有改善 repeated-split selector。最佳安全/时间折中仍来自更简单的 `base_rho_mean` risk controller。
- micro-feature risk controller 变得过于保守：它降低了选择率，但也压掉了 timeout recovery，因此 solved-count protection 反而变差。
- risk-controller target 应先看 solved-count protection，再看 runtime。更低 selected fraction 只有在减少 lost solved instances 且不抹掉 timeout recovery 时才有意义。
- 如果 micro trace features 不能改善 held-out 稳定性，瓶颈大概率是 warmup evidence 质量或 trace-label 设计，而不是 selector objective 本身。
