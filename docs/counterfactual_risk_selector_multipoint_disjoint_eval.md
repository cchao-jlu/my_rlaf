# 多点 Neg2 Risk Selector 的 Heldout 评估

本轮评估使用 `RiskFocusedMultipoint300350_Neg2` checkpoint，在
`data/selector_splits/3sat/heldout_test/{300,350}` 上运行。

注意：该 selector 的训练 trace 使用 `2000` conflicts 作为最终
intervention evidence，因此本次评估也显式设置：

- `feedback_refinement.rollout_conflicts=2000`
- `feedback_refinement.warmup_cpu_lim=15`

## 运行命令

```bash
python3 evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/300/*.cnf' \
  save_file=eval_multipoint_neg2_heldout_300.csv \
  feedback_refinement.rollout_conflicts=2000 \
  feedback_refinement.warmup_cpu_lim=15

python3 evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/350/*.cnf' \
  save_file=eval_multipoint_neg2_heldout_350.csv \
  feedback_refinement.rollout_conflicts=2000 \
  feedback_refinement.warmup_cpu_lim=15
```

## 输出文件

- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/eval_multipoint_neg2_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/eval_multipoint_neg2_heldout_350.csv`

## 结果

| split | solved | mean total time | mean final CPU | mean GPU/refine |
| --- | ---: | ---: | ---: | ---: |
| 300 heldout | 100 / 100 | 8.0819 | 7.4524 | 0.5986 |
| 350 heldout | 53 / 100 | 35.2614 | 34.4567 | 0.7706 |

## 与已有 heldout 结果对比

| 方法 | 300 solved | 300 mean | 350 solved | 350 mean |
| --- | ---: | ---: | ---: | ---: |
| old ultra-conservative | 100 | 7.8623 | 54 | 34.2257 |
| old risk-focused conservative | 100 | 8.5011 | 54 | 34.4550 |
| multipoint Neg2 | 100 | 8.0819 | 53 | 35.2614 |

## 结论

`Neg2` 在训练 split 的 repeated-split 诊断上看起来更好，但 heldout
正式评估没有站住：

- `300` 没丢解，但平均时间仍慢于 old ultra-conservative；
- `350` solved count 下降到 `53 / 100`，低于旧 selector 的 `54 / 100`；
- 平均时间也变差。

因此当前不建议继续跑 `400`。下一步应该回到 selector 形式或 evidence
使用方式上：仅靠最终 2000-conflict event state 的线性 selector 仍然
不能稳定泛化。更合理的方向是把多点 drift 特征接入推理流程，或者做
两阶段 selector：先识别 easy-risk，再识别 hard-recovery。
