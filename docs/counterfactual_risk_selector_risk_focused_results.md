# Risk-Focused Counterfactual Selector 训练与评估结果

本文档记录使用 `risk_focused_selector_train_300350_traces.pt` 训练的新 conservative selector 结果。

## 训练数据

trace：

```text
data/counterfactual_trace/risk_focused_selector_train_300350_traces.pt
```

标签分布：

| size | eligible | positive | negative | neutral | warmup_solved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 300 | 92 | 1 | 16 | 75 | 8 |
| 350 | 94 | 6 | 18 | 70 | 6 |

reason 分布：

| size | recovered_timeout | hard_speedup | lost_solution | easy_slowdown | slowdown | neutral |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | 0 | 1 | 0 | 16 | 0 | 75 |
| 350 | 5 | 1 | 4 | 9 | 5 | 70 |

## 训练配置

主训练命令：

```bash
python3 train_counterfactual_risk_selector.py \
  --trace data/counterfactual_trace/risk_focused_selector_train_300350_traces.pt \
  --checkpoint runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  --output-dir runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_Conservative \
  --doc-path docs/counterfactual_risk_selector_risk_focused_300350_conservative.md \
  --negative-weight-scale 1.0 \
  --max-selected-fraction 0.10 \
  --epochs 1000 --lr 0.05 --l2 0.001
```

checkpoint：

```text
runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_Conservative/best.pt
```

selector：

- features：`base_rho_mean`, `delta_mu_abs_mean`, `event_gate_mean`, `event_top10_mass`, `rho_event_corr`
- threshold：`0.201734`
- selected fraction：`0.0968`

## 训练集拟合

| selected fraction | base solved | adapter solved | selector solved | lost solution | recovered timeout | selector mean | delta vs base |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0968 | 135 | 136 | 136 | 0 | 1 | 22.7591 | -0.1287 |

## Repeated-Split 诊断

| heldout | selected fraction | delta solved vs base | lost solution | recovered timeout | delta time vs base | keeps base solved rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300+350 | 0.0783 | -0.1200 | 0.1400 | 0.0200 | +0.0780 | 0.8600 |
| 300 | 0.0730 | 0.0000 | 0.0000 | 0.0000 | +0.0127 | 1.0000 |
| 350 | 0.0834 | -0.1200 | 0.1400 | 0.0200 | +0.1420 | 0.8600 |

诊断结论：训练集拟合看起来安全，但 repeated split 暴露出 350 上仍有 lost-solution risk。它还不能作为主候选。

## 更保守变体

额外训练了两版：

| output dir | negative-weight-scale | max-selected-fraction | result |
| --- | ---: | ---: | --- |
| `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_UltraConservative` | 2.0 | 0.05 | selected fraction 0，退化为不开 adapter |
| `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_Max05` | 1.0 | 0.05 | selected fraction 0，退化为不开 adapter |

这说明当前 feature space 下，能选到 recovered case 的阈值区间也会选到一部分风险实例；继续靠调 threshold 很难解决。

## Disjoint Heldout 评估

评估命令：

```bash
python3 evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_Conservative/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/300/*.cnf' \
  save_file=eval_risk_focused_conservative_heldout_300.csv

python3 evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  checkpoint=runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorRiskFocused300350_Conservative/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/350/*.cnf' \
  save_file=eval_risk_focused_conservative_heldout_350.csv
```

结果：

| size | method | n | solved | mean time | median time | mean conflicts | mean decisions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | one-shot | 100 | 100 | 7.7159 | 7.2823 | 268855.43 | 304454.56 |
| 300 | fixed-rho | 100 | 100 | 7.5556 | 6.8847 | 264998.83 | 300020.91 |
| 300 | old cf-risk | 100 | 100 | 7.8623 | 7.4284 | 269886.35 | 305624.80 |
| 300 | risk-focused | 100 | 100 | 8.5011 | 7.7711 | 268990.41 | 304607.35 |
| 350 | one-shot | 100 | 56 | 33.8844 | 37.5688 | 965160.45 | 1094486.12 |
| 350 | fixed-rho | 100 | 53 | 34.3734 | 42.3896 | 991240.00 | 1124262.58 |
| 350 | old cf-risk | 100 | 54 | 34.2257 | 42.5540 | 918558.33 | 1041959.94 |
| 350 | risk-focused | 100 | 54 | 34.4550 | 42.9695 | 906721.64 | 1028649.34 |

paired 对比 one-shot：

| size | delta solved | recovered timeout | lost solution | delta mean time | median delta | wins | losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | 0 | 0 | 0 | +0.7852 | +0.4536 | 0 | 72 |
| 350 | -2 | 0 | 2 | +0.5706 | -0.0139 | 0 | 27 |

## 结论

risk-focused labels 改善了标签可解释性，但没有改善最终 selector 泛化。新 selector 在 disjoint 300/350 上弱于旧 cf-risk，更不能作为 400 候选。

主要判断：

- 问题不只是 label 权重或 threshold。
- 当前 graph-level selector features 仍不足以区分 recovered timeout 和 easy slowdown/lost risk。
- 下一步不应继续调 max-selected-fraction，而应改 selector feature 来源：把 graph-level 聚合特征升级为更直接的 per-instance risk evidence，例如 selected top variables 的 event/rho alignment、warmup solved-depth、base-vs-adapter delta distribution、或者用一个小 MLP selector 替代线性 selector。
