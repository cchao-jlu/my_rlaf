# Counterfactual Risk Selector Disjoint 300/350 评估

本文档记录当前 ultra-conservative counterfactual risk selector 在 difficulty-matched disjoint heldout split 上的评估结果。

## 协议

使用 heldout split：

- `data/selector_splits/3sat/heldout_test/300/*.cnf`：100 个实例
- `data/selector_splits/3sat/heldout_test/350/*.cnf`：100 个实例

运行命令：

```bash
python3 evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/300/*.cnf' \
  save_file=eval_counterfactual_risk_selector_heldout_300.csv

python3 evaluate_guided_solver.py --config-name config_eval_guided_solver_counterfactual_risk_selector \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/350/*.cnf' \
  save_file=eval_counterfactual_risk_selector_heldout_350.csv
```

输出文件：

- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350_UltraConservative/eval_counterfactual_risk_selector_heldout_300.csv`
- `runs/GNN_Glucose_3SAT_CounterfactualRiskSelectorSmall300350_UltraConservative/eval_counterfactual_risk_selector_heldout_350.csv`

对照结果来自同一 heldout split 上过滤后的 clean CSV：

- one-shot：`runs/GNN_Glucose_3SAT_V1/eval_oneshot_300_optimized_events_gated.csv`
- one-shot：`runs/GNN_Glucose_3SAT_V1/eval_oneshot_350_optimized_events_gated.csv`
- fixed-rho：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/eval_trace_adapter_rho_gate_300_optimized_events_gated.csv`
- fixed-rho：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/eval_trace_adapter_rho_gate_350_optimized_events_gated.csv`

## 汇总结果

| size | method | n | solved | mean time | median time | mean CPU | mean GPU | mean conflicts | mean decisions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | one-shot | 100 | 100 | 7.7159 | 7.2823 | 7.1803 | 0.5356 | 268855.43 | 304454.56 |
| 300 | fixed-rho | 100 | 100 | 7.5556 | 6.8847 | 6.9784 | 0.5648 | 264998.83 | 300020.91 |
| 300 | cf-risk selector | 100 | 100 | 7.8623 | 7.4284 | 7.3050 | 0.5458 | 269886.35 | 305624.80 |
| 350 | one-shot | 100 | 56 | 33.8844 | 37.5688 | 33.1834 | 0.7010 | 965160.45 | 1094486.12 |
| 350 | fixed-rho | 100 | 53 | 34.3734 | 42.3896 | 33.6926 | 0.6677 | 991240.00 | 1124262.58 |
| 350 | cf-risk selector | 100 | 54 | 34.2257 | 42.5540 | 33.5758 | 0.6377 | 918558.33 | 1041959.94 |

## Paired Win/Loss

| size | comparison | delta solved | recovered timeout | lost solution | delta mean time | median delta | wins | losses |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | cf-risk vs one-shot | 0 | 0 | 0 | +0.1464 | +0.0512 | 14 | 39 |
| 300 | cf-risk vs fixed-rho | 0 | 0 | 0 | +0.3066 | +0.0241 | 17 | 34 |
| 350 | cf-risk vs one-shot | -2 | 0 | 2 | +0.3414 | -0.0392 | 3 | 21 |
| 350 | cf-risk vs fixed-rho | +1 | 2 | 1 | -0.1476 | -0.0291 | 13 | 20 |

## 决策

不继续跑 400。

原因：

- 300 上 cf-risk selector 没有丢解，但比 one-shot 和 fixed-rho 都慢。
- 350 上 cf-risk selector 比 fixed-rho 解出数多 1、平均时间略好，但相对 one-shot 少解 2 个，没有 recovered timeout，仍有 2 个 lost solution。
- 当前结果没有证明 ultra-conservative selector 在干净 disjoint split 上具备稳定收益。400 更受 timeout 长尾支配，如果 350 已经没有恢复 one-shot timeout，直接跑 400 的投入产出比不高。

结论：当前 selector 可以继续作为 safety/risk-control 方向保留，但不能作为最终主结果。下一步应优先改 counterfactual label/rollout evidence，而不是直接扩大到 400。
