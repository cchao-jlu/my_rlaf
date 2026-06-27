# 多点 Counterfactual Risk Selector 训练结果

本轮使用 `risk_focused_multipoint_selector_train_300350_traces.pt` 训练
conservative risk selector。该 trace 的 intervention evidence 来自
`500 / 1000 / 2000` conflicts 三个采样点，最终分支标签在
`2000` conflicts 后生成。

## 训练输入

- trace：`data/counterfactual_trace/risk_focused_multipoint_selector_train_300350_traces.pt`
- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt`
- 可部署特征：
  - `base_rho_mean`
  - `delta_abs_mean`
  - `delta_mu_abs_mean`
  - `event_gate_mean`
  - `event_entropy_norm`
  - `event_top05_mass`
  - `event_top10_mass`
  - `rho_event_corr`
  - `rho_event_top10_overlap`
  - `event_conf_learnt_log_mean`
  - `event_conf_learnt_rate_mean`
  - `event_conf_learnt_rank_mean`

说明：这次保存为 checkpoint 的 selector 只使用最终 event state 可计算的
特征，因此能被现有 `evaluate_guided_solver.py` 直接加载。多点 drift
列已经保存在 outcome CSV 中，但暂时不写入 checkpoint，否则现有评估
流程无法在推理时重建这些 graph-level drift 特征。

## 候选结果

| 版本 | 输出目录 | selected | delta solved | lost | recovered | delta time |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Conservative | `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Conservative` | 0.0878 | +0.28 | 0.34 | 0.62 | -0.2230 |
| Neg2 | `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2` | 0.0811 | +0.28 | 0.32 | 0.60 | -0.2108 |
| Max05 | `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Max05` | 0.0311 | +0.04 | 0.14 | 0.18 | -0.0116 |

表中数值来自 50 次 repeated split 的 `300+350` heldout 平均。

## 当前选择

当前主线候选建议使用 `Neg2`：

- 相比 `Conservative`，`Neg2` 的 selected fraction 更低，lost 略低；
- recovered 和 delta solved 基本保持；
- wall-clock time 仍然保持正收益；
- 相比 `Max05`，它没有过度熔断，保留了更多恢复 timeout 的能力。

`Max05` 可以保留为安全下界消融：它说明强行压低 selected fraction
可以进一步减少 lost，但同时几乎抹掉 recovery 和时间收益。

## 下一步

下一步应在 disjoint 300/350 上评估 `Neg2`：

```bash
python3 evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/best.pt \
  dataset.eval_path='data/selector_splits/3sat/disjoint_test/300/*.cnf' \
  save_file=eval_multipoint_neg2_disjoint_300.csv

python3 evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocusedMultipoint300350_Neg2/best.pt \
  dataset.eval_path='data/selector_splits/3sat/disjoint_test/350/*.cnf' \
  save_file=eval_multipoint_neg2_disjoint_350.csv
```

如果 disjoint 结果满足 `300` 不明显变慢、`350` solved 不低于 one-shot，
再考虑进入 `400` 测试；否则继续改 selector 的风险目标或使用多点
drift 做两阶段离线 gate。
