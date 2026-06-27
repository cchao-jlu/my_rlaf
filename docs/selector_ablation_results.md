# Slow-Fast Selector 消融

本文档记录较早的 test-trained slow-fast selector 消融结果。它现在只作为历史上下文保留：当前主线 selector 候选已经切换为 `docs/current_mainline_counterfactual_risk_selector.md` 中的 ultra-conservative counterfactual risk controller。

## 历史配置

运行命令：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_slow_fast_selector \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  save_file=eval_trace_adapter_300_round1_conf500.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_slow_fast_selector \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  save_file=eval_trace_adapter_350_round1_conf500.csv
```

该配置固定为：

- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorRho300350/best.pt`
- feedback state：增强版变量级 event state
- rollout budget：500 conflicts
- refinement rounds：1
- state momentum：0.5
- adapter residual：gated，clip 到 0.5，scale 为 0.25
- selector feature：`base_rho_mean`，在 3SAT-300 和 3SAT-350 trace 上训练

## 在线求解结果

由下面命令生成：

```bash
python summarize_selector_ablation.py
```

| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-shot baseline | 300 | 200 | 200 | 7.5060 | 6.3091 | 256867.99 | 290940.28 |
| always adapter | 300 | 200 | 200 | 7.3572 | 5.4163 | 254877.58 | 288553.17 |
| fixed rho gate | 300 | 200 | 200 | 7.1407 | 5.4279 | 249771.64 | 282893.78 |
| learned selector | 300 | 200 | 200 | 7.2308 | 5.6390 | 249487.07 | 282574.33 |
| one-shot baseline | 350 | 200 | 108 | 34.5932 | 47.5073 | 977654.07 | 1108964.57 |
| always adapter | 350 | 200 | 103 | 35.5161 | 54.2078 | 1020833.04 | 1157525.74 |
| fixed rho gate | 350 | 200 | 106 | 34.4200 | 46.4910 | 984417.39 | 1116791.11 |
| learned selector | 350 | 200 | 110 | 34.0612 | 38.7670 | 973729.46 | 1104616.65 |

## 离线 Selector Policy 消融

该消融使用同一组实例级 baseline 和 always-adapter runtime 记录，然后比较 learned selector 与 inverse policy。

| size | selected fraction | base | always adapter | learned selector | inverse selector |
|---:|---:|---:|---:|---:|---:|
| 300 | 0.3100 | 7.5060 | 7.3572 | 7.2539 | 7.6093 |
| 350 | 0.3000 | 34.5932 | 35.5161 | 34.0512 | 36.0582 |
| all | 0.3050 | 21.0496 | 21.4367 | 20.6525 | 21.8337 |

## 结论

这个 learned selector 不再作为当前主线。它在 3SAT-300 平均时间上略弱于 fixed rho gate，但在这组旧实验里取得了最好的 3SAT-350 平均时间、中位时间、解出数、conflicts 和 decisions。后续的干净划分实验和 counterfactual-label 实验证明，更稳妥的主线是 ultra-conservative risk-controller selector，其首要目标是避免丢失 base-solved 实例。

inverse selector 仍然是有价值的消融：它在线下比 one-shot 和 always-adapter 都差，说明原始 selector signal 不是简单的随机 gating noise。
