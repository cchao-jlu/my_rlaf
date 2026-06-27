# Two-Stage MLP Risk Controller 评估

本轮目标是验证一个小容量非线性 selector 是否能解决线性 two-stage
selector 的表达力瓶颈。结构保持不变：

```text
use_adapter = hard_recovery_detector && !easy_risk_gate
```

区别是 `easy-risk gate` 和 `hard-recovery detector` 从线性 head 换成
hidden dim 为 `4` 的小 MLP，并且 checkpoint 可直接部署：

- `selector_mode: two_stage_mlp`
- `risk_selector_mlp_weights / risk_selector_mlp_biases`
- `recovery_selector_mlp_weights / recovery_selector_mlp_biases`

## 训练命令

```bash
python3 train_two_stage_risk_controller.py \
  --trace data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_traces.pt \
  --checkpoint runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  --output-dir runs/GNN_Glucose_3SAT_TwoStageMLPRiskControllerMultipoint300350_H4 \
  --doc-path docs/two_stage_mlp_risk_controller_multipoint_300350_h4.md \
  --stage-scope all \
  --stage-model mlp \
  --mlp-hidden-dim 4 \
  --epochs 800 \
  --lr 0.01 \
  --l2 0.01 \
  --max-selected-fraction 0.12 \
  --split-seeds 50
```

## Repeated Split

| 方法 | selected | delta solved | lost | recovered | delta time | keep base solved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| old ultra | 0.0477 | -0.02 | 0.02 | 0.00 | -0.0312 | 0.98 |
| linear two-stage | 0.1013 | +0.44 | 0.12 | 0.56 | -0.0271 | 0.92 |
| DriftStats single-stage | 0.1013 | +0.68 | 0.04 | 0.72 | -0.1837 | 0.96 |
| MLP two-stage H4 | 0.0909 | +0.68 | 0.02 | 0.70 | -0.2061 | 0.98 |

离线 repeated split 上，MLP two-stage 是更好的 risk-controller 形态：

- solved delta 与 DriftStats 持平；
- lost 更低；
- 平均时间改善更大；
- 比线性 two-stage 明显更稳。

## Heldout 正式评估

评估配置：

- split：`data/selector_splits/3sat/heldout_test/{300,350}`
- `feedback_refinement.rollout_conflicts=2000`
- `feedback_refinement.warmup_cpu_lim=15`
- final solver `cpu-lim=60`

| 方法 | 300 solved | 300 mean | 350 solved | 350 mean |
| --- | ---: | ---: | ---: | ---: |
| old ultra-conservative | 100 | 7.8623 | 54 | 34.2257 |
| linear two-stage | 100 | 8.0841 | 54 | 34.3281 |
| DriftStats single-stage | 100 | 8.5429 | 53 | 34.5965 |
| MLP two-stage H4 | 100 | 8.0688 | 54 | 34.8391 |

输出文件：

- `runs/GNN_Glucose_3SAT_TwoStageMLPRiskControllerMultipoint300350_H4/eval_two_stage_mlp_h4_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_TwoStageMLPRiskControllerMultipoint300350_H4/eval_two_stage_mlp_h4_heldout_350.csv`

## 结论

MLP two-stage 没有成为新的主线结果：

- `300` 不丢解，但仍慢于 old ultra；
- `350` solved count 与 old ultra/linear two-stage 持平，平均时间更慢；
- repeated split 的离线优势没有转化成 heldout 优势。

因此当前不跑 `400`。这轮结果说明 selector 容量不是主要瓶颈，继续堆更复杂
selector 风险很高。下一步应回到反事实 trace 的信息质量：

1. 扩充 risk-focused counterfactual trace 的训练来源，不只依赖当前
   `selector_train` 的 200 个样本；
2. 改 recovery 标签，让 timeout recovery 与普通 hard speedup 分开训练；
3. 对 recovery detector 使用 pairwise/ranking 目标，学习“哪些 hard/timeout
   实例更值得冒险”，而不是只做稀疏二分类。
