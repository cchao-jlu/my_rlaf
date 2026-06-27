# recovered_timeout 重复运行稳定性标注

本报告只针对训练 trace 中原本标为 `recovered_timeout` 的样本。
每个候选重复执行 warmup -> event state -> base/adapter 分支，
用 `recovered_rate = P(base 未解且 adapter 解出)` 估计恢复稳定性。

训练时不会翻转原始标签，只会把 `recovered_timeout` 的 recovery detector
样本权重乘以 `recovery_stability_weight`，从而降低不稳定恢复样本的影响。

## 配置

- repeats：`1`
- min weight：`0.15`
- stable threshold：`0.6`
- detail csv：`runs/analysis/recovered_timeout_stability_smoke_repeats.csv`
- summary csv：`runs/analysis/recovered_timeout_stability_smoke_summary.csv`

## 按规模汇总

| size | n | stable_recovered | recovered_rate_mean | stability_weight_mean |
| --- | --- | --- | --- | --- |
| 400 | 1 | 0 | 0.0000 | 0.1500 |

## 候选明细

| size | file_key | repeats | recovered_rate | base_unsolved_rate | adapter_solved_rate | base_mean_time | adapter_mean_time | recovery_stability_weight | stable_recovered |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 400 | 3sat_148.cnf | 1 | 0.0000 | 1.0000 | 0.0000 | 1.9904 | 1.9939 | 0.1500 | False |

