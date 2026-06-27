# Boundary-Focused Pairwise Trace

该训练帧用于修复 recovery selector 的排序边界：让 hard recovery / hard speedup 排在 easy slowdown / lost solution 前面。
这里不重新跑 solver，而是合并已有 counterfactual trace 和 full400 审计中的边界样本。

注意：`full400_audit` 行用于诊断和排序约束，不应直接当作最终 held-out 评估结果。

## 标签计数

| boundary_source | size | boundary_reason | count |
| --- | --- | --- | --- |
| counterfactual_trace | 300 | easy_slowdown | 30 |
| counterfactual_trace | 300 | hard_speedup | 1 |
| counterfactual_trace | 300 | slowdown | 7 |
| counterfactual_trace | 350 | easy_slowdown | 15 |
| counterfactual_trace | 350 | hard_recovery | 5 |
| counterfactual_trace | 350 | hard_speedup | 2 |
| counterfactual_trace | 350 | lost_solution | 3 |
| counterfactual_trace | 350 | slowdown | 8 |
| counterfactual_trace | 400 | easy_slowdown | 6 |
| counterfactual_trace | 400 | hard_recovery | 8 |
| counterfactual_trace | 400 | hard_speedup | 4 |
| counterfactual_trace | 400 | lost_solution | 5 |
| counterfactual_trace | 400 | slowdown | 3 |
| full400_audit | 400 | easy_slowdown | 22 |
| full400_audit | 400 | hard_recovery | 6 |
| full400_audit | 400 | hard_speedup | 6 |
| full400_audit | 400 | slowdown | 3 |

## 重点样本

| boundary_source | size | file_key | boundary_label | boundary_reason | base_time | adapter_time | boundary_weight | boundary_pair_weight |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| counterfactual_trace | 300 | 3sat_88.cnf | 0.0000 | easy_slowdown | 6.4001 | 6.8917 | 28.0000 | 6.0000 |
| counterfactual_trace | 350 | 3sat_25.cnf | 1.0000 | hard_speedup | 14.4249 | 7.8888 | 8.0000 | 2.0000 |
| counterfactual_trace | 400 | 3sat_140.cnf | 1.0000 | hard_speedup | 39.6426 | 4.0024 | 8.0000 | 2.0000 |
| counterfactual_trace | 400 | 3sat_163.cnf | 1.0000 | hard_recovery | 59.9851 | 28.3986 | 32.0000 | 6.0000 |
| counterfactual_trace | 400 | 3sat_88.cnf | 0.0000 | easy_slowdown | 0.1954 | 30.3304 | 28.0000 | 6.0000 |
| full400_audit | 400 | 3sat_140.cnf | 0.0000 | slowdown | 39.7812 | 41.0826 | 15.0000 | 3.0000 |
| full400_audit | 400 | 3sat_163.cnf | 1.0000 | hard_recovery | 60.8197 | 29.2935 | 48.0000 | 9.0000 |
| full400_audit | 400 | 3sat_25.cnf | 0.0000 | easy_slowdown | 1.6911 | 1.9812 | 42.0000 | 9.0000 |
| full400_audit | 400 | 3sat_82.cnf | 0.0000 | slowdown | 21.4710 | 36.0880 | 15.0000 | 3.0000 |

## 输出文件

- `data/counterfactual_trace/boundary_focused_pairwise_trace.csv`
