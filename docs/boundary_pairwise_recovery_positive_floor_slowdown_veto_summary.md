# Boundary Pairwise + Slowdown Veto 结果汇总

本轮目标是修复 compact stable recovery detector 的边界排序问题：保住 `3sat_163/89/46` 这类 recovery / hard speedup，同时挡掉 `3sat_25/88` 这类 easy slowdown。

## 关键结论

- Pairwise recovery ranking 能修复 `3sat_163` 与 `3sat_25/88` 的排序错误。
- Positive-floor 阈值进一步保住 `3sat_89` 和 `3sat_46`，但会打开更多 slowdown 候选。
- 叠加 slowdown veto 后，offline full400 估算回到旧 compact 的 `56 solved`，且均值估算略优。
- 7 个重点实例真实 wall-clock 验证通过：`3sat_89` 从 timeout 恢复到 `0.531s`，`3sat_163` 仍恢复，`3sat_25/88` 没有被错误放大。
- 但完整 full400 分批真实评估只有 `52/200`，没有追上旧 compact；focus 结果不能当作最终证据，因为在线审计显示 `3sat_89` 在最终 selector 下并未稳定开启 adapter。
- 这条分支应作为边界修复诊断/负结果保留，论文主线仍保持 old compact 或 full400-calibrated compact。

## Offline Full400 估算

| policy | selected_before_veto | vetoed | selected | base_solved | old_solved_est | selector_solved_est | lost_solution_est | recovered_timeout_est | base_mean | old_mean_est | selector_mean_est | delta_mean_vs_old_est |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| positive_floor_pairwise_recovery_slowdown_veto | 62 | 25 | 37 | 50 | 56 | 56 | 0 | 6 | 47.751662 | 46.246573 | 46.112309 | -0.134264 |

## 真实 Full400 分批结果

| method | n | solved | mean_time | median_time | mean_cpu_time | mean_gpu_time | mean_conflicts | mean_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| oneshot | 200 | 50 | 47.751662 | 60.765965 | 46.944073 | 0.807589 | 1360590.180000 | 1553591.675000 |
| old_compact | 200 | 56 | 46.348389 | 60.880623 | 45.429551 | 0.846797 | 1310319.785000 | 1496544.645000 |
| old_compact_calibrated | 200 | 56 | 46.346545 | 60.868893 | 45.404186 | 0.869192 | 1311840.760000 | 1498268.615000 |
| pairwise_veto_actual | 200 | 52 | 46.875523 | 60.959291 | 45.956313 | 0.846720 | 1302398.595000 | 1487153.925000 |

## 真实 Full400 相对旧 Compact 的结果

| n | old_solved | pairwise_solved | delta_solved_vs_old | old_mean_time | pairwise_mean_time | delta_mean_time_vs_old | faster_both_solved | slower_both_solved | tie_both_solved | recovered_vs_old | lost_vs_old | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | 56 | 52 | -4 | 46.348389 | 46.875523 | 0.527134 | 22 | 23 | 7 | 0 | 4 | 144 |

## Offline 估算与真实结果偏差

| n | offline_solved_est | actual_solved | solved_est_mismatch | offline_est_actual_timeout | offline_timeout_actual_solved |
| --- | --- | --- | --- | --- | --- |
| 200 | 56 | 52 | 4 | 4 | 0 |

## Online Feature Proxy 复核

旧 offline 估算直接复用了 old compact 的 full400 selector feature cache，再套 pairwise/veto 权重；这和最终 checkpoint 在线评估时的 multi-point feature 不一致。重新用最终 checkpoint 提取 feature 后，proxy 估算从 `56 solved` 降到 `54 solved`，更接近真实 `52 solved`。

| n | selected | base_solved | old_solved | proxy_solved | actual_solved | base_mean | old_mean | proxy_mean | actual_mean | proxy_actual_solved_mismatch | proxy_solved_actual_timeout | proxy_timeout_actual_solved |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | 49 | 50 | 56 | 54 | 52 | 47.751662 | 46.348389 | 46.680611 | 46.875523 | 2 | 2 | 0 |

## Online Feature Proxy 与真实结果仍不一致的样本

| file_key | selector_use_adapter | risk_prob | recovery_prob | slowdown_prob | base_solved | base_time | old_solved | old_time | online_feature_proxy_solved | actual_solved | actual_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | 0 | 0.796813 | 0.130861 | 0.287896 | True | 60.049018 | True | 59.494184 | True | False | 61.091410 |
| 3sat_89.cnf | 1 | 0.593619 | 0.459462 | 0.086555 | False | 60.763306 | True | 0.972039 | True | False | 60.985450 |

## 重点样本 Offline 决策

| file_key | outcome | risk_prob | recovery_prob | slowdown_prob | use_before_veto | slowdown_veto | use_adapter |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | slower_both_solved | 0.292693 | 0.515942 | 0.106216 | True | False | True |
| 3sat_163.cnf | recovered_timeout | 0.699415 | 0.718187 | 0.047417 | True | False | True |
| 3sat_25.cnf | slower_both_solved | 0.525899 | 0.216358 | 0.126511 | False | False | False |
| 3sat_46.cnf | faster_both_solved | 0.556280 | 0.384490 | 0.068033 | True | False | True |
| 3sat_82.cnf | slower_both_solved | 0.779136 | 0.600151 | 0.075714 | True | False | True |
| 3sat_88.cnf | tie_both_solved | 0.593232 | 0.395577 | 0.308447 | True | True | False |
| 3sat_89.cnf | recovered_timeout | 0.593619 | 0.394044 | 0.042998 | True | False | True |

## 重点样本真实结果

| file_key | old_result | pairwise_result | old_time | pairwise_time | delta_time_vs_old | outcome_vs_old |
| --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | SATISFIABLE | SATISFIABLE | 41.082554 | 4.469628 | -36.612926 | faster_both_solved |
| 3sat_163.cnf | SATISFIABLE | SATISFIABLE | 29.293494 | 30.950278 | 1.656785 | slower_both_solved |
| 3sat_25.cnf | SATISFIABLE | SATISFIABLE | 1.981157 | 1.864128 | -0.117029 | faster_both_solved |
| 3sat_46.cnf | SATISFIABLE | SATISFIABLE | 1.057535 | 30.631111 | 29.573576 | slower_both_solved |
| 3sat_82.cnf | SATISFIABLE | SATISFIABLE | 36.087994 | 35.180332 | -0.907662 | faster_both_solved |
| 3sat_88.cnf | SATISFIABLE | SATISFIABLE | 1.016990 | 1.183464 | 0.166474 | slower_both_solved |
| 3sat_89.cnf | SATISFIABLE | INDETERMINATE | 0.972039 | 60.985450 | 60.013411 | lost_vs_old |

## Focus Wall-Clock 汇总

| n | solved | mean_time | mean_cpu_time |
| --- | --- | --- | --- |
| 7 | 7 | 14.741150 | 14.401465 |

## Focus Wall-Clock 明细

| file_key | Result | time | CPU time | conflicts | decisions | refinement CPU time | refinement GPU time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | SATISFIABLE | 4.591611 | 4.254960 | 135171.000000 | 155254.000000 | 0.074673 | 0.257595 |
| 3sat_163.cnf | SATISFIABLE | 29.219880 | 28.878900 | 915021.000000 | 1050086.000000 | 0.079002 | 0.257595 |
| 3sat_25.cnf | SATISFIABLE | 1.331543 | 0.992285 | 41249.000000 | 47888.000000 | 0.077280 | 0.257595 |
| 3sat_46.cnf | SATISFIABLE | 31.234047 | 30.896100 | 977212.000000 | 1110702.000000 | 0.075969 | 0.257595 |
| 3sat_82.cnf | SATISFIABLE | 35.701104 | 35.357700 | 1090841.000000 | 1251869.000000 | 0.081426 | 0.257595 |
| 3sat_88.cnf | SATISFIABLE | 0.578626 | 0.247751 | 10969.000000 | 13071.000000 | 0.068897 | 0.257595 |
| 3sat_89.cnf | SATISFIABLE | 0.531241 | 0.182559 | 8641.000000 | 10334.000000 | 0.086704 | 0.257595 |

## 完整 Full400 重跑状态

- `eval_positive_floor_pairwise_slowdown_veto_full400.csv` 存在，但其时间戳早于最终 `config.yaml` 刷新，属于旧错误校准下的结果，不作为有效结论。
- 本轮已按 4 个 50 实例批次完成正式 full400 重跑，并合并为 `runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv`。
- 分批真实结果为 `52/200`、均值 `46.8755s`，低于旧 compact 的 `56/200`、`46.3484s`；因此 pairwise+veto 暂时不能替换主线。
- 旧 offline 估算使用 stale selector feature cache，高估到 `56 solved`；用最终 checkpoint 重新提取 online feature 后，proxy 估算降为 `54 solved`，只剩 2 个真实偏差。
- 注意：检测到 `runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto/eval_positive_floor_pairwise_slowdown_veto_full400_rerun.csv` 已存在，需要确认时间戳晚于最终 config 后才能使用。

## 下一步

1. 主结果不要切到 pairwise+veto；保留旧 compact / full400-calibrated compact 作为当前主线。
2. 后续 threshold sweep 必须基于 `positive_floor_pairwise_slowdown_veto_full400_online_selector_features.csv` 这类最终 checkpoint 在线特征，不能复用旧 compact cache。
3. 后续若继续改 selector，应优先修正真实 wall-clock 与离线反事实标签之间的分布偏差，而不是继续增加 selector 结构复杂度。
