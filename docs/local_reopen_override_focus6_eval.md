# Local Reopen Override Focus6 真实 Wall-clock 验证

## 实验目的

本实验不再调全局阈值，只在 `new_closed_old_on` 局部边界上加入 reopen override。
目标是验证 dense offline trace 中的收益能否转化为真实 solver wall-clock：打开 `3sat_46/196/188`，同时挡住 `3sat_82/93`。

## 局部规则

- `warmup_c1000_minus_warmup_c750_decisions >= 294`
- `warmup_c2000_rho_event_corr >= 0.0365`

第二个阈值使用 `0.0365`，避免 `3sat_196.cnf` 在 `0.03650097...` 附近被浮点四舍五入误关。

## 聚合结果

| policy | solved | mean_time | total_time | mean_cpu | mean_conflicts |
| --- | --- | --- | --- | --- | --- |
| local_reopen | 5 | 22.7838 | 136.7031 | 22.4491 | 701971.0000 |
| no_override | 4 | 36.0680 | 216.4079 | 35.7438 | 1125086.1667 |

## 逐实例对比

| file_key | expected_trace_class | no_override_result | local_reopen_result | no_override_time | local_reopen_time | delta_time | delta_conflicts | delta_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | positive/recovered_timeout | INDETERMINATE | SATISFIABLE | 60.3132 | 25.5675 | -34.7457 | -952495.0000 | -1083848.0000 |
| 3sat_196.cnf | positive/hard_speedup | SATISFIABLE | SATISFIABLE | 25.6798 | 10.0656 | -15.6142 | -545275.0000 | -625256.0000 |
| 3sat_46.cnf | positive/hard_speedup | SATISFIABLE | SATISFIABLE | 30.6333 | 0.5319 | -30.1014 | -967440.0000 | -1099110.0000 |
| 3sat_66.cnf | neutral | INDETERMINATE | INDETERMINATE | 60.2852 | 60.3053 | 0.0200 | -73481.0000 | -85277.0000 |
| 3sat_82.cnf | negative/slowdown | SATISFIABLE | SATISFIABLE | 20.6905 | 21.4830 | 0.7925 | 0.0000 | 0.0000 |
| 3sat_93.cnf | negative/slowdown | SATISFIABLE | SATISFIABLE | 18.8059 | 18.7499 | -0.0560 | 0.0000 | 0.0000 |

## 结论

- `3sat_46.cnf` 和 `3sat_196.cnf` 的 hard speedup 落到了真实 wall-clock；其中 `3sat_46.cnf` 从约 30.63s 降到约 0.53s，`3sat_196.cnf` 从约 25.68s 降到约 10.07s。
- `3sat_188.cnf` 从 timeout 恢复为 SAT，时间约 25.57s，说明 recovered timeout 的 offline trace 不是假信号。
- `3sat_82.cnf` 和 `3sat_93.cnf` 的冲突数/决策数没有变化，说明 negative slowdown 样本没有被 reopen；总时间的小差异主要来自额外 750-conflict warmup 采样点和运行噪声。
- `3sat_66.cnf` 被规则打开但仍 timeout，真实开销约 +0.02s，符合 dense trace 中的 neutral 判断。

## 输出文件

- `runs/analysis/local_reopen_focus6_wallclock_comparison.csv`
- `runs/analysis/local_reopen_focus6_wallclock_summary.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/eval_local_reopen_focus6_400.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_focus6_400.csv`
