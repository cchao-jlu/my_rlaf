# Counterfactual Risk Selector 训练结果

本文档记录第一版基于 same-evidence counterfactual outcome traces 训练得到的 selector。

训练 trace：

- `data/counterfactual_trace/small300_counterfactual_outcome_traces.pt`
- `data/counterfactual_trace/small350_counterfactual_outcome_traces.pt`

使用特征：

- `base_rho_mean`
- `delta_mu_abs_mean`
- `event_gate_mean`
- `event_top10_mass`
- `rho_event_corr`

## 训练变体

| variant | output dir | negative weight scale | max selected fraction |
| --- | --- | --- | --- |
| balanced conservative | `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350` | 2.0 | 0.25 |
| ultra conservative | `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350_UltraConservative` | 4.0 | 0.10 |

## Repeated-Split 对比

| variant | selected fraction | delta solved vs base | lost solution | recovered timeout | delta time vs base | keeps base solved rate | beats base time rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| balanced conservative | 0.1945 | -0.1400 | 0.1400 | 0.0000 | +0.1087 | 0.8600 | 0.1800 |
| ultra conservative | 0.0477 | -0.0200 | 0.0200 | 0.0000 | -0.0312 | 0.9800 | 0.3200 |

## 全数据拟合策略

| variant | selected fraction | base solved | adapter solved | selector solved | lost solution | recovered timeout | delta time vs base |
| --- | --- | --- | --- | --- | --- | --- | --- |
| balanced conservative | 0.1596 | 73 | 71 | 73 | 0 | 0 | -0.6301 |
| ultra conservative | 0.0851 | 73 | 71 | 73 | 0 | 0 | -0.1261 |

## 结论

采用 ultra-conservative checkpoint 作为当前 risk-controller 候选：

```text
runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350_UltraConservative/best.pt
```

它是刻意保守的。在当前 small trace set 上，它还不能恢复 timeout 实例，但在 repeated split 中几乎不丢 base-solved 实例，并且平均时间略有改善。这正是 risk controller 第一阶段最应该满足的性质。

评估配置：

```text
configs/config_eval_guided_solver_counterfactual_risk_selector.yaml
```

下一步应在干净的 disjoint 300/350 实例上评估，然后再扩展到 400。

后续 disjoint 300/350 评估记录在：

```text
docs/counterfactual_risk_selector_disjoint_300350.md
```

该评估没有复现稳定收益，因此当前不继续跑 400；下一步应先改 counterfactual label/rollout evidence。
