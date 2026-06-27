# 当前主线：Ultra-Conservative Counterfactual Risk Selector

EchoSAT 当前采用 ultra-conservative counterfactual risk selector 作为主线 selector 候选。

这个 selector 是安全优先的。它不是为了尽可能多地打开 adapter，而是为了尽量保住 base-solved 实例，只在反事实结果模型判断风险较低时才允许 slow-fast adapter 介入。

## Checkpoint 路径

```text
runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350_UltraConservative/best.pt
```

这个 checkpoint 包含 trace-pretrained gated residual adapter，并在模型配置中保存了线性风险 selector：

- 特征：`base_rho_mean`、`delta_mu_abs_mean`、`event_gate_mean`、`event_top10_mass`、`rho_event_corr`
- selector threshold：`0.13779568672180176`
- 训练策略：`negative_weight_scale=4.0`，`max_selected_fraction=0.10`

## 评估配置

```text
configs/config_eval_guided_solver_counterfactual_risk_selector.yaml
```

运行命令：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  save_file=eval_counterfactual_risk_selector_300.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  save_file=eval_counterfactual_risk_selector_350.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  dataset.eval_path='data/test/3sat/400/*.cnf' \
  save_file=eval_counterfactual_risk_selector_400.csv
```

## 当前证据

在 small 300/350 counterfactual trace set 上做 repeated split：

| selected fraction | delta solved vs base | lost solution | recovered timeout | delta time vs base | keeps base solved rate |
| --- | --- | --- | --- | --- | --- |
| 0.0477 | -0.0200 | 0.0200 | 0.0000 | -0.0312 | 0.9800 |

全数据拟合策略：

| selected fraction | base solved | adapter solved | selector solved | lost solution | recovered timeout | delta time vs base |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0851 | 73 | 71 | 73 | 0 | 0 | -0.1261 |

干净 disjoint heldout split 上的 300/350 结果记录在：

```text
docs/counterfactual_risk_selector_disjoint_300350.md
```

核心结果：

| size | one-shot solved / mean | fixed-rho solved / mean | cf-risk solved / mean |
| --- | --- | --- | --- |
| 300 | 100 / 7.7159 | 100 / 7.5556 | 100 / 7.8623 |
| 350 | 56 / 33.8844 | 53 / 34.3734 | 54 / 34.2257 |

## 解读

这还不是一个强 timeout-recovery 结果。small trace repeated split 显示它几乎不牺牲 base-solved 实例，并且有轻微平均时间收益；但 disjoint 300/350 评估没有复现这个收益。300 上它比 one-shot/fixed-rho 都慢，350 上相对 one-shot 少解 2 个且没有 recovered timeout。因此当前不继续跑 400。

Fixed-rho gate 继续作为受控基线。ultra-conservative selector 仍可作为 risk-controller 方向保留，但不能作为最终主结果。下一步应优先改 counterfactual label/rollout evidence，再重新评估 selector。
