# Hard-Recovery Trace 扩充结果

本轮目标是解决 `timeout_recovery` 正例太少的问题。原始
300/350 selector trace 中只有 5 个 `recovered_timeout`，不足以支撑
recovery detector。

## 新增数据

新增脚本：

- `create_hard_recovery_split.py`

它从 `data/test/3sat/400` 中构造一个 hard-recovery split：

- `hard_recovery_train/400`：120 个训练候选；
- `hard_recovery_heldout/400`：80 个保留候选；
- manifest：`data/selector_splits/3sat/hard_recovery_manifest.csv`。

重要：split 按 raw adapter 的已有 400 结果分层，而不是 gated selector
结果。这样训练集包含 raw adapter 已知恢复样本：

| split | bucket | count |
| --- | --- | ---: |
| hard_recovery_train | known_recovered | 12 |
| hard_recovery_train | known_lost | 8 |
| hard_recovery_train | both_timeout | 100 |
| hard_recovery_heldout | both_timeout | 37 |
| hard_recovery_heldout | other | 43 |

新增 trace 配置：

- `configs/config_generate_counterfactual_outcome_traces_hard_recovery_400.yaml`

输出：

- `data/counterfactual_trace/hard_recovery_400_train_traces.pt`
- `data/counterfactual_trace/hard_recovery_400_train_outcomes.csv`
- `docs/counterfactual_outcome_trace_hard_recovery_400_train.md`

## 新 Trace 标签

400 hard-recovery trace 生成结果：

| class | count |
| --- | ---: |
| neutral | 94 |
| negative | 12 |
| positive | 12 |
| warmup_solved | 2 |

原因分布：

| reason | count |
| --- | ---: |
| recovered_timeout | 8 |
| hard_speedup | 4 |
| lost_solution | 5 |
| easy_slowdown | 4 |
| slowdown | 3 |

合并旧 300/350 trace 后：

- `recovered_timeout` 从 5 个增加到 13 个；
- recovery train 样本从 119 增加到 223；
- risk train 样本从 180 增加到 298。

## Selector 训练结果

### 直接合并 300/350/400

checkpoint：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350400_RecoveryTimeoutOnly`

Repeated split：

| heldout | selected | delta solved | lost | recovered | delta time | keep base |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.1024 | +0.78 | 0.38 | 1.16 | -0.2953 | 0.90 |
| 300 | 0.0191 | 0.00 | 0.00 | 0.00 | +0.0113 | 1.00 |
| 350 | 0.0969 | +0.22 | 0.00 | 0.22 | -0.0965 | 1.00 |
| 400 | 0.1702 | +0.56 | 0.38 | 0.94 | -0.6809 | 0.84 |

结论：recovery 明显增强，但 400 lost 也上升，risk controller 不够稳。

### 更保守阈值 `max_selected_fraction=0.08`

checkpoint：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350400_RecoveryTimeoutOnly_Max08`

Repeated split：

| heldout | selected | delta solved | lost | recovered | delta time | keep base |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.0730 | +0.40 | 0.26 | 0.66 | -0.1872 | 0.88 |
| 350 | 0.0644 | +0.14 | 0.00 | 0.14 | -0.0426 | 1.00 |
| 400 | 0.1254 | +0.26 | 0.26 | 0.52 | -0.4441 | 0.84 |

结论：降低选择率能降低 recovery 和 lost，但没有解决 400 keep-base 问题。

### 分源训练

配置：

- risk gate 只用 `300,350`；
- recovery detector 用 `350,400`。

checkpoint：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350400_SplitStageSizes`

Repeated split：

| heldout | selected | delta solved | lost | recovered | delta time | keep base |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.1031 | +0.68 | 0.18 | 0.86 | -0.2176 | 0.92 |
| 300 | 0.0836 | 0.00 | 0.00 | 0.00 | +0.0403 | 1.00 |
| 350 | 0.1160 | +0.34 | 0.06 | 0.40 | -0.1871 | 0.94 |
| 400 | 0.1081 | +0.34 | 0.12 | 0.46 | -0.4377 | 0.90 |

结论：分源训练比直接合并更稳，但仍不够安全，且 300/350 被带得更激进。

## 当前结论

扩充 hard-recovery trace 是有效的：`recovered_timeout` 正例从 5 增加到
13，400 上的 recovery 信号明显增强。

但这也暴露了新的瓶颈：risk gate 当前特征不足以识别 400 上新增的
lost/slowdown 风险。直接训练或降低选择率都不能同时满足：

- 保持 300/350 不退化；
- 在 400 上恢复更多 timeout；
- 不显著丢 base-solved 实例。

因此本轮不跑正式 400。下一步应该改 risk gate 的证据，而不是继续扩大
trace 或堆 MLP：

1. 给 risk gate 增加“base-solved risk”特征，例如 warmup solve proximity、
   base rho 分布尾部、event concentration 的极端值；
2. 或者把 risk gate 训练成 one-class / anomaly-style：只要像 easy/medium
   solved，就强制 fallback；
3. 保留 400 hard-recovery trace 作为 recovery detector 的正例来源。
