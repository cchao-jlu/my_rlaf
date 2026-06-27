# Online-Consistent Boundary400 Full400 评估

本报告合并 4 个 50 实例 batch 的真实 wall-clock 结果。
该 checkpoint 使用 full400 boundary 子集生成的 online-consistent trace 重训 two-stage selector。

## 方法汇总

| method | n | solved | mean_time | median_time | mean_cpu_time | mean_gpu_time |
| --- | --- | --- | --- | --- | --- | --- |
| oneshot | 200 | 50 | 47.7517 | 60.7660 | 46.9441 | 0.8076 |
| old_compact | 200 | 56 | 46.3484 | 60.8806 | 45.4296 | 0.8468 |
| pairwise_veto_actual | 200 | 52 | 46.8755 | 60.9593 | 45.9563 | 0.8467 |
| online_consistent_boundary400 | 200 | 56 | 46.2217 | 60.8820 | 45.3366 | 0.8126 |

## 相对旧 compact 主线的 outcome

| outcome_vs_old | count |
| --- | --- |
| both_timeout | 144 |
| faster_both_solved | 28 |
| slower_both_solved | 22 |
| tie_both_solved | 6 |

## 难度桶

| bucket | n | base_solved | old_solved | new_solved | delta_solved_vs_old | delta_mean_time_vs_old | faster_both_solved | slower_both_solved | tie_both_solved | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy(<10s) | 37 | 37 | 37 | 37 | 0 | -0.2185 | 16 | 17 | 4 | 0 | 0 | 0 |
| medium(10-30s) | 9 | 9 | 9 | 9 | 0 | -0.2142 | 5 | 4 | 0 | 0 | 0 | 0 |
| hard(>=30s) | 4 | 4 | 4 | 4 | 0 | -2.8220 | 3 | 1 | 0 | 0 | 0 | 0 |
| timeout | 150 | 0 | 6 | 6 | 0 | -0.0270 | 4 | 0 | 2 | 0 | 0 | 144 |

## 重点样本

| file_key | difficulty_bucket | old_result | new_result | old_time | new_time | delta_time_vs_old | outcome_vs_old |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 59.4942 | 59.2834 | -0.2108 | faster_both_solved |
| 3sat_163.cnf | timeout | SATISFIABLE | SATISFIABLE | 29.2935 | 29.0814 | -0.2121 | faster_both_solved |
| 3sat_188.cnf | timeout | SATISFIABLE | SATISFIABLE | 26.3512 | 25.6299 | -0.7213 | faster_both_solved |
| 3sat_189.cnf | timeout | SATISFIABLE | SATISFIABLE | 14.8203 | 14.6985 | -0.1217 | faster_both_solved |
| 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 36.0880 | 21.7471 | -14.3409 | faster_both_solved |
| 3sat_89.cnf | timeout | SATISFIABLE | SATISFIABLE | 0.9720 | 1.0573 | 0.0853 | tie_both_solved |

## 最大变化

| change_type | file_key | difficulty_bucket | old_result | new_result | old_time | new_time | delta_time_vs_old | outcome_vs_old | base_time | pairwise_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| largest_win | 3sat_140.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 41.0826 | 4.3394 | -36.7432 | faster_both_solved | 39.7812 | 4.4696 |
| largest_win | 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 36.0880 | 21.7471 | -14.3409 | faster_both_solved | 21.4710 | 35.1803 |
| largest_win | 3sat_92.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 8.0256 | 3.0248 | -5.0008 | faster_both_solved | 7.6922 | 7.4563 |
| largest_win | 3sat_138.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 52.3750 | 49.2613 | -3.1137 | faster_both_solved | 52.1488 | 51.0884 |
| largest_win | 3sat_93.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.5550 | 18.7508 | -2.8042 | faster_both_solved | 18.8329 | 20.8691 |
| largest_win | 3sat_19.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.9099 | 1.8683 | -2.0416 | faster_both_solved | 3.6099 | 3.8916 |
| largest_win | 3sat_188.cnf | timeout | SATISFIABLE | SATISFIABLE | 26.3512 | 25.6299 | -0.7213 | faster_both_solved | 60.8011 | 60.3573 |
| largest_win | 3sat_97.cnf | timeout | SATISFIABLE | SATISFIABLE | 12.4787 | 11.7636 | -0.7151 | faster_both_solved | 60.7605 | 11.7357 |
| largest_win | 3sat_91.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 1.0114 | 0.2983 | -0.7131 | faster_both_solved | 0.9640 | 0.4207 |
| largest_win | 3sat_180.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 14.3728 | 13.7128 | -0.6601 | faster_both_solved | 13.6719 | 13.8996 |
| largest_win | 3sat_47.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 2.9202 | 2.2724 | -0.6479 | faster_both_solved | 2.8333 | 2.3557 |
| largest_win | 3sat_5.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8728 | 60.2374 | -0.6354 | both_timeout | 60.7839 | 60.3297 |
| largest_win | 3sat_52.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8861 | 60.2511 | -0.6350 | both_timeout | 60.7814 | 60.3358 |
| largest_win | 3sat_45.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8749 | 60.2428 | -0.6321 | both_timeout | 60.7991 | 60.3499 |
| largest_win | 3sat_141.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.2778 | 2.6479 | -0.6300 | faster_both_solved | 3.0762 | 2.8457 |
| largest_loss | 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 1.0575 | 29.8371 | 28.7796 | slower_both_solved | 30.7425 | 30.6311 |
| largest_loss | 3sat_196.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 10.3172 | 26.1159 | 15.7987 | slower_both_solved | 25.1129 | 10.3727 |
| largest_loss | 3sat_157.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 27.9502 | 28.6097 | 0.6596 | slower_both_solved | 3.2106 | 3.6164 |
| largest_loss | 3sat_86.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.4575 | 3.9738 | 0.5163 | slower_both_solved | 3.3912 | 3.5560 |
| largest_loss | 3sat_164.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7134 | 61.1343 | 0.4209 | both_timeout | 60.8240 | 61.0880 |
| largest_loss | 3sat_161.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7267 | 61.1382 | 0.4115 | both_timeout | 60.8376 | 61.0464 |
| largest_loss | 3sat_17.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7295 | 61.1370 | 0.4075 | both_timeout | 60.8354 | 61.0688 |
| largest_loss | 3sat_168.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7115 | 61.1141 | 0.4026 | both_timeout | 60.8354 | 61.0757 |
| largest_loss | 3sat_160.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7230 | 61.1248 | 0.4018 | both_timeout | 60.8115 | 61.0695 |
| largest_loss | 3sat_162.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7360 | 61.1330 | 0.3969 | both_timeout | 60.8230 | 61.0807 |
| largest_loss | 3sat_152.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7253 | 61.1206 | 0.3952 | both_timeout | 60.8258 | 61.0924 |
| largest_loss | 3sat_153.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7249 | 61.1191 | 0.3942 | both_timeout | 60.8367 | 61.1068 |
| largest_loss | 3sat_167.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 11.1047 | 11.4969 | 0.3922 | slower_both_solved | 11.1136 | 11.9395 |
| largest_loss | 3sat_149.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.9164 | 4.3063 | 0.3899 | slower_both_solved | 3.7633 | 4.2171 |
| largest_loss | 3sat_166.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.7270 | 61.1145 | 0.3875 | both_timeout | 60.8417 | 61.0726 |

## 输出文件

- `runs/analysis/online_consistent_boundary400_full400_actual_batched.csv`
- `runs/analysis/online_consistent_boundary400_full400_summary.csv`
- `runs/analysis/online_consistent_boundary400_full400_per_instance.csv`
- `runs/analysis/online_consistent_boundary400_full400_bucket_summary.csv`
- `runs/analysis/online_consistent_boundary400_full400_largest_changes.csv`
- `figures/fig_online_consistent_boundary400_full400_cactus.pdf`
