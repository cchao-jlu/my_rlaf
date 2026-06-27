# Recovery Label 消融结果

本轮目标是验证前一轮结论：MLP selector 容量不是主要瓶颈，下一步应该改
counterfactual trace / recovery label。

我们把 two-stage risk controller 的 recovery head 从旧的
`all_positive` 标签拆成两种更明确的恢复标签：

- `timeout_recovery`：只把 `recovered_timeout` 当作 recovery 正例；
- `timeout_recovery_with_speedup_aux`：把 `recovered_timeout` 作为主正例，
  同时把 `hard_speedup` 作为弱辅助正例。

训练前还修复了一个实现问题：`apply_stage_scope(all)` 之前会覆盖
`recovery_train = label.notna()`，导致新标签模式把 NaN 样本混入训练。
修复后，stage scope 会保留标签模式定义的训练 mask。

## 标签规模

| 模式 | recovery train | positive | negative |
| --- | ---: | ---: | ---: |
| all_positive | 180 | 8 | 172 |
| timeout_recovery | 119 | 5 | 114 |
| timeout_recovery_with_speedup_aux | 122 | 8 | 114 |

`timeout_recovery` 的正例非常少，但语义最干净：它只学习“什么时候 adapter
可能救回 base timeout”，不再把普通 hard speedup 混进恢复检测器。

## Repeated Split

| 方法 | selected | delta solved | lost | recovered | delta time | keep base solved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all_positive two-stage | 0.1013 | +0.44 | 0.12 | 0.56 | -0.0271 | 0.92 |
| timeout_recovery | 0.0991 | +0.6735 | 0.0612 | 0.7347 | -0.1122 | 1.00 |
| timeout_recovery_with_speedup_aux | 0.1022 | +0.50 | 0.06 | 0.56 | -0.0732 | 0.96 |
| MLP two-stage H4 | 0.0909 | +0.68 | 0.02 | 0.70 | -0.2061 | 0.98 |

离线诊断结论：

- `timeout_recovery` 明显优于旧的 `all_positive` 线性 two-stage；
- 加 `hard_speedup` 辅助反而削弱 recovery，不如纯 timeout recovery；
- MLP H4 仍是 repeated split 最强，但 heldout 之前已经没有站住。

## Heldout 正式评估

评估配置：

- split：`data/selector_splits/3sat/heldout_test/{300,350}`
- `feedback_refinement.rollout_conflicts=2000`
- `feedback_refinement.warmup_cpu_lim=15`
- final solver `cpu-lim=60`

| 方法 | 300 solved | 300 mean | 350 solved | 350 mean |
| --- | ---: | ---: | ---: | ---: |
| old ultra-conservative | 100 | 7.8623 | 54 | 34.2257 |
| all_positive two-stage | 100 | 8.0841 | 54 | 34.3281 |
| MLP two-stage H4 | 100 | 8.0688 | 54 | 34.8391 |
| timeout_recovery | 100 | 8.0185 | 54 | 34.2942 |

输出文件：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350_RecoveryTimeoutOnly/eval_two_stage_recovery_timeout_only_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350_RecoveryTimeoutOnly/eval_two_stage_recovery_timeout_only_heldout_350.csv`

## 结论

`timeout_recovery` 是目前最合理的 two-stage 线性标签：

- 比旧 `all_positive` two-stage 更稳；
- 比 MLP H4 的 heldout 更好；
- solved count 与 old ultra 持平；
- 但平均时间仍略慢于 old ultra。

因此仍不跑 `400`。这轮结果说明方向是对的，但训练数据中真正
`recovered_timeout` 正例只有 5 个，信息量不足。下一步应扩充
counterfactual trace，而不是继续调 selector：

1. 在 `selector_train` 之外补充更多 350/400 hard/timeout 候选；
2. 优先收集 base timeout 或接近 timeout 的实例，增加 `recovered_timeout`
   正例密度；
3. 之后再训练 `timeout_recovery` two-stage，若 300/350 heldout 超过 old
   ultra，再跑 400。
