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
- warmup budget：`conflicts` / `[500, 1000, 2000]` conflicts
- intervention point：`2000` conflicts
- final cpu limit：`60`

## 多点 evidence

如果配置中包含多个 `intervention_conflicts`，脚本会用同一个初始
GNN guidance 分别运行多个 conflict 上限，并把各点 graph-level
event features 及相邻点 drift 写入 outcome CSV/PT payload。
当前 Glucose wrapper 还不能导出并恢复 CDCL 快照，所以这些点是
same-initial-guidance cumulative probes，不是单个 CDCL 进程的连续暂停恢复。

## 标签计数

| class | count |
| --- | --- |
| neutral | 123 |
| negative | 49 |
| warmup_solved | 20 |
| positive | 8 |

## 标签原因计数

| reason | count |
| --- | --- |
| neutral | 123 |
| easy_slowdown | 30 |
| warmup_solved | 20 |
| slowdown | 16 |
| recovered_timeout | 5 |
| hard_speedup | 3 |
| lost_solution | 3 |

## 分支平均时间

| counterfactual_class | base_time | adapter_time | adapter_minus_base_time |
| --- | --- | --- | --- |
| neutral | 26.0550 | 25.9109 | -0.1442 |
| negative | 11.2183 | 16.8522 | 5.6338 |
| warmup_solved | nan | nan | nan |
| positive | 49.0461 | 16.7261 | -32.3199 |

