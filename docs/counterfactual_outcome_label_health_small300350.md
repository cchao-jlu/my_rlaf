# Counterfactual Outcome Label Health：Small 300/350

这次实验检查 same-evidence counterfactual labels 是否比早期通过拼接 one-shot/fixed-rho CSV 得到的标签更健康。

实验协议：

- dataset：`data/test/3sat/300/*.cnf` 排序后的前 50 个公式
- dataset：`data/test/3sat/350/*.cnf` 排序后的前 50 个公式
- warmup：500 conflicts，开启 event collection
- final branch budget：60 秒
- branches：cached base guidance vs 基于同一份 warmup evidence 的 event-adapter guidance

输出：

- `data/counterfactual_trace/small300_counterfactual_outcomes.csv`
- `data/counterfactual_trace/small350_counterfactual_outcomes.csv`
- `data/counterfactual_trace/small300_counterfactual_outcome_traces.pt`
- `data/counterfactual_trace/small350_counterfactual_outcome_traces.pt`
- `docs/counterfactual_outcome_trace_small300.md`
- `docs/counterfactual_outcome_trace_small350.md`

## 新 Counterfactual Labels

| size | n | warmup solved | reached intervention | positive | negative | neutral | labelled/reached | positive/reached | negative/reached |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | 50 | 2 | 48 | 6 | 9 | 33 | 31.25% | 12.50% | 18.75% |
| 350 | 50 | 4 | 46 | 5 | 12 | 29 | 36.96% | 10.87% | 26.09% |

## 分支结果

| size | base solved | adapter solved | adapter - base solved | base mean time | adapter mean time | adapter - base mean time |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | 48 | 48 | 0 | 6.2244 | 6.2824 | +0.0580 |
| 350 | 25 | 23 | -2 | 36.7499 | 36.8606 | +0.1107 |

## 旧 Joined-CSV Contrastive Labels

| size | n | positive | negative | neutral | labelled/all | positive/all | negative/all |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | 200 | 5 | 35 | 160 | 20.00% | 2.50% | 17.50% |
| 350 | 200 | 13 | 17 | 170 | 15.00% | 6.50% | 8.50% |

## 解读

新的 same-evidence counterfactual 协议给出了更密集的训练信号：300 上 labelled examples 从 `20.00%` 增加到 `31.25%`，350 上从 `15.00%` 增加到 `36.96%`。positive examples 也不再那么稀疏，尤其是 300。

这比旧 joined-CSV labels 更适合训练 risk-controller selector，但还不能说明 adapter 应该被广泛启用。在这个小规模 350 slice 上，adapter branch 相比 base branch 少解出 2 个实例，而且 negative labels 仍多于 positive labels。因此下一步训练目标应该是 selective activation：尽量恢复 positive cases，同时避开 negative cases。

这次小实验不是最终 evaluation split。它使用每个规模排序后的前 50 个实例，不是随机划分，也不是 difficulty-matched split。
