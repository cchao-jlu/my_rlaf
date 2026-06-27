# Counterfactual Outcome Trace 生成

本次运行从共享 warmup event trace 生成 paired base-vs-adapter labels。
流程是先用同一份 warmup guidance rollout，收集变量级 event evidence；
随后 base 和 adapter 分支都基于这份相同 evidence 进行评估。

重要实现说明：当前 Glucose wrapper 不能序列化并恢复内部 CDCL
trail/clause database。因此这些标签是 same-evidence branch
counterfactuals，不是 in-process CDCL clone continuations。

## 配置

- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt`
- dataset：`data/selector_splits/3sat/selector_train/*/*.cnf`
- warmup budget：`conflicts` / `1000` conflicts
- final cpu limit：`60`

## 标签计数

| class | count |
| --- | --- |
| neutral | 145 |
| negative | 34 |
| warmup_solved | 14 |
| positive | 7 |

## 标签原因计数

| reason | count |
| --- | --- |
| neutral | 145 |
| easy_slowdown | 25 |
| warmup_solved | 14 |
| recovered_timeout | 5 |
| slowdown | 5 |
| lost_solution | 4 |
| hard_speedup | 2 |

## 分支平均时间

| counterfactual_class | base_time | adapter_time | adapter_minus_base_time |
| --- | --- | --- | --- |
| neutral | 25.2335 | 24.7838 | -0.4497 |
| negative | 6.9402 | 13.6485 | 6.7083 |
| warmup_solved | nan | nan | nan |
| positive | 51.7600 | 16.4574 | -35.3026 |

