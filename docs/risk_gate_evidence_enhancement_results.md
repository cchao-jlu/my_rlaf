# Risk Gate 证据增强实验记录

## 结论

扩充 counterfactual trace 后，瓶颈确实转移到了 risk gate。
直接把大量 warmup count/time/event 特征加入 risk head 会提高 adapter
触发率，但不能稳定识别 400 规模上的 lost/slowdown 风险。

当前更稳的主线是 **compact risk evidence**：

- risk gate 只保留少量和 400 翻车直接相关的强证据；
- recovery detector 继续使用 timeout-recovery 标签；
- selector 仍保持 linear two-stage，不继续堆 MLP 容量。

## 为什么不用全量增强特征

400 规模的风险样本主要不是 timeout，而是 base 本来能解的 easy/medium
实例被 adapter 打慢或打丢：

- `lost_solution`：主要出现在 400 easy/hard base-solved；
- `slowdown/easy_slowdown`：主要出现在 400 easy/medium base-solved；
- `recovered_timeout`：出现在 400 timeout。

因此 risk gate 的任务不是判断“是否困难”，而是判断“adapter 介入是否会破坏
base 已经能解的实例”。高维全量证据会把这个信号稀释。

## Compact Risk Gate 特征

当前默认 risk 特征已切换为：

- `warmup_c500_solved`
- `warmup_c1000_solved`
- `warmup_c2000_base_rho_std`
- `warmup_c2000_base_rho_range`
- `warmup_c2000_event_conf_learnt_log_max`
- `warmup_c2000_minus_warmup_c1000_delta_abs_mean`
- `warmup_c2000_minus_warmup_c1000_delta_mu_abs_mean`
- `warmup_c2000_minus_warmup_c1000_propagations`
- `warmup_c2000_event_entropy_norm`
- `warmup_c2000_event_top10_mass`
- `warmup_c1000_minus_warmup_c500_rho_event_top10_overlap`
- `warmup_c2000_minus_warmup_c1000_event_top05_mass`

这些特征可以在真实推理时部署，因为都来自同一套 multi-point warmup evidence：
500/1000/2000 conflicts 的 solver 统计、event state 和模型图级输出分布。

## Repeated Split 对比

| method | heldout | selected | delta solved | lost | recovered | delta time | keep base | beat time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| old split-stage | 400 | 0.1081 | 0.34 | 0.12 | 0.46 | -0.4377 | 0.90 | 0.68 |
| high-dimensional evidence | 400 | 0.1475 | 0.26 | 0.50 | 0.76 | -0.4792 | 0.74 | 0.64 |
| compact evidence, risk 300/350/400 | 400 | 0.1654 | 0.94 | 0.10 | 1.04 | -0.9108 | 0.98 | 0.86 |
| compact evidence, risk 350/400 | 400 | 0.1393 | 0.80 | 0.08 | 0.88 | -0.7623 | 0.98 | 0.86 |

完整结果文件：

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/two_stage_repeated_split_summary.csv`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_Max12Risk350400/two_stage_repeated_split_summary.csv`

## 当前主线选择

主线建议使用：

- checkpoint：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt`
- 保守对照：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_Max12Risk350400/best.pt`

前者 recovered 更高，400 的平均时间收益更强；后者 selected 更低，400 lost
更低一点。两者都明显优于高维增强证据版本。

## 下一步

先不要继续扩 trace 或堆 MLP。下一步应该做：

1. 用 compact 主线 checkpoint 跑 disjoint 300/350/400 正式评估。
2. 生成 cactus plot 和 per-instance win/loss 报告。
3. 若正式 400 仍有个别 lost，再针对 lost 实例补 risk-focused counterfactual label，
   而不是扩大所有 trace。
