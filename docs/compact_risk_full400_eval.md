# Compact Risk Controller 完整 400 测试集评估

本文档记录 compact risk evidence two-stage selector 在完整
`data/test/3sat/400/*.cnf` 上的重新评估。比较对象是同一批 CNF 上
重新运行的 one-shot baseline。

## 输出文件

- `runs/analysis/compact_risk_full400_per_instance.csv`
- `runs/analysis/compact_risk_full400_summary.csv`
- `runs/analysis/compact_risk_full400_bucket_summary.csv`
- `runs/analysis/compact_risk_full400_largest_changes.csv`
- `figures/fig_compact_risk_full400_cactus.pdf`

## 总体结果

| size | split | n | base_solved | compact_solved | delta_solved | base_mean_time | compact_mean_time | delta_mean_time | median_delta_time | wins | losses | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 400 | data/test/3sat/400 | 200 | 50 | 56 | 6 | 47.7517 | 46.3484 | -1.4033 | 0.1359 | 12 | 33 | 6 | 0 | 144 |

## Difficulty Bucket

bucket 按 one-shot baseline 划分：10s 内为 easy，10-30s 为 medium，
30s 以上为 hard，未解为 timeout。

| bucket | n | delta_solved | delta_mean_time | wins | losses | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| easy(<10s) | 37 | 0 | 0.7615 | 2 | 26 | 0 | 0 | 0 |
| medium(10-30s) | 9 | 0 | -1.8766 | 2 | 5 | 0 | 0 | 0 |
| hard(>=30s) | 4 | 0 | -7.1781 | 2 | 2 | 0 | 0 | 0 |
| timeout | 150 | 6 | -1.7549 | 6 | 0 | 6 | 0 | 144 |

## 最大单实例变化

| change_type | file_key | difficulty_bucket | base_result | compact_result | base_time | compact_time | delta_time | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| largest_win | 3sat_89.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.7633 | 0.9720 | -59.7913 | recovered_timeout |
| largest_win | 3sat_85.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.7717 | 1.4759 | -59.2958 | recovered_timeout |
| largest_win | 3sat_97.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.7605 | 12.4787 | -48.2818 | recovered_timeout |
| largest_win | 3sat_189.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.7532 | 14.8203 | -45.9329 | recovered_timeout |
| largest_win | 3sat_188.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.8011 | 26.3512 | -34.4499 | recovered_timeout |
| largest_win | 3sat_163.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.8197 | 29.2935 | -31.5262 | recovered_timeout |
| largest_win | 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 30.7425 | 1.0575 | -29.6850 | faster_both_solved |
| largest_win | 3sat_128.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 29.1131 | 7.5215 | -21.5917 | faster_both_solved |
| largest_win | 3sat_196.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 25.1129 | 10.3172 | -14.7956 | faster_both_solved |
| largest_win | 3sat_120.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.1629 | 1.4870 | -1.6759 | faster_both_solved |
| largest_win | 3sat_122.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 60.0490 | 59.4942 | -0.5548 | faster_both_solved |
| largest_win | 3sat_168.cnf | timeout | INDETERMINATE | INDETERMINATE | 60.8354 | 60.7115 | -0.1239 | both_timeout |
| largest_loss | 3sat_157.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.2106 | 27.9502 | 24.7396 | slower_both_solved |
| largest_loss | 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.4710 | 36.0880 | 14.6170 | slower_both_solved |
| largest_loss | 3sat_93.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.8329 | 21.5550 | 2.7221 | slower_both_solved |
| largest_loss | 3sat_140.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 39.7812 | 41.0826 | 1.3013 | slower_both_solved |
| largest_loss | 3sat_54.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.0357 | 18.9037 | 0.8679 | slower_both_solved |
| largest_loss | 3sat_180.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 13.6719 | 14.3728 | 0.7009 | slower_both_solved |
| largest_loss | 3sat_20.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 10.3011 | 10.8629 | 0.5618 | slower_both_solved |
| largest_loss | 3sat_22.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 1.7926 | 2.1633 | 0.3707 | slower_both_solved |
| largest_loss | 3sat_92.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 7.6922 | 8.0256 | 0.3334 | slower_both_solved |
| largest_loss | 3sat_125.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.1999 | 3.5243 | 0.3244 | slower_both_solved |
| largest_loss | 3sat_19.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 3.6099 | 3.9099 | 0.3000 | slower_both_solved |
| largest_loss | 3sat_25.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 1.6911 | 1.9812 | 0.2900 | slower_both_solved |

## 结论

- compact risk controller 在完整 400 测试集上没有 lost solution。
- solved count 从 one-shot 的 50 提升到 56，恢复 6 个 timeout。
- 平均总时间从 47.75s 降到 46.35s，平均冲突数也下降。
- 主要收益来自少数 hard/timeout 实例的大幅改善；easy/medium 上仍有一些小幅 slowdown。
- 这个结果比 hard-recovery heldout 更关键：它说明 compact risk gate 不只是安全，
  在完整 400 分布上也出现了真实 timeout recovery。
