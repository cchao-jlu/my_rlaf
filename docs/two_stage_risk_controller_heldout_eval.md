# Two-Stage Risk Controller 实现与 Heldout 评估

本轮实现了真正的 two-stage risk controller：

```text
use_adapter = hard_recovery_detector && !easy_risk_gate
```

它不是一个单线性 selector，而是两个独立线性头：

- `easy-risk gate`：识别 adapter 可能造成 lost / slowdown 的情形；
- `hard-recovery detector`：识别 adapter 可能恢复 timeout 或明显加速 hard instance 的情形。

## 代码改动

- `src/model/model.py`
  - 新增 `selector_mode=two_stage`
  - 新增 `risk_selector_*` 与 `recovery_selector_*` 配置字段
  - 推理时先计算 risk/recovery 两个概率，再执行 AND/NOT 门控
- `evaluate_guided_solver.py`
  - 已支持 two-stage checkpoint 的多点 `warmup_c*` 与 drift 特征
- `train_two_stage_risk_controller.py`
  - 新增 two-stage 训练脚本
  - 阈值选择优先级：
    1. 最小化 `lost_solution`
    2. 最大化 `recovered_timeout`
    3. 最大化 solved delta
    4. 最小化平均时间

## 训练数据

- trace：`data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_traces.pt`
- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt`
- output：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350`

## Repeated Split

| 方法 | selected | delta solved | lost | recovered | delta time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Neg2 single-stage | 0.0811 | +0.28 | 0.32 | 0.60 | -0.2108 |
| DriftStats single-stage | 0.1013 | +0.68 | 0.04 | 0.72 | -0.1837 |
| TwoStage grid | 0.1013 | +0.44 | 0.12 | 0.56 | -0.0271 |

解释：two-stage 比普通 `Neg2` 更稳，但 repeated split 上仍不如
`DriftStats` 单头。它的价值主要是结构更符合 risk controller 叙事，
而不是当前数值最强。

## Heldout 正式评估

评估 split：

- `data/selector_splits/3sat/heldout_test/300/*.cnf`
- `data/selector_splits/3sat/heldout_test/350/*.cnf`

评估配置：

- `feedback_refinement.rollout_conflicts=2000`
- `feedback_refinement.warmup_cpu_lim=15`
- final solver `cpu-lim=60`

| 方法 | 300 solved | 300 mean | 350 solved | 350 mean |
| --- | ---: | ---: | ---: | ---: |
| old ultra-conservative | 100 | 7.8623 | 54 | 34.2257 |
| multipoint Neg2 | 100 | 8.0819 | 53 | 35.2614 |
| DriftStatsNeg2 | 100 | 8.5429 | 53 | 34.5965 |
| TwoStage | 100 | 8.0841 | 54 | 34.3281 |

输出文件：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350/eval_two_stage_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerMultipoint300350/eval_two_stage_heldout_350.csv`

## 结论

Two-stage 版本比 `multipoint Neg2` 更稳：`350` solved count 从 `53`
恢复到 `54`，与 old ultra-conservative 持平；同时 `300` 不丢解。

但它还没有超过 old ultra-conservative：

- `300` 平均时间更慢；
- `350` solved 持平，平均时间略慢；
- 因此当前仍不建议直接跑 `400` 作为主结果。

下一步更合理的是保留 two-stage 结构，但调整目标：

1. `easy-risk gate` 只训练在 base-solved / easy-medium 样本上，专门做
   “不许翻车”；
2. `hard-recovery detector` 只训练在 timeout/hard 样本上，避免被大量
   easy neutral 稀释；
3. 两个 head 使用不同训练子集，而不是当前这种全 eligible 样本共享训练。
