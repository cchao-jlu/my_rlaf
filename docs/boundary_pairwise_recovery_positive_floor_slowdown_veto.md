# 简单/中等实例 Slowdown Filter 诊断

本轮目标是在不丢掉 400 完整测试集 6 个 `recovered_timeout` 的前提下，
对已经打开 adapter 的 easy/medium slowdown 做更细的 post-warmup veto。

## 关键判断

- 33 个 slowdown 中，9 个发生在 `selector_use_adapter=1` 的样本上；
- 另外 24 个 slowdown 发生在 `selector_use_adapter=0`，主要来自 warmup/计时开销或噪声，post-warmup filter 无法直接消除；
- 因此本 filter 的有效作用域是这 9 个 selected slowdown。

## 训练设置

- 训练 CSV：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloor/pairwise_recovery_training_frame_trace_only.csv`
- 输出 checkpoint：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerBoundaryPairwiseRecoveryPositiveFloorSlowdownVeto`
- threshold mode：`full400_preserve_recovery`
- threshold：`0.232955`
- bias：`0.064508`
- veto 规则：`slowdown_prob >= threshold` 时关闭 adapter；
- 正例：easy/medium slowdown 与 lost_solution；
- 强保留负例：recovered_timeout 与 hard_speedup。

## 特征

- recovery_prob
- warmup_c2000_event_entropy_norm
- warmup_c2000_event_top10_mass
- warmup_c2000_rho_event_corr
- warmup_c2000_delta_abs_mean
- warmup_c1000_minus_warmup_c500_event_top10_mass
- warmup_c2000_minus_warmup_c1000_event_top10_mass

## Full400 汇总

| metric                               | value      |
| ------------------------------------ | ---------- |
| full400_n                            | 200.000000 |
| original_recovered_timeout           | 6.000000   |
| preserved_recovered_timeout          | 6.000000   |
| original_slowdown_total              | 33.000000  |
| original_selected_slowdown           | 9.000000   |
| vetoed_selected_slowdown             | 1.000000   |
| vetoed_selected_easy_medium_slowdown | 1.000000   |
| post_warmup_est_slowdown_total       | 32.000000  |
| vetoed_faster_both_solved            | 2.000000   |
| base_solved                          | 50.000000  |
| filtered_solved                      | 56.000000  |
| delta_solved_vs_base                 | 6.000000   |
| mean_delta_post_warmup_est_vs_base   | -1.257141  |
| slowdown_margin                      | 0.100000   |

## 6 个 Recovered Timeout

| file_key     | difficulty_bucket | outcome           | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ------------ | ----------------- | ----------------- | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_163.cnf | timeout           | recovered_timeout | -31.526202 | 0.699415  | 0.718187      | 0.057026      | 0             |
| 3sat_188.cnf | timeout           | recovered_timeout | -34.449921 | 0.258579  | 0.644791      | 0.031055      | 0             |
| 3sat_189.cnf | timeout           | recovered_timeout | -45.932897 | 0.588801  | 0.681483      | 0.181907      | 0             |
| 3sat_85.cnf  | timeout           | recovered_timeout | -59.295770 | 0.405947  | 0.711335      | 0.039913      | 0             |
| 3sat_89.cnf  | timeout           | recovered_timeout | -59.791267 | 0.593619  | 0.394044      | 0.113850      | 0             |
| 3sat_97.cnf  | timeout           | recovered_timeout | -48.281786 | 0.529829  | 0.647137      | 0.082822      | 0             |

## 9 个 Selected Slowdown

| file_key     | difficulty_bucket | outcome            | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ------------ | ----------------- | ------------------ | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_82.cnf  | medium(10-30s)    | slower_both_solved | 14.616988  | 0.779136  | 0.600151      | 0.138569      | 0             |
| 3sat_93.cnf  | medium(10-30s)    | slower_both_solved | 2.722067   | 0.752000  | 0.682772      | 0.153850      | 0             |
| 3sat_140.cnf | hard(>=30s)       | slower_both_solved | 1.301342   | 0.292693  | 0.515942      | 0.071454      | 0             |
| 3sat_20.cnf  | medium(10-30s)    | slower_both_solved | 0.561759   | 0.475132  | 0.717474      | 0.109216      | 0             |
| 3sat_22.cnf  | easy(<10s)        | slower_both_solved | 0.370704   | 0.393290  | 0.762445      | 0.013160      | 0             |
| 3sat_125.cnf | easy(<10s)        | slower_both_solved | 0.324392   | 0.198548  | 0.416785      | 0.089942      | 0             |
| 3sat_27.cnf  | easy(<10s)        | slower_both_solved | 0.158550   | 0.261708  | 0.555938      | 0.123203      | 0             |
| 3sat_1.cnf   | easy(<10s)        | slower_both_solved | 0.122872   | 0.766840  | 0.566112      | 0.232955      | 1             |
| 3sat_132.cnf | easy(<10s)        | slower_both_solved | 0.120795   | 0.190343  | 0.391028      | 0.031161      | 0             |

## 被 Filter 拦截的样本

| file_key     | difficulty_bucket | outcome            | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ------------ | ----------------- | ------------------ | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_35.cnf  | timeout           | both_timeout       | 0.164143   | 0.329178  | 0.442683      | 0.636288      | 1             |
| 3sat_58.cnf  | timeout           | both_timeout       | 0.092040   | 0.688927  | 0.549791      | 0.528554      | 1             |
| 3sat_88.cnf  | easy(<10s)        | tie_both_solved    | 0.034690   | 0.593232  | 0.395577      | 0.377892      | 1             |
| 3sat_46.cnf  | hard(>=30s)       | faster_both_solved | -29.685012 | 0.556280  | 0.384490      | 0.366615      | 1             |
| 3sat_66.cnf  | timeout           | both_timeout       | 0.170519   | 0.650250  | 0.612699      | 0.332552      | 1             |
| 3sat_135.cnf | timeout           | both_timeout       | 0.152851   | 0.515365  | 0.443412      | 0.319091      | 1             |
| 3sat_29.cnf  | timeout           | both_timeout       | 0.143023   | 0.738512  | 0.454239      | 0.287068      | 1             |
| 3sat_80.cnf  | timeout           | both_timeout       | 0.172686   | 0.206426  | 0.426445      | 0.282890      | 1             |
| 3sat_154.cnf | easy(<10s)        | faster_both_solved | -0.103374  | 0.697116  | 0.448260      | 0.263017      | 1             |
| 3sat_74.cnf  | timeout           | both_timeout       | 0.213209   | 0.715756  | 0.413233      | 0.259179      | 1             |
| 3sat_75.cnf  | timeout           | both_timeout       | 0.185968   | 0.385808  | 0.500226      | 0.251416      | 1             |
| 3sat_1.cnf   | easy(<10s)        | slower_both_solved | 0.122872   | 0.766840  | 0.566112      | 0.232955      | 1             |

## 24 个未开 Adapter 的 Slowdown

这些样本不经过 adapter，因此当前 filter 不会改变它们。要进一步压低这部分 slowdown，
需要另做 pre-warmup skip gate，让明显 easy/medium 的样本直接走 one-shot，不进入 event rollout。

| file_key     | difficulty_bucket | delta_time | risk_prob | recovery_prob |
| ------------ | ----------------- | ---------- | --------- | ------------- |
| 3sat_157.cnf | easy(<10s)        | 24.739551  | 0.524109  | 0.006732      |
| 3sat_54.cnf  | medium(10-30s)    | 0.867918   | 0.794743  | 0.198134      |
| 3sat_180.cnf | medium(10-30s)    | 0.700925   | 0.219593  | 0.001321      |
| 3sat_92.cnf  | easy(<10s)        | 0.333400   | 0.475594  | 0.044187      |
| 3sat_19.cnf  | easy(<10s)        | 0.300014   | 0.516183  | 0.180853      |
| 3sat_25.cnf  | easy(<10s)        | 0.290045   | 0.525899  | 0.216358      |
| 3sat_24.cnf  | easy(<10s)        | 0.282287   | 0.513053  | 0.311279      |
| 3sat_190.cnf | easy(<10s)        | 0.256243   | 0.991364  | 0.000000      |
| 3sat_63.cnf  | easy(<10s)        | 0.233884   | 0.741606  | 0.039818      |
| 3sat_138.cnf | hard(>=30s)       | 0.226143   | 0.260328  | 0.228588      |
| 3sat_131.cnf | easy(<10s)        | 0.204388   | 0.621691  | 0.005296      |
| 3sat_141.cnf | easy(<10s)        | 0.201586   | 0.919760  | 0.035176      |
| 3sat_70.cnf  | easy(<10s)        | 0.176373   | 0.822223  | 0.253237      |
| 3sat_176.cnf | easy(<10s)        | 0.165855   | 0.825210  | 0.032187      |
| 3sat_149.cnf | easy(<10s)        | 0.153025   | 0.600409  | 0.100868      |
| 3sat_142.cnf | easy(<10s)        | 0.152972   | 0.671401  | 0.005514      |
| 3sat_14.cnf  | easy(<10s)        | 0.147534   | 0.741101  | 0.016019      |
| 3sat_65.cnf  | easy(<10s)        | 0.144479   | 0.012507  | 0.000000      |
| 3sat_181.cnf | easy(<10s)        | 0.144220   | 0.550956  | 0.049063      |
| 3sat_129.cnf | easy(<10s)        | 0.143319   | 0.606396  | 0.038012      |
| 3sat_121.cnf | easy(<10s)        | 0.136385   | 0.768378  | 0.208860      |
| 3sat_124.cnf | easy(<10s)        | 0.135502   | 0.912855  | 0.000000      |
| 3sat_150.cnf | easy(<10s)        | 0.131294   | 0.822424  | 0.043990      |
| 3sat_130.cnf | easy(<10s)        | 0.123778   | 0.915890  | 0.034894      |

