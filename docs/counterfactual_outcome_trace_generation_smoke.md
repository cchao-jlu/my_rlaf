# Counterfactual Outcome Trace 生成 Smoke Test

本次运行从共享 warmup event trace 生成 paired base-vs-adapter labels。流程是先用同一份 warmup guidance rollout，收集变量级 event evidence；随后 base 和 adapter 分支都基于这份相同 evidence 进行评估。

重要实现说明：当前 Glucose wrapper 不能序列化并恢复内部 CDCL trail/clause database。因此这些标签是 same-evidence branch counterfactuals，不是 in-process CDCL clone continuations。

## 配置

- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt`
- dataset：`data/test/3sat/300/*.cnf`
- warmup budget：`conflicts` / `1` conflicts
- final cpu limit：`1`

## 标签计数

| class | count |
| --- | --- |
| negative | 1 |
| neutral | 1 |

## 分支平均时间

| counterfactual_class | base_time | adapter_time | adapter_minus_base_time |
| --- | --- | --- | --- |
| negative | 0.0995 | 0.1681 | 0.0686 |
| neutral | 0.9940 | 1.0005 | 0.0064 |
