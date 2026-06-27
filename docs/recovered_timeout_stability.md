# recovered_timeout 重复运行稳定性标注

本报告只针对训练 trace 中原本标为 `recovered_timeout` 的样本。
每个候选重复执行 warmup -> event state -> base/adapter 分支，
用 `recovered_rate = P(base 未解且 adapter 解出)` 估计恢复稳定性。

训练时不会翻转原始标签，只会把 `recovered_timeout` 的 recovery detector
样本权重乘以 `recovery_stability_weight`，从而降低不稳定恢复样本的影响。

## 配置

- repeats：`3`
- min weight：`0.15`
- stable threshold：`0.6`
- detail csv：`runs/analysis/recovered_timeout_stability_repeats.csv`
- summary csv：`runs/analysis/recovered_timeout_stability_summary.csv`

## 按规模汇总

| size | n | stable_recovered | recovered_rate_mean | stability_weight_mean |
| --- | --- | --- | --- | --- |
| 350 | 5 | 5 | 1.0000 | 1.0000 |
| 400 | 8 | 8 | 1.0000 | 1.0000 |

## 候选明细

| size | file_key | repeats | recovered_rate | base_unsolved_rate | adapter_solved_rate | base_mean_time | adapter_mean_time | recovery_stability_weight | stable_recovered |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 350 | 3sat_125.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9853 | 46.1631 | 1.0000 | True |
| 350 | 3sat_182.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9805 | 31.1149 | 1.0000 | True |
| 350 | 3sat_51.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9544 | 13.8343 | 1.0000 | True |
| 350 | 3sat_70.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9499 | 10.0405 | 1.0000 | True |
| 350 | 3sat_81.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9684 | 21.2450 | 1.0000 | True |
| 400 | 3sat_148.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9820 | 16.0939 | 1.0000 | True |
| 400 | 3sat_163.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9769 | 29.1926 | 1.0000 | True |
| 400 | 3sat_188.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9838 | 25.6874 | 1.0000 | True |
| 400 | 3sat_189.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9603 | 13.8941 | 1.0000 | True |
| 400 | 3sat_40.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9839 | 17.5148 | 1.0000 | True |
| 400 | 3sat_85.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9738 | 0.7137 | 1.0000 | True |
| 400 | 3sat_89.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9783 | 0.1781 | 1.0000 | True |
| 400 | 3sat_97.cnf | 3 | 1.0000 | 1.0000 | 1.0000 | 59.9728 | 11.8751 | 1.0000 | True |

