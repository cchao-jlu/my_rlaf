# New-Closed-Old-On 局部边界子集

该子集只包含正式 full400 审计中的 `new_closed_old_on` 样本：旧 compact 曾开启 adapter，而当前 online-consistent boundary400 selector 关闭 adapter。
目标是生成局部 counterfactual trace，区分 `3sat_46/196` 这类旧 adapter 有效样本和 `3sat_82/188` 这类保持关闭更好的样本。

- 输出 CNF 目录：`data/new_closed_old_on_boundary/3sat/400`
- manifest：`data/new_closed_old_on_boundary/manifest.csv`
- 子集大小：`26`

## 局部标签计数

| reason | count |
| --- | --- |
| neutral | 21 |
| keep_closed | 3 |
| reopen_old_adapter | 2 |

## 样本清单

| file_key | difficulty_bucket | base_time | old_time | new_time | delta_time_vs_old | outcome_vs_old | new_risk_prob | new_recovery_prob | new_slowdown_prob | local_closed_old_label | local_closed_old_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_106.cnf | timeout | 60.8365 | 60.8881 | 61.1851 | 0.2970 | both_timeout | 0.4183 | 0.3227 | 0.1306 | <NA> | neutral |
| 3sat_115.cnf | timeout | 60.8221 | 60.8982 | 61.1573 | 0.2591 | both_timeout | 0.2831 | 0.5351 | 0.0403 | <NA> | neutral |
| 3sat_117.cnf | timeout | 60.7623 | 60.9250 | 61.1983 | 0.2732 | both_timeout | 0.3104 | 0.4557 | 0.0852 | <NA> | neutral |
| 3sat_144.cnf | timeout | 60.7744 | 60.8973 | 61.1008 | 0.2034 | both_timeout | 0.1639 | 0.1149 | 0.7646 | <NA> | neutral |
| 3sat_145.cnf | timeout | 60.7660 | 60.9015 | 61.1035 | 0.2020 | both_timeout | 0.0553 | 0.4535 | 0.0309 | <NA> | neutral |
| 3sat_151.cnf | timeout | 60.7656 | 60.8878 | 61.1084 | 0.2206 | both_timeout | 0.5095 | 0.4808 | 0.0832 | <NA> | neutral |
| 3sat_153.cnf | timeout | 60.8367 | 60.7249 | 61.1191 | 0.3942 | both_timeout | 0.2153 | 0.6856 | 0.0451 | <NA> | neutral |
| 3sat_164.cnf | timeout | 60.8240 | 60.7134 | 61.1343 | 0.4209 | both_timeout | 0.6691 | 0.5037 | 0.1813 | <NA> | neutral |
| 3sat_17.cnf | timeout | 60.8354 | 60.7295 | 61.1370 | 0.4075 | both_timeout | 0.1021 | 0.0850 | 0.5701 | <NA> | neutral |
| 3sat_172.cnf | timeout | 60.8187 | 60.9678 | 61.1129 | 0.1451 | both_timeout | 0.5476 | 0.4565 | 0.2761 | <NA> | neutral |
| 3sat_173.cnf | timeout | 60.8128 | 60.9520 | 61.1029 | 0.1510 | both_timeout | 0.2059 | 0.6377 | 0.0421 | <NA> | neutral |
| 3sat_183.cnf | timeout | 60.8226 | 60.9469 | 60.3602 | -0.5866 | both_timeout | 0.3936 | 0.0020 | 0.8402 | <NA> | neutral |
| 3sat_188.cnf | timeout | 60.8011 | 26.3512 | 25.6299 | -0.7213 | faster_both_solved | 0.2635 | 0.7545 | 0.0189 | 0 | keep_closed |
| 3sat_196.cnf | medium(10-30s) | 25.1129 | 10.3172 | 26.1159 | 15.7987 | slower_both_solved | 0.5842 | 0.2482 | 0.4350 | 1 | reopen_old_adapter |
| 3sat_197.cnf | timeout | 60.7539 | 61.0292 | 60.8870 | -0.1423 | both_timeout | 0.2966 | 0.6761 | 0.0445 | <NA> | neutral |
| 3sat_23.cnf | timeout | 60.7539 | 61.0240 | 60.8932 | -0.1308 | both_timeout | 0.2535 | 0.5442 | 0.1155 | <NA> | neutral |
| 3sat_37.cnf | timeout | 60.7414 | 60.9070 | 60.8828 | -0.0242 | both_timeout | 0.4347 | 0.0400 | 0.7388 | <NA> | neutral |
| 3sat_46.cnf | hard(>=30s) | 30.7425 | 1.0575 | 29.8371 | 28.7796 | slower_both_solved | 0.5161 | 0.3486 | 0.4061 | 1 | reopen_old_adapter |
| 3sat_49.cnf | timeout | 60.7917 | 60.8551 | 60.2536 | -0.6015 | both_timeout | 0.7257 | 0.2669 | 0.5220 | <NA> | neutral |
| 3sat_53.cnf | timeout | 60.7938 | 60.8565 | 60.2332 | -0.6232 | both_timeout | 0.7625 | 0.1948 | 0.4071 | <NA> | neutral |
| 3sat_66.cnf | timeout | 60.8412 | 61.0117 | 60.8271 | -0.1846 | both_timeout | 0.6627 | 0.1224 | 0.8299 | <NA> | neutral |
| 3sat_69.cnf | timeout | 60.8334 | 61.0054 | 60.8107 | -0.1946 | both_timeout | 0.5142 | 0.0629 | 0.6239 | <NA> | neutral |
| 3sat_71.cnf | timeout | 60.8228 | 60.9958 | 60.7966 | -0.1991 | both_timeout | 0.2913 | 0.1664 | 0.6366 | <NA> | neutral |
| 3sat_75.cnf | timeout | 60.8317 | 61.0177 | 60.8662 | -0.1515 | both_timeout | 0.2908 | 0.4272 | 0.3206 | <NA> | neutral |
| 3sat_82.cnf | medium(10-30s) | 21.4710 | 36.0880 | 21.7471 | -14.3409 | faster_both_solved | 0.8629 | 0.0777 | 0.6466 | 0 | keep_closed |
| 3sat_93.cnf | medium(10-30s) | 18.8329 | 21.5550 | 18.7508 | -2.8042 | faster_both_solved | 0.8189 | 0.7686 | 0.1087 | 0 | keep_closed |

