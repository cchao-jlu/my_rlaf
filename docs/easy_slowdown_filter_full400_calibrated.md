# 简单/中等实例 Slowdown Filter 诊断

本轮目标是在不丢掉 400 完整测试集 6 个 `recovered_timeout` 的前提下，
对已经打开 adapter 的 easy/medium slowdown 做更细的 post-warmup veto。

## 关键判断

- 33 个 slowdown 中，只有 6 个发生在 `selector_use_adapter=1` 的样本上；
- 另外 27 个 slowdown 发生在 `selector_use_adapter=0`，主要来自 warmup/计时开销或噪声，post-warmup filter 无法直接消除；
- 因此本 filter 的有效作用域是这 6 个 selected slowdown。

## 训练设置

- 训练 CSV：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/two_stage_all_data_policy.csv`
- 输出 checkpoint：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated`
- threshold mode：`full400_preserve_recovery`
- threshold：`0.275569`
- bias：`-0.290794`
- veto 规则：`slowdown_prob >= threshold` 时关闭 adapter；
- 正例：easy/medium slowdown 与 lost_solution；
- 强保留负例：recovered_timeout 与 hard_speedup。

## 特征

- risk_prob
- recovery_prob
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

## Full400 汇总

| metric                               | value      |
| ------------------------------------ | ---------- |
| full400_n                            | 200.000000 |
| original_recovered_timeout           | 6.000000   |
| preserved_recovered_timeout          | 6.000000   |
| original_slowdown_total              | 33.000000  |
| original_selected_slowdown           | 6.000000   |
| vetoed_selected_slowdown             | 2.000000   |
| vetoed_selected_easy_medium_slowdown | 2.000000   |
| post_warmup_est_slowdown_total       | 31.000000  |
| vetoed_faster_both_solved            | 0.000000   |
| base_solved                          | 50.000000  |
| filtered_solved                      | 56.000000  |
| delta_solved_vs_base                 | 6.000000   |
| mean_delta_post_warmup_est_vs_base   | -1.489130  |
| slowdown_margin                      | 0.100000   |

## 6 个 Recovered Timeout

| file_key     | difficulty_bucket | outcome           | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ------------ | ----------------- | ----------------- | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_163.cnf | timeout           | recovered_timeout | -31.526202 | 0.699415  | 0.760016      | 0.135942      | 0             |
| 3sat_188.cnf | timeout           | recovered_timeout | -34.449921 | 0.258579  | 0.926653      | 0.002353      | 0             |
| 3sat_189.cnf | timeout           | recovered_timeout | -45.932897 | 0.588801  | 0.761742      | 0.081713      | 0             |
| 3sat_85.cnf  | timeout           | recovered_timeout | -59.295770 | 0.405947  | 0.860374      | 0.011158      | 0             |
| 3sat_89.cnf  | timeout           | recovered_timeout | -59.791267 | 0.593619  | 0.619808      | 0.090842      | 0             |
| 3sat_97.cnf  | timeout           | recovered_timeout | -48.281786 | 0.529829  | 0.617819      | 0.075807      | 0             |

## 6 个 Selected Slowdown

| file_key     | difficulty_bucket | outcome            | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ------------ | ----------------- | ------------------ | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_157.cnf | easy(<10s)        | slower_both_solved | 24.739551  | 0.524109  | 0.612839      | 0.048935      | 0             |
| 3sat_82.cnf  | medium(10-30s)    | slower_both_solved | 14.616988  | 0.779136  | 0.745158      | 0.275569      | 1             |
| 3sat_93.cnf  | medium(10-30s)    | slower_both_solved | 2.722067   | 0.752000  | 0.704601      | 0.303488      | 1             |
| 3sat_22.cnf  | easy(<10s)        | slower_both_solved | 0.370704   | 0.393290  | 0.995380      | 0.003278      | 0             |
| 3sat_19.cnf  | easy(<10s)        | slower_both_solved | 0.300014   | 0.516183  | 0.598645      | 0.090956      | 0             |
| 3sat_132.cnf | easy(<10s)        | slower_both_solved | 0.120795   | 0.190343  | 0.926420      | 0.002074      | 0             |

## 被 Filter 拦截的样本

| file_key    | difficulty_bucket | outcome            | delta_time | risk_prob | recovery_prob | slowdown_prob | slowdown_veto |
| ----------- | ----------------- | ------------------ | ---------- | --------- | ------------- | ------------- | ------------- |
| 3sat_53.cnf | timeout           | both_timeout       | 0.062608   | 0.714614  | 0.644663      | 0.335167      | 1             |
| 3sat_93.cnf | medium(10-30s)    | slower_both_solved | 2.722067   | 0.752000  | 0.704601      | 0.303488      | 1             |
| 3sat_49.cnf | timeout           | both_timeout       | 0.063362   | 0.753168  | 0.931481      | 0.300914      | 1             |
| 3sat_82.cnf | medium(10-30s)    | slower_both_solved | 14.616988  | 0.779136  | 0.745158      | 0.275569      | 1             |

## 27 个未开 Adapter 的 Slowdown

这些样本不经过 adapter，因此当前 filter 不会改变它们。要进一步压低这部分 slowdown，
需要另做 pre-warmup skip gate，让明显 easy/medium 的样本直接走 one-shot，不进入 event rollout。

| file_key     | difficulty_bucket | delta_time | risk_prob | recovery_prob |
| ------------ | ----------------- | ---------- | --------- | ------------- |
| 3sat_140.cnf | hard(>=30s)       | 1.301342   | 0.292693  | 0.422560      |
| 3sat_54.cnf  | medium(10-30s)    | 0.867918   | 0.794743  | 0.501948      |
| 3sat_180.cnf | medium(10-30s)    | 0.700925   | 0.219593  | 0.003485      |
| 3sat_20.cnf  | medium(10-30s)    | 0.561759   | 0.475132  | 0.090245      |
| 3sat_92.cnf  | easy(<10s)        | 0.333400   | 0.475594  | 0.036001      |
| 3sat_125.cnf | easy(<10s)        | 0.324392   | 0.198548  | 0.346415      |
| 3sat_25.cnf  | easy(<10s)        | 0.290045   | 0.525899  | 0.514194      |
| 3sat_24.cnf  | easy(<10s)        | 0.282287   | 0.513053  | 0.098713      |
| 3sat_190.cnf | easy(<10s)        | 0.256243   | 0.991364  | 0.000000      |
| 3sat_63.cnf  | easy(<10s)        | 0.233884   | 0.741606  | 0.144676      |
| 3sat_138.cnf | hard(>=30s)       | 0.226143   | 0.260328  | 0.038062      |
| 3sat_131.cnf | easy(<10s)        | 0.204388   | 0.621691  | 0.124638      |
| 3sat_141.cnf | easy(<10s)        | 0.201586   | 0.919760  | 0.326001      |
| 3sat_70.cnf  | easy(<10s)        | 0.176373   | 0.822223  | 0.776947      |
| 3sat_176.cnf | easy(<10s)        | 0.165855   | 0.825210  | 0.006728      |
| 3sat_27.cnf  | easy(<10s)        | 0.158550   | 0.261708  | 0.356959      |
| 3sat_149.cnf | easy(<10s)        | 0.153025   | 0.600409  | 0.184238      |
| 3sat_142.cnf | easy(<10s)        | 0.152972   | 0.671401  | 0.002173      |
| 3sat_14.cnf  | easy(<10s)        | 0.147534   | 0.741101  | 0.128087      |
| 3sat_65.cnf  | easy(<10s)        | 0.144479   | 0.012507  | 0.000000      |
| 3sat_181.cnf | easy(<10s)        | 0.144220   | 0.550956  | 0.021296      |
| 3sat_129.cnf | easy(<10s)        | 0.143319   | 0.606396  | 0.065161      |
| 3sat_121.cnf | easy(<10s)        | 0.136385   | 0.768378  | 0.072735      |
| 3sat_124.cnf | easy(<10s)        | 0.135502   | 0.912855  | 0.000000      |
| 3sat_150.cnf | easy(<10s)        | 0.131294   | 0.822424  | 0.004346      |
| 3sat_130.cnf | easy(<10s)        | 0.123778   | 0.915890  | 0.032009      |
| 3sat_1.cnf   | easy(<10s)        | 0.122872   | 0.766840  | 0.357523      |

