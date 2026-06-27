# Guarded Local Reopen Full400 评估

## 实验定位

这不是新的全局主模型，而是 `local boundary correction ablation` 的 full400 接入验证。
candidate guard 只允许 `data/new_closed_old_on_boundary/manifest.csv` 中的局部边界样本触发 reopen；非候选样本不会因为局部规则被额外打开。

局部规则为：

- `local_reopen_candidate >= 1`
- `warmup_c1000_minus_warmup_c750_decisions >= 294`
- `warmup_c2000_rho_event_corr >= 0.0365`

## 方法汇总

| method | n | solved | mean_time | median_time | total_time | mean_cpu_time | mean_gpu_time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| one_shot | 200 | 50 | 47.7517 | 60.7660 | 9550.3325 | 46.9441 | 0.8076 |
| old_compact | 200 | 56 | 46.3484 | 60.8806 | 9269.6778 | 45.4296 | 0.8468 |
| online_consistent | 200 | 56 | 46.2217 | 60.8820 | 9244.3337 | 45.3366 | 0.8126 |
| local_reopen_guarded | 200 | 56 | 45.4976 | 60.3461 | 9099.5283 | 45.1173 | 0.2899 |
| pairwise_veto | 200 | 52 | 46.8755 | 60.9593 | 9375.1046 | 45.9563 | 0.8467 |

关键数字：

- guarded local reopen：`56/200`，mean time `45.4976s`。
- online-consistent conservative：`56/200`，mean time `46.2217s`。
- 旧 compact 主线：`56/200`，mean time `46.3484s`。
- 相比 online-consistent conservative：解出数 `+0`，平均时间 `-0.7240s`。
- 相比旧 compact：解出数 `+0`，平均时间 `-0.8507s`。

## Local Reopen 实际触发集合

| file_key | use_adapter | local_reopen_rule_open | use_adapter_with_local_reopen | online_result | local_result | online_time | local_time | delta_time_vs_online | outcome_vs_online | warmup_c1000_minus_warmup_c750_decisions | warmup_c2000_rho_event_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | False | True | True | SATISFIABLE | SATISFIABLE | 25.6299 | 25.7315 | 0.1015 | slower_both_solved | 294.0000 | 0.2096 |
| 3sat_196.cnf | False | True | True | SATISFIABLE | SATISFIABLE | 26.1159 | 9.6220 | -16.4939 | faster_both_solved | 320.0000 | 0.0365 |
| 3sat_46.cnf | False | True | True | SATISFIABLE | SATISFIABLE | 29.8371 | 0.5256 | -29.3115 | faster_both_solved | 310.0000 | 0.0859 |
| 3sat_66.cnf | False | True | True | INDETERMINATE | INDETERMINATE | 60.8271 | 60.4345 | -0.3925 | both_timeout | 298.0000 | 0.2113 |

## 相对 Conservative 的 Outcome

| outcome_vs_online | count |
| --- | --- |
| both_timeout | 144 |
| faster_both_solved | 42 |
| slower_both_solved | 7 |
| tie_both_solved | 7 |

## 难度桶

| bucket | n | one_shot_solved | online_solved | local_solved | delta_solved_vs_online | delta_mean_time_vs_online | faster_both_solved | slower_both_solved | tie_both_solved | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy(<10s) | 37 | 37 | 37 | 37 | 0 | -0.4943 | 28 | 3 | 6 | 0 | 0 | 0 |
| medium(10-30s) | 9 | 9 | 9 | 9 | 0 | -2.3297 | 7 | 2 | 0 | 0 | 0 | 0 |
| hard(>=30s) | 4 | 4 | 4 | 4 | 0 | -7.0313 | 2 | 1 | 1 | 0 | 0 | 0 |
| timeout | 150 | 0 | 6 | 6 | 0 | -0.5162 | 5 | 1 | 0 | 0 | 0 | 144 |

## 重点样本

| file_key | difficulty_bucket | online_result | local_result | online_time | local_time | delta_time_vs_online | outcome_vs_online | old_time | one_shot_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_188.cnf | timeout | SATISFIABLE | SATISFIABLE | 25.6299 | 25.7315 | 0.1015 | slower_both_solved | 26.3512 | 60.8011 |
| 3sat_196.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 26.1159 | 9.6220 | -16.4939 | faster_both_solved | 10.3172 | 25.1129 |
| 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 29.8371 | 0.5256 | -29.3115 | faster_both_solved | 1.0575 | 30.7425 |
| 3sat_66.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8271 | 60.4345 | -0.3925 | both_timeout | 61.0117 | 60.8412 |
| 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.7471 | 20.5844 | -1.1627 | faster_both_solved | 36.0880 | 21.4710 |
| 3sat_93.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.7508 | 18.8856 | 0.1348 | slower_both_solved | 21.5550 | 18.8329 |

## 最大单实例变化

| change_type | file_key | difficulty_bucket | online_result | local_result | online_time | local_time | delta_time_vs_online | outcome_vs_online | old_time | one_shot_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| largest_win | 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 29.8371 | 0.5256 | -29.3115 | faster_both_solved | 1.0575 | 30.7425 |
| largest_win | 3sat_196.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 26.1159 | 9.6220 | -16.4939 | faster_both_solved | 10.3172 | 25.1129 |
| largest_win | 3sat_122.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 59.2834 | 57.7678 | -1.5156 | faster_both_solved | 59.4942 | 60.0490 |
| largest_win | 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.7471 | 20.5844 | -1.1627 | faster_both_solved | 36.0880 | 21.4710 |
| largest_win | 3sat_128.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 7.8749 | 6.8778 | -0.9971 | faster_both_solved | 7.5215 | 29.1131 |
| largest_win | 3sat_147.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 11.9006 | 10.9857 | -0.9148 | faster_both_solved | 11.7653 | 11.7280 |
| largest_win | 3sat_125.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.7606 | 2.8464 | -0.9141 | faster_both_solved | 3.5243 | 3.1999 |
| largest_win | 3sat_149.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 4.3063 | 3.4165 | -0.8898 | faster_both_solved | 3.9164 | 3.7633 |
| largest_win | 3sat_13.cnf | timeout | INDETERMINATE | INDETERMINATE | 61.2167 | 60.3737 | -0.8430 | both_timeout | 60.9380 | 60.7675 |
| largest_win | 3sat_119.cnf | timeout | INDETERMINATE | INDETERMINATE | 61.2101 | 60.3674 | -0.8427 | both_timeout | 60.9288 | 60.7637 |
| largest_win | 3sat_126.cnf | timeout | INDETERMINATE | INDETERMINATE | 61.1915 | 60.3651 | -0.8264 | both_timeout | 60.9451 | 60.7601 |
| largest_win | 3sat_12.cnf | timeout | INDETERMINATE | INDETERMINATE | 61.1978 | 60.3755 | -0.8223 | both_timeout | 60.9383 | 60.7582 |
| largest_loss | 3sat_138.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 49.2613 | 51.9639 | 2.7026 | slower_both_solved | 52.3750 | 52.1488 |
| largest_loss | 3sat_180.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 13.7128 | 13.9217 | 0.2090 | slower_both_solved | 14.3728 | 13.6719 |
| largest_loss | 3sat_92.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.0248 | 3.1867 | 0.1620 | slower_both_solved | 8.0256 | 7.6922 |
| largest_loss | 3sat_99.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2387 | 60.3904 | 0.1516 | both_timeout | 60.7938 | 60.7613 |
| largest_loss | 3sat_90.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2564 | 60.3956 | 0.1392 | both_timeout | 60.7986 | 60.7724 |
| largest_loss | 3sat_5.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2374 | 60.3750 | 0.1375 | both_timeout | 60.8728 | 60.7839 |
| largest_loss | 3sat_93.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.7508 | 18.8856 | 0.1348 | slower_both_solved | 21.5550 | 18.8329 |
| largest_loss | 3sat_50.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2443 | 60.3711 | 0.1267 | both_timeout | 60.8647 | 60.8001 |
| largest_loss | 3sat_96.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 0.3286 | 0.4496 | 0.1210 | slower_both_solved | 0.8594 | 0.9593 |
| largest_loss | 3sat_53.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2332 | 60.3535 | 0.1203 | both_timeout | 60.8565 | 60.7938 |
| largest_loss | 3sat_45.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2428 | 60.3597 | 0.1170 | both_timeout | 60.8749 | 60.7991 |
| largest_loss | 3sat_98.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.2632 | 60.3775 | 0.1143 | both_timeout | 60.7851 | 60.7655 |

## 当前结论

- candidate guard 生效：full400 中只有 4 个 `new_closed_old_on` 候选触发 local reopen。
- full400 wall-clock 没有增加 solved count，但平均时间优于旧 compact 与 online-consistent conservative。
- 这条线适合作为 `local boundary correction ablation` 写入论文：证明过保守 risk controller 的少量边界错误可以被局部 reopen rule 修正，但不应提升为主模型故事。

## 输出文件

- `runs/analysis/local_reopen_guarded_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_per_instance.csv`
- `runs/analysis/local_reopen_guarded_full400_bucket_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_largest_changes.csv`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`
- `figures/fig_local_reopen_guarded_full400_cactus.pdf`
- `runs/analysis/local_reopen_guarded_full400_guidance_audit.csv`
