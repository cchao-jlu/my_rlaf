# 多点 Drift Selector 接入与评估

本轮把多点 rollout evidence 从离线 CSV 诊断推进到可部署推理路径：

- `evaluate_guided_solver.py` 支持同一次评估中跑多个 evidence probe；
- 当前使用 `500 / 1000 / 2000` conflicts；
- 模型 selector 可以读取预计算的 graph-level selector features；
- 支持特征包括：
  - `warmup_c{t}_event_entropy_norm`
  - `warmup_c{t}_event_top10_mass`
  - `warmup_c{t}_rho_event_corr`
  - `warmup_c{t}_decisions`
  - `warmup_c{t}_propagations`
  - `warmup_c{t}_cpu_time`
  - `warmup_c{t2}_minus_warmup_c{t1}_...`

## 新增候选

### DriftNeg2

只使用 event/rho/delta 的多点与 drift 特征。

Repeated split 结果：

| split | selected | delta solved | lost | recovered | delta time |
| --- | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.0987 | +0.04 | 0.14 | 0.18 | +0.0268 |
| 300 | 0.0804 | 0.00 | 0.00 | 0.00 | +0.0642 |
| 350 | 0.1169 | +0.04 | 0.14 | 0.18 | -0.0106 |

结论：更安全，但 recovery 基本被压掉，且 300 明显增加时间开销。

### DriftStatsNeg2

在 drift 特征基础上加入 rollout 动力学统计：

- `warmup_c500_decisions`
- `warmup_c1000_decisions`
- `warmup_c2000_decisions`
- `warmup_c500_propagations`
- `warmup_c1000_propagations`
- `warmup_c2000_propagations`
- `warmup_c500_cpu_time`
- `warmup_c1000_cpu_time`
- `warmup_c2000_cpu_time`

Repeated split 结果：

| split | selected | delta solved | lost | recovered | delta time |
| --- | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.1013 | +0.68 | 0.04 | 0.72 | -0.1837 |
| 300 | 0.0276 | 0.00 | 0.00 | 0.00 | +0.0046 |
| 350 | 0.1751 | +0.68 | 0.04 | 0.72 | -0.3720 |

离线 repeated split 看起来明显优于 `Neg2`，因此进行了 heldout 正式评估。

## Heldout 正式评估

评估配置：

- checkpoint：`runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_DriftStatsNeg2/best.pt`
- split：`data/selector_splits/3sat/heldout_test/{300,350}`
- `feedback_refinement.rollout_conflicts=2000`
- `feedback_refinement.warmup_cpu_lim=15`
- final solver `cpu-lim=60`

| 方法 | 300 solved | 300 mean | 350 solved | 350 mean |
| --- | ---: | ---: | ---: | ---: |
| old ultra-conservative | 100 | 7.8623 | 54 | 34.2257 |
| old risk-focused conservative | 100 | 8.5011 | 54 | 34.4550 |
| multipoint Neg2 | 100 | 8.0819 | 53 | 35.2614 |
| DriftStatsNeg2 | 100 | 8.5429 | 53 | 34.5965 |

输出文件：

- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_DriftStatsNeg2/eval_drift_stats_neg2_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_DriftStatsNeg2/eval_drift_stats_neg2_heldout_350.csv`

## 结论

多点 drift 与 rollout 统计特征已经可以端到端部署，但 heldout 结果没有
超过旧的 ultra-conservative selector：

- `300` 不丢解，但时间开销更大；
- `350` 仍只解出 `53 / 100`，低于旧 selector 的 `54 / 100`；
- repeated split 的 recovery 信号没有泛化到 heldout。

因此当前不建议跑 `400`，也不建议把 DriftStatsNeg2 作为主线结果。

下一步应转向更明确的 risk-controller 结构，而不是继续堆线性特征：

1. 先训练 easy-risk gate，只负责判定“不能开 adapter”；
2. 再训练 hard-recovery detector，只在高置信 hard timeout 候选上开 adapter；
3. 两个模型的目标分开优化，避免一个线性分类器同时承担避险和救援。
