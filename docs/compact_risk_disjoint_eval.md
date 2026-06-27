# Compact Risk Controller Disjoint 评估

本文档记录 compact risk evidence two-stage selector 的正式 disjoint 评估。
比较对象是同一批 CNF 上重新运行的 one-shot baseline。

## Split

- 300：`data/selector_splits/3sat/heldout_test/300/*.cnf`，100 个实例
- 350：`data/selector_splits/3sat/heldout_test/350/*.cnf`，100 个实例
- 400：`data/selector_splits/3sat/hard_recovery_heldout/400/*.cnf`，80 个实例

注意：400 不是完整随机测试集，而是 hard-recovery split 的 heldout 部分。

## 输出文件

- `runs/analysis/compact_risk_disjoint_per_instance.csv`
- `runs/analysis/compact_risk_disjoint_summary.csv`
- `runs/analysis/compact_risk_disjoint_bucket_summary.csv`
- `runs/analysis/compact_risk_disjoint_largest_changes.csv`
- `figures/fig_compact_risk_disjoint_cactus_300_350_400.pdf`

## 总体结果

| size | split | n | base_solved | compact_solved | delta_solved | base_mean_time | compact_mean_time | delta_mean_time | median_delta_time | wins | losses | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | heldout_test/300 | 100 | 100 | 100 | 0 | 7.9924 | 7.6769 | -0.3155 | -0.0838 | 38 | 4 | 0 | 0 | 0 |
| 350 | heldout_test/350 | 100 | 55 | 56 | 1 | 34.1622 | 33.7504 | -0.4118 | 0.0882 | 8 | 23 | 1 | 0 | 44 |
| 400 | hard_recovery_heldout/400 | 80 | 22 | 22 | 0 | 46.4695 | 46.2896 | -0.1799 | 0.2335 | 4 | 16 | 0 | 0 | 58 |

## Difficulty Bucket

bucket 按 one-shot baseline 划分：10s 内为 easy，10-30s 为 medium，
30s 以上为 hard，未解为 timeout。

| size | bucket | n | delta_solved | delta_mean_time | wins | losses | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | easy(<10s) | 66 | 0 | -0.0028 | 18 | 1 | 0 | 0 | 0 |
| 300 | medium(10-30s) | 33 | 0 | -0.2074 | 19 | 3 | 0 | 0 | 0 |
| 300 | hard(>=30s) | 1 | 0 | -24.5208 | 1 | 0 | 0 | 0 | 0 |
| 350 | easy(<10s) | 35 | 0 | 0.1418 | 0 | 13 | 0 | 0 | 0 |
| 350 | medium(10-30s) | 9 | 0 | 0.1249 | 3 | 4 | 0 | 0 | 0 |
| 350 | hard(>=30s) | 11 | 0 | -2.4222 | 4 | 6 | 0 | 0 | 0 |
| 350 | timeout | 45 | 1 | -0.4584 | 1 | 0 | 1 | 0 | 44 |
| 400 | easy(<10s) | 17 | 0 | 0.0542 | 2 | 13 | 0 | 0 | 0 |
| 400 | medium(10-30s) | 3 | 0 | 0.0035 | 1 | 2 | 0 | 0 | 0 |
| 400 | hard(>=30s) | 2 | 0 | -14.3351 | 1 | 1 | 0 | 0 | 0 |
| 400 | timeout | 58 | 0 | 0.2301 | 0 | 0 | 0 | 0 | 58 |

## 最大单实例变化

| size | change_type | file_key | difficulty_bucket | base_result | compact_result | base_time | compact_time | delta_time | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | largest_win | 3sat_180.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 35.3759 | 10.8551 | -24.5208 | faster_both_solved |
| 300 | largest_win | 3sat_65.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 13.5453 | 12.1263 | -1.4190 | faster_both_solved |
| 300 | largest_win | 3sat_130.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 16.1407 | 15.4609 | -0.6798 | faster_both_solved |
| 300 | largest_win | 3sat_181.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 14.3984 | 13.7461 | -0.6524 | faster_both_solved |
| 300 | largest_win | 3sat_52.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 10.3717 | 9.8010 | -0.5707 | faster_both_solved |
| 300 | largest_win | 3sat_46.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 13.7385 | 13.2949 | -0.4437 | faster_both_solved |
| 300 | largest_win | 3sat_160.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 15.7135 | 15.2729 | -0.4406 | faster_both_solved |
| 300 | largest_win | 3sat_43.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 20.3639 | 19.9717 | -0.3922 | faster_both_solved |
| 300 | largest_loss | 3sat_50.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 7.0835 | 11.5596 | 4.4762 | slower_both_solved |
| 300 | largest_loss | 3sat_118.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 25.7797 | 26.0994 | 0.3197 | slower_both_solved |
| 300 | largest_loss | 3sat_12.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 10.0342 | 10.2339 | 0.1997 | slower_both_solved |
| 300 | largest_loss | 3sat_11.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 12.0549 | 12.1562 | 0.1013 | slower_both_solved |
| 300 | largest_loss | 3sat_1.cnf | easy(<10s) | UNSATISFIABLE | UNSATISFIABLE | 8.1573 | 8.2480 | 0.0906 | tie_both_solved |
| 300 | largest_loss | 3sat_147.cnf | easy(<10s) | UNSATISFIABLE | UNSATISFIABLE | 7.8630 | 7.9374 | 0.0744 | tie_both_solved |
| 300 | largest_loss | 3sat_158.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 21.9847 | 22.0470 | 0.0623 | tie_both_solved |
| 300 | largest_loss | 3sat_122.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 2.8304 | 2.8828 | 0.0524 | tie_both_solved |
| 350 | largest_win | 3sat_181.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 31.7340 | 2.8581 | -28.8760 | faster_both_solved |
| 350 | largest_win | 3sat_6.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.6782 | 36.0098 | -24.6684 | recovered_timeout |
| 350 | largest_win | 3sat_164.cnf | hard(>=30s) | UNSATISFIABLE | UNSATISFIABLE | 52.2197 | 50.3967 | -1.8230 | faster_both_solved |
| 350 | largest_win | 3sat_101.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 38.1624 | 37.0433 | -1.1191 | faster_both_solved |
| 350 | largest_win | 3sat_160.cnf | hard(>=30s) | UNSATISFIABLE | UNSATISFIABLE | 32.3367 | 31.4656 | -0.8711 | faster_both_solved |
| 350 | largest_win | 3sat_2.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 15.6071 | 15.2432 | -0.3640 | faster_both_solved |
| 350 | largest_win | 3sat_41.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.1248 | 17.9460 | -0.1789 | faster_both_solved |
| 350 | largest_win | 3sat_112.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 11.2993 | 11.1815 | -0.1178 | faster_both_solved |
| 350 | largest_loss | 3sat_57.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 1.6004 | 3.6962 | 2.0958 | slower_both_solved |
| 350 | largest_loss | 3sat_35.cnf | hard(>=30s) | UNSATISFIABLE | UNSATISFIABLE | 41.1038 | 42.8290 | 1.7252 | slower_both_solved |
| 350 | largest_loss | 3sat_8.cnf | hard(>=30s) | UNSATISFIABLE | UNSATISFIABLE | 57.8770 | 59.4650 | 1.5880 | slower_both_solved |
| 350 | largest_loss | 3sat_1.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 32.1486 | 33.1962 | 1.0476 | slower_both_solved |
| 350 | largest_loss | 3sat_29.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 38.4364 | 39.2724 | 0.8360 | slower_both_solved |
| 350 | largest_loss | 3sat_40.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 22.7436 | 23.5302 | 0.7866 | slower_both_solved |
| 350 | largest_loss | 3sat_23.cnf | medium(10-30s) | UNSATISFIABLE | UNSATISFIABLE | 26.6453 | 27.1858 | 0.5405 | slower_both_solved |
| 350 | largest_loss | 3sat_115.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 32.7442 | 33.1564 | 0.4122 | slower_both_solved |
| 400 | largest_win | 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 31.2569 | 1.3515 | -29.9054 | faster_both_solved |
| 400 | largest_win | 3sat_196.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 26.0840 | 10.6208 | -15.4631 | faster_both_solved |
| 400 | largest_win | 3sat_120.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.3872 | 1.5121 | -1.8751 | faster_both_solved |
| 400 | largest_win | 3sat_1.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.4104 | 3.2642 | -0.1463 | faster_both_solved |
| 400 | largest_win | 3sat_131.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.5741 | 3.5706 | -0.0036 | tie_both_solved |
| 400 | largest_win | 3sat_14.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 5.0711 | 5.1024 | 0.0313 | tie_both_solved |
| 400 | largest_win | 3sat_103.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8452 | 60.9441 | 0.0988 | both_timeout |
| 400 | largest_win | 3sat_10.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8420 | 60.9409 | 0.0988 | both_timeout |
| 400 | largest_loss | 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.1393 | 36.1896 | 15.0503 | slower_both_solved |
| 400 | largest_loss | 3sat_138.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 52.6210 | 53.8562 | 1.2351 | slower_both_solved |
| 400 | largest_loss | 3sat_147.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 11.5974 | 12.0208 | 0.4234 | slower_both_solved |
| 400 | largest_loss | 3sat_181.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 2.3881 | 2.7605 | 0.3723 | slower_both_solved |
| 400 | largest_loss | 3sat_3.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8365 | 61.1743 | 0.3379 | both_timeout |
| 400 | largest_loss | 3sat_28.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8390 | 61.1581 | 0.3191 | both_timeout |
| 400 | largest_loss | 3sat_187.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8506 | 61.1697 | 0.3191 | both_timeout |
| 400 | largest_loss | 3sat_35.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8548 | 61.1698 | 0.3151 | both_timeout |

## 结论

- compact risk controller 在 300/350/400 三个 disjoint split 上没有 lost solution。
- 300 和 350 都保持 100/100 solved，并带来小幅平均时间下降。
- 400 hard-recovery heldout 上 solved count 与 one-shot 持平；平均时间略降，
  但 timeout bucket 没有 recovered_timeout，说明这个 heldout split 对 recovery 能力
  仍然不够敏感。
- 当前结果支持“risk gate 能防止翻车并带来稳定小收益”，但还不能证明
  它在真正 400 timeout recovery 上有强恢复能力。
