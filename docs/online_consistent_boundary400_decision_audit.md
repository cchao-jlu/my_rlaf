# Online-consistent Boundary400 Selector 决策审计

本审计只使用 `online_consistent_boundary400_full400_selector_features.csv` 作为当前 selector 的在线一致特征证据。
旧 compact 的原始开关只作为“该实例是否已有真实 adapter 分支观测”的参照，不用于新 checkpoint 的决策。

## 主要结论

- 新 online-consistent boundary400 checkpoint 与旧 compact 同为 `56/200`，均时从 `46.3484s` 小幅降到 `46.2217s`。
- 大退化 `3sat_46.cnf`、`3sat_196.cnf` 不是新 selector 误开 adapter，而是新 selector 关闭了旧 compact 曾开启且在该次运行中很有效的 adapter 分支。
- 大改善 `3sat_140.cnf` 是新 selector 新开 adapter 后获得的 hard speedup；`3sat_82.cnf` 是关闭旧 compact adapter 后回到更快回退路径。
- 因此下一步应做“基于当前 online cache 的阈值/边界审计”，优先验证是否能重新打开少数有旧 adapter 真实观测的正例，同时不打开没有观测支撑的风险样本。

## 决策变化汇总

| decision_change | n | old_solved | new_solved | delta_solved | delta_mean_time_vs_old | faster_both_solved | slower_both_solved | tie_both_solved | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| both_off | 143 | 33 | 33 | 0 | -0.0441 | 15 | 14 | 4 | 0 | 0 | 110 |
| both_on | 18 | 12 | 12 | 0 | -0.1514 | 6 | 4 | 2 | 0 | 0 | 6 |
| new_closed_old_on | 26 | 5 | 5 | 0 | 1.0326 | 3 | 2 | 0 | 0 | 0 | 21 |
| new_opened_old_off | 13 | 6 | 6 | 0 | -3.3197 | 4 | 2 | 0 | 0 | 0 | 7 |

## 重点样本

| file_key | difficulty_bucket | base_time | old_time | new_time | delta_time_vs_old | outcome_vs_old | old_original_use_adapter | old_on_new_cache_use_adapter | new_use_adapter_actual | new_risk_prob | new_recovery_prob | new_slowdown_prob | decision_change | old_weight_cache_shift | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | hard(>=30s) | 60.0490 | 59.4942 | 59.2834 | -0.2108 | faster_both_solved | 0 | 0 | 0 | 0.8636 | 0.4429 | 0.0864 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_140.cnf | hard(>=30s) | 39.7812 | 41.0826 | 4.3394 | -36.7432 | faster_both_solved | 0 | 0 | 1 | 0.2339 | 0.9526 | 0.0100 | new_opened_old_off | both_off | 新 selector 打开 adapter 后加速 |
| 3sat_163.cnf | timeout | 60.8197 | 29.2935 | 29.0814 | -0.2121 | faster_both_solved | 1 | 1 | 1 | 0.7316 | 0.9320 | 0.0219 | both_on | both_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |
| 3sat_188.cnf | timeout | 60.8011 | 26.3512 | 25.6299 | -0.7213 | faster_both_solved | 1 | 1 | 0 | 0.2635 | 0.7545 | 0.0189 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速 |
| 3sat_196.cnf | medium(10-30s) | 25.1129 | 10.3172 | 26.1159 | 15.7987 | slower_both_solved | 1 | 1 | 0 | 0.5842 | 0.2482 | 0.4350 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径慢化 |
| 3sat_25.cnf | easy(<10s) | 1.6911 | 1.9812 | 1.8238 | -0.1574 | faster_both_solved | 0 | 0 | 0 | 0.7068 | 0.4180 | 0.1847 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_46.cnf | hard(>=30s) | 30.7425 | 1.0575 | 29.8371 | 28.7796 | slower_both_solved | 1 | 1 | 0 | 0.5161 | 0.3486 | 0.4061 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径慢化 |
| 3sat_82.cnf | medium(10-30s) | 21.4710 | 36.0880 | 21.7471 | -14.3409 | faster_both_solved | 1 | 1 | 0 | 0.8629 | 0.0777 | 0.6466 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速 |
| 3sat_88.cnf | easy(<10s) | 0.9823 | 1.0170 | 1.0972 | 0.0802 | tie_both_solved | 0 | 0 | 0 | 0.6278 | 0.6848 | 0.1365 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_89.cnf | timeout | 60.7633 | 0.9720 | 1.0573 | 0.0853 | tie_both_solved | 1 | 1 | 1 | 0.6400 | 0.7912 | 0.0198 | both_on | both_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |
| 3sat_97.cnf | timeout | 60.7605 | 12.4787 | 11.7636 | -0.7151 | faster_both_solved | 1 | 1 | 1 | 0.5101 | 0.9400 | 0.0226 | both_on | both_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |

## 最大退化

| file_key | difficulty_bucket | base_time | old_time | new_time | delta_time_vs_old | outcome_vs_old | old_original_use_adapter | old_on_new_cache_use_adapter | new_use_adapter_actual | new_risk_prob | new_recovery_prob | new_slowdown_prob | decision_change | old_weight_cache_shift | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_46.cnf | hard(>=30s) | 30.7425 | 1.0575 | 29.8371 | 28.7796 | slower_both_solved | 1 | 1 | 0 | 0.5161 | 0.3486 | 0.4061 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径慢化 |
| 3sat_196.cnf | medium(10-30s) | 25.1129 | 10.3172 | 26.1159 | 15.7987 | slower_both_solved | 1 | 1 | 0 | 0.5842 | 0.2482 | 0.4350 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径慢化 |
| 3sat_157.cnf | easy(<10s) | 3.2106 | 27.9502 | 28.6097 | 0.6596 | slower_both_solved | 1 | 1 | 1 | 0.5350 | 0.8785 | 0.0062 | both_on | both_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |
| 3sat_86.cnf | easy(<10s) | 3.3912 | 3.4575 | 3.9738 | 0.5163 | slower_both_solved | 0 | 0 | 1 | 0.6838 | 0.8527 | 0.1136 | new_opened_old_off | both_off | 新 selector 打开 adapter 后慢化 |
| 3sat_164.cnf | timeout | 60.8240 | 60.7134 | 61.1343 | 0.4209 | both_timeout | 1 | 1 | 0 | 0.6691 | 0.5037 | 0.1813 | new_closed_old_on | both_on | 边界变化但 outcome 不显著 |
| 3sat_161.cnf | timeout | 60.8376 | 60.7267 | 61.1382 | 0.4115 | both_timeout | 0 | 0 | 0 | 0.9237 | 0.8685 | 0.0534 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_17.cnf | timeout | 60.8354 | 60.7295 | 61.1370 | 0.4075 | both_timeout | 1 | 1 | 0 | 0.1021 | 0.0850 | 0.5701 | new_closed_old_on | both_on | 边界变化但 outcome 不显著 |
| 3sat_168.cnf | timeout | 60.8354 | 60.7115 | 61.1141 | 0.4026 | both_timeout | 0 | 0 | 0 | 0.8096 | 0.1921 | 0.4475 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_160.cnf | timeout | 60.8115 | 60.7230 | 61.1248 | 0.4018 | both_timeout | 0 | 0 | 0 | 0.8050 | 0.0356 | 0.5843 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_162.cnf | timeout | 60.8230 | 60.7360 | 61.1330 | 0.3969 | both_timeout | 0 | 0 | 0 | 0.0647 | 0.6794 | 0.1550 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_152.cnf | timeout | 60.8258 | 60.7253 | 61.1206 | 0.3952 | both_timeout | 0 | 0 | 0 | 0.8757 | 0.2067 | 0.7443 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_153.cnf | timeout | 60.8367 | 60.7249 | 61.1191 | 0.3942 | both_timeout | 1 | 1 | 0 | 0.2153 | 0.6856 | 0.0451 | new_closed_old_on | both_on | 边界变化但 outcome 不显著 |
| 3sat_167.cnf | medium(10-30s) | 11.1136 | 11.1047 | 11.4969 | 0.3922 | slower_both_solved | 0 | 0 | 0 | 0.8495 | 0.3515 | 0.5003 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_149.cnf | easy(<10s) | 3.7633 | 3.9164 | 4.3063 | 0.3899 | slower_both_solved | 0 | 0 | 0 | 0.5568 | 0.0423 | 0.7950 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_166.cnf | timeout | 60.8417 | 60.7270 | 61.1145 | 0.3875 | both_timeout | 0 | 0 | 0 | 0.4014 | 0.0021 | 0.8623 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |

## 最大改善

| file_key | difficulty_bucket | base_time | old_time | new_time | delta_time_vs_old | outcome_vs_old | old_original_use_adapter | old_on_new_cache_use_adapter | new_use_adapter_actual | new_risk_prob | new_recovery_prob | new_slowdown_prob | decision_change | old_weight_cache_shift | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_140.cnf | hard(>=30s) | 39.7812 | 41.0826 | 4.3394 | -36.7432 | faster_both_solved | 0 | 0 | 1 | 0.2339 | 0.9526 | 0.0100 | new_opened_old_off | both_off | 新 selector 打开 adapter 后加速 |
| 3sat_82.cnf | medium(10-30s) | 21.4710 | 36.0880 | 21.7471 | -14.3409 | faster_both_solved | 1 | 1 | 0 | 0.8629 | 0.0777 | 0.6466 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速 |
| 3sat_92.cnf | easy(<10s) | 7.6922 | 8.0256 | 3.0248 | -5.0008 | faster_both_solved | 0 | 0 | 1 | 0.4618 | 0.9732 | 0.1223 | new_opened_old_off | both_off | 新 selector 打开 adapter 后加速 |
| 3sat_138.cnf | hard(>=30s) | 52.1488 | 52.3750 | 49.2613 | -3.1137 | faster_both_solved | 0 | 0 | 0 | 0.2268 | 0.5814 | 0.0243 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_93.cnf | medium(10-30s) | 18.8329 | 21.5550 | 18.7508 | -2.8042 | faster_both_solved | 1 | 1 | 0 | 0.8189 | 0.7686 | 0.1087 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速 |
| 3sat_19.cnf | easy(<10s) | 3.6099 | 3.9099 | 1.8683 | -2.0416 | faster_both_solved | 1 | 0 | 1 | 0.4562 | 0.9702 | 0.0059 | both_on | new_closed_old_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |
| 3sat_188.cnf | timeout | 60.8011 | 26.3512 | 25.6299 | -0.7213 | faster_both_solved | 1 | 1 | 0 | 0.2635 | 0.7545 | 0.0189 | new_closed_old_on | both_on | 新 selector 关闭旧 compact 曾开启的 adapter，退回路径反而加速 |
| 3sat_97.cnf | timeout | 60.7605 | 12.4787 | 11.7636 | -0.7151 | faster_both_solved | 1 | 1 | 1 | 0.5101 | 0.9400 | 0.0226 | both_on | both_on | 两者都开启 adapter，差异来自新 checkpoint/运行路径 |
| 3sat_91.cnf | easy(<10s) | 0.9640 | 1.0114 | 0.2983 | -0.7131 | faster_both_solved | 0 | 0 | 1 | 0.5135 | 0.8814 | 0.0286 | new_opened_old_off | both_off | 新 selector 打开 adapter 后加速 |
| 3sat_180.cnf | medium(10-30s) | 13.6719 | 14.3728 | 13.7128 | -0.6601 | faster_both_solved | 0 | 0 | 0 | 0.1873 | 0.3859 | 0.2072 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_47.cnf | easy(<10s) | 2.8333 | 2.9202 | 2.2724 | -0.6479 | faster_both_solved | 0 | 0 | 0 | 0.9009 | 0.7746 | 0.0470 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_5.cnf | timeout | 60.7839 | 60.8728 | 60.2374 | -0.6354 | both_timeout | 0 | 0 | 0 | 0.2298 | 0.0009 | 0.8450 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_52.cnf | timeout | 60.7814 | 60.8861 | 60.2511 | -0.6350 | both_timeout | 0 | 0 | 0 | 0.6688 | 0.3882 | 0.2545 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_45.cnf | timeout | 60.7991 | 60.8749 | 60.2428 | -0.6321 | both_timeout | 0 | 0 | 0 | 0.1729 | 0.0266 | 0.3778 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |
| 3sat_141.cnf | easy(<10s) | 3.0762 | 3.2778 | 2.6479 | -0.6300 | faster_both_solved | 0 | 0 | 0 | 0.9593 | 0.7967 | 0.0141 | both_off | both_off | 两者都关闭 adapter，差异主要来自回退求解路径或运行噪声 |

## 输出文件

- `runs/analysis/online_consistent_boundary400_decision_audit.csv`
- `runs/analysis/online_consistent_boundary400_decision_audit_focus.csv`
- `runs/analysis/online_consistent_boundary400_decision_audit_summary.csv`
