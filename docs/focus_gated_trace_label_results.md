# Focus-Gated Trace Label 结果

本文档记录 selector feature 实验之后的第一轮 rollout/trace-label 修改。前一轮实验显示，micro selector features 没有改善 held-out 稳定性。

## 修改内容

trace pseudo-label 现在支持 focus gate：

- 用 `low_lbd_learnt_lits + conflict_lits` 计算 focus score。
- 通过 `focus_topk_ratio` 计算 top-k mass。
- 同时缩放 target residual 和 confidence。
- 除非 `focus_gate_enabled=true`，否则默认行为保持不变。

配置：

- `configs/config_train_trace_distill_focus_gated.yaml`

checkpoint：

- `runs/GNN_Glucose_3SAT_TraceAdapter_FocusGatedSmallResidual/best.pt`

## 3SAT-300 评估

所有行都使用优化后的 weighted Glucose binary：

```text
bb9ff6f661aeaa91e0274e09d0977793ff3633846e05617093f9f6e1e2689865
```

| method | solved | mean time | median | mean CPU | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|
| one-shot | 200/200 | 7.4380 | 6.1297 | 6.9007 | 256867.99 | 290940.28 |
| fixed-rho | 200/200 | 7.1805 | 5.4250 | 6.5972 | 249771.64 | 282893.78 |
| focus-gated trace label | 200/200 | 7.9280 | 6.2944 | 7.3275 | 287040.16 | 325223.57 |

CSV：

- `runs/GNN_Glucose_3SAT_TraceAdapter_FocusGatedSmallResidual/eval_focus_gated_300_optimized_events_gated.csv`

## 结论

focus-gated trace label 是负结果。理论上它降低了 noisy-label confidence，但训练出的 adapter 在 3SAT-300 上比 one-shot 和 fixed-rho 都差。因此它不应作为主方法候选继续评估 350/400。

这说明瓶颈不只是 pseudo-label scaling。当前单次 500-conflict warmup trace 可能没有足够稳定的证据来区分 timeout recovery 和 lost-solution risk。下一步更有用的改动应是 rollout evidence generation，例如 multiple short rollouts 或 base-vs-adapter contrastive trace label。
