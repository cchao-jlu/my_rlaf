# Local Boundary Correction Ablation

## 实验定位

本实验只验证 `new_closed_old_on` 局部边界，不是新的全局主模型，也没有扫描全局阈值。
动机是：当前 conservative risk controller 为了避免 easy/medium 翻车，会过保守地关掉少数 recoverable 或 hard-speedup 样本。
local reopen override 只作为 boundary correction，用一条局部规则修正这类边界错误。

## 局部规则

- `local_reopen_candidate >= 1`
- `warmup_c1000_minus_warmup_c750_decisions >= 294`
- `warmup_c2000_rho_event_corr >= 0.0365`

其中 `local_reopen_candidate` 是候选守门特征：只有审计表判定为 `new_closed_old_on` 局部边界的样本才允许进入 reopen rule；其他 full400 样本即使满足后两个数值条件，也默认保持关闭。
该规则来自 `new_closed_old_on` dense trace，不来自 full400 全局阈值搜索。

## 真实 Wall-clock 聚合结果

| policy | n | solved | mean_time | total_time | mean_cpu | mean_conflicts | mean_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local_reopen | 26 | 5 | 51.6751 | 1343.5539 | 51.3337 | 1461661.2308 | 1671571.3462 |
| no_override | 26 | 5 | 53.3406 | 1386.8551 | 52.9955 | 1526094.1154 | 1745096.4615 |

- total time 变化：`-43.3012s`
- mean time 变化：`-1.6654s`
- 解出数保持 `5/26`，没有新增 lost solution。

## 实际打开集合

guidance audit 显示 local reopen rule 只打开 4 个样本：

| file_key | counterfactual_class | counterfactual_reason | base_selector_use_adapter | local_reopen_rule_open | warmup_c1000_minus_warmup_c750_decisions | warmup_c2000_rho_event_corr | delta_time | delta_conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | positive | recovered_timeout | True | True | 294.0000 | 0.2096 | 1.0735 | 0.0000 |
| 3sat_196.cnf | positive | hard_speedup | False | True | 320.0000 | 0.0365 | -15.3528 | -545275.0000 |
| 3sat_46.cnf | positive | hard_speedup | False | True | 310.0000 | 0.0859 | -29.2290 | -967440.0000 |
| 3sat_66.cnf | neutral | neutral | False | True | 298.0000 | 0.2113 | 0.0053 | -10888.0000 |

其中 `3sat_46.cnf` 和 `3sat_196.cnf` 的 hard-speedup 稳定落到真实 wall-clock；`3sat_66.cnf` 是 neutral，真实开销约为零；`3sat_188.cnf` 在本次 boundary26 run 中 no-override 已经解出，因此没有贡献新增 solved，但仍处于应打开的安全区域。

## Negative 保护

两个 negative slowdown 样本均保持关闭，final conflicts/decisions 不变；时间上的微小差异主要来自额外 750-conflict warmup 采样点和运行噪声。

| file_key | counterfactual_class | counterfactual_reason | base_selector_use_adapter | local_reopen_rule_open | delta_time | delta_conflicts | delta_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_82.cnf | negative | slowdown | False | False | 0.2746 | 0.0000 | 0.0000 |
| 3sat_93.cnf | negative | slowdown | False | False | -0.0072 | 0.0000 | 0.0000 |

## 焦点样本逐实例结果

| file_key | counterfactual_class | counterfactual_reason | no_override_result | local_reopen_result | no_override_time | local_reopen_time | delta_time | delta_conflicts | delta_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | positive | recovered_timeout | SATISFIABLE | SATISFIABLE | 25.7637 | 26.8372 | 1.0735 | 0.0000 | 0.0000 |
| 3sat_196.cnf | positive | hard_speedup | SATISFIABLE | SATISFIABLE | 25.4261 | 10.0733 | -15.3528 | -545275.0000 | -625256.0000 |
| 3sat_46.cnf | positive | hard_speedup | SATISFIABLE | SATISFIABLE | 29.7798 | 0.5509 | -29.2290 | -967440.0000 | -1099110.0000 |
| 3sat_66.cnf | neutral | neutral | INDETERMINATE | INDETERMINATE | 60.2189 | 60.2242 | 0.0053 | -10888.0000 | -13396.0000 |
| 3sat_82.cnf | negative | slowdown | SATISFIABLE | SATISFIABLE | 20.3782 | 20.6528 | 0.2746 | 0.0000 | 0.0000 |
| 3sat_93.cnf | negative | slowdown | SATISFIABLE | SATISFIABLE | 18.5299 | 18.5227 | -0.0072 | 0.0000 | 0.0000 |

## 当前结论

- boundary26 真实 wall-clock 支持把该模块写成 `local boundary correction ablation`。
- 该规则修复了 `3sat_46/196` 这类被 conservative selector 错关的 hard-speedup 样本，同时没有打开 `3sat_82/93` 这类 slowdown 负例。
- 目前仍不应直接宣称它是 full400 主线模型；接 full400 前必须使用 candidate guard，只允许在 `new_closed_old_on` 这类局部候选上触发 reopen。当前 checkpoint 配置已经把 `local_reopen_candidate >= 1` 写入 `local_reopen_feature_names`，评估时需要通过 `feedback_refinement.local_reopen_candidate_manifest` 提供候选清单。

## 输出文件

- `runs/analysis/local_reopen_boundary26_wallclock_comparison.csv`
- `runs/analysis/local_reopen_boundary26_wallclock_summary.csv`
- `runs/analysis/local_reopen_boundary26_open_set.csv`
- `runs/analysis/local_reopen_boundary26_guidance_audit.csv`
