# 论文稳定性验证清单

> 只围绕最终 online cache 做验证。代码/结果名统一使用 `online_consistent_boundary400`，论文简称统一写成 `Online-Consistent Selector`。

## 目标

把论文里最关键的三条线收齐：

1. `old_compact` 作为稳定 baseline。
2. `online_consistent_boundary400` 作为主线 selector。
3. `local_reopen_guarded` 作为边界修正 ablation。

## 现有可复用证据

| 项目 | 作用 | 现有文档 / 产物 |
| --- | --- | --- |
| `old_compact` 直接来源 | 主 baseline 数字来源 | `docs/compact_risk_full400_eval.md`，`runs/analysis/compact_risk_full400_summary.csv` |
| `old_compact` 对照解释 | 说明 stable 分支不优于 old compact | `docs/compact_stable_full400_eval.md` |
| `Online-Consistent Selector` 主线 | 最终 online cache 的 full400 结果 | `docs/online_consistent_boundary400_full400_eval.md`，`runs/analysis/online_consistent_boundary400_full400_summary.csv` |
| `Online-Consistent Selector` 决策审计 | 哪些实例开/关 adapter，边界错误在哪里 | `docs/online_consistent_boundary400_decision_audit.md`，`runs/analysis/online_consistent_boundary400_decision_audit_summary.csv` |
| `Online-Consistent Selector` 阈值扫描 | 只在最终 cache 上做阈值检查 | `docs/online_consistent_boundary400_threshold_sweep.md`，`runs/analysis/online_consistent_boundary400_threshold_sweep_best.csv`，`runs/analysis/online_consistent_boundary400_threshold_sweep_compare.csv` |
| 最终稳定性表 | full400 上的 bootstrap / repeated split 稳定性 | `runs/analysis/online_consistent_boundary400_stability.csv`，`summarize_online_consistent_boundary400_stability.py` |
| `local_reopen_guarded` ablation | 边界修正补丁的 full400 结果 | `docs/local_reopen_guarded_full400_eval.md`，`runs/analysis/local_reopen_guarded_full400_summary.csv` |
| `local_reopen_guarded` 触发集合 | 审计打开了哪 4 个样本 | `runs/analysis/local_reopen_guarded_full400_open_set.csv`，`runs/analysis/local_reopen_guarded_full400_guidance_audit.csv` |
| `local_reopen_guarded` 逐实例 / 分桶 / cactus | 论文图表直接来源 | `runs/analysis/local_reopen_guarded_full400_per_instance.csv`，`runs/analysis/local_reopen_guarded_full400_bucket_summary.csv`，`figures/fig_local_reopen_guarded_full400_cactus.pdf` |

## 现阶段结论

- `online_consistent_boundary400` 是论文主线的固定名称，正文可简称为 `Online-Consistent Selector`。
- `old_compact` 的数字应以 `docs/compact_risk_full400_eval.md` 为直接来源。
- `local_reopen_guarded` 只应写成 `local boundary correction ablation`，不是主模型升级。
- full400 上，`local_reopen_guarded` 没有增加 solved count，但压低了 mean time，因此它是边界修正，不是主方法。
- bootstrap 和 repeated split 稳定性表支持同一结论：`online_consistent_boundary400` 与 `local_reopen_guarded` 的 solved count 改善来自相同的 6 个 one-shot 超时恢复，local reopen 的额外贡献主要体现在 mean time。

## 最终稳定性表

下面这张表只基于最终 full400 逐实例结果生成，不复用旧 selector cache，也不重新训练或修改主模型。

统计口径：

- `bootstrap`：按实例配对重采样 2000 次。
- `split`：每次无放回抽 100 个实例，重复 2000 次，用于模拟 split-level robustness。
- `base` 固定为 `one_shot`，其余方法都和 `one_shot` 做成对比较。

| method | solved / 200 | mean_time | delta_mean_time_vs_one_shot | bootstrap_delta_time_ci_low | bootstrap_delta_time_ci_high | bootstrap_time_improve_prob | delta_solved_vs_one_shot | split_time_improve_rate | split_solved_improve_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `one_shot` | 50 | 47.7517s | 0.0000s | 0.0000s | 0.0000s | 0.0000 | 0 | 0.0000 | 0.0000 |
| `old_compact` | 56 | 46.3484s | -1.4033s | -2.7286s | -0.2643s | 0.9950 | 6 | 0.9905 | 0.9850 |
| `online_consistent_boundary400` | 56 | 46.2217s | -1.5300s | -2.8232s | -0.4075s | 0.9975 | 6 | 0.9935 | 0.9870 |
| `local_reopen_guarded` | 56 | 45.4976s | -2.2540s | -3.6504s | -1.0676s | 1.0000 | 6 | 1.0000 | 0.9860 |

读法：

- `online_consistent_boundary400` 是主线 selector，稳定性优于 one-shot，但与 `old_compact` 的 solved count 相同。
- `local_reopen_guarded` 的 solved count 仍为 56/200；它的论文价值是把 mean time 从 `46.2217s` 降到 `45.4976s`。
- `split_solved_improve_rate` 对三种方法都接近 1，说明 6 个 recovered timeout 的优势在 100-instance 子集上稳定出现；但这不应被解释为 local reopen 的额外 solved-count 突破。

## 不再做的事

- 不再扩 selector 复杂度。
- 不再动 polarity / SBE 分支。
- 不再把 boundary ablation 写成新的全局主模型。
- 不再用旧 cache 作为最终结论依据。
