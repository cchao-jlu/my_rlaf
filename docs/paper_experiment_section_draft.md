# 论文实验章节草稿

> 当前草稿只整理实验叙事、表格口径和图表引用，不引入新模型或新实验结论。
> 代码/结果名使用 `online_consistent_boundary400`，论文简称使用 Online-Consistent Selector。
> `local_reopen_guarded` 仅作为 local boundary correction ablation。

## 4 Experiments

本节评估神经反馈引导在 3SAT 求解中的实际收益，重点回答三个问题：

1. 在线一致的保守 selector 是否能在完整 3SAT-400 测试集上稳定改善 one-shot baseline？
2. 这种改善来自哪些实例类型，是否主要依赖少数 timeout recovery？
3. 对保守 selector 的局部边界错误，是否可以用受保护的 local reopen 规则做小范围修补？

实验结论是：Online-Consistent Selector 在 full400 上将 solved count 从 `50/200` 提升到 `56/200`，平均时间从 `47.7517s` 降到 `46.2217s`。它与 old compact baseline 的 solved count 相同，但平均时间略低。进一步的 `local_reopen_guarded` 不增加 solved count，仍为 `56/200`，但把平均时间降到 `45.4976s`。因此，本文把 Online-Consistent Selector 作为主线 selector，把 `local_reopen_guarded` 作为边界修正消融，而不是新的全局主模型。

## 4.1 Experimental Setup

**Benchmark.** 主要实验在 `data/test/3sat/400/*.cnf` 上进行，共 `200` 个 3SAT-400 实例。所有 full400 结论均来自真实 wall-clock 运行，而不是离线估计或旧 selector cache。每个实例的求解时间上限为 `60s`；未在时限内求解的实例记为 `INDETERMINATE`。

**Compared methods.** 我们比较四类方法：

- `one_shot`：one-shot neural guidance baseline；它不使用后续反馈 refinement，但不是完全无神经引导的 solver default。
- `old_compact`：早期 compact risk controller，作为稳定参考 baseline；其直接数字来源是 `docs/compact_risk_full400_eval.md`。
- `online_consistent_boundary400`：最终主线 selector，在论文中简称 Online-Consistent Selector。
- `local_reopen_guarded`：在 Online-Consistent Selector 基础上的局部边界修正 ablation，只允许 `new_closed_old_on` 候选样本触发 reopen。

此外，`pairwise_veto`、`compact_stable`、`polarity / SBE` 只作为负结果或补充诊断，不作为主线方法。

**Metrics.** 我们报告 solved count、mean wall-clock time、median time、per-instance win/loss、difficulty bucket 以及 cactus plot。由于 SAT 求解收益高度集中在少数 hard/timeout 实例上，本文不只看 solved count，也报告平均时间和逐实例变化。

## 4.2 Main Results on Full400

Table 1 给出完整 3SAT-400 测试集上的主结果。

| method | solved / 200 | mean_time | median_time | 论文定位 |
| --- | --- | --- | --- | --- |
| `one_shot` | 50 | 47.7517s | 60.7660s | baseline |
| `old_compact` | 56 | 46.3484s | 60.8806s | stable reference baseline |
| `online_consistent_boundary400` | 56 | 46.2217s | 60.8820s | main selector |
| `local_reopen_guarded` | 56 | 45.4976s | 60.3461s | boundary correction ablation |
| `pairwise_veto` | 52 | 46.8755s | 60.9593s | negative branch |

Online-Consistent Selector 相比 one-shot 多解出 `6` 个实例，并将 mean time 降低 `1.5300s`。与 old compact 相比，它不改变 solved count，但 mean time 从 `46.3484s` 小幅降低到 `46.2217s`。这说明主线收益已经不应再表述为扩大模型能力，而应表述为更一致的在线选择：在保持 recovered timeout 数量的同时减少部分错误 adapter 决策带来的时间损失。

`local_reopen_guarded` 的 full400 结果进一步说明了边界修正的定位。它不改变 solved count，仍为 `56/200`，但 mean time 从 Online-Consistent Selector 的 `46.2217s` 降到 `45.4976s`。因此，local reopen 的贡献是修正少数边界样本上的时间退化，而不是产生新的 solved-count breakthrough。

**Figure 1.** Full400 cactus plot 可以使用 `figures/fig_online_consistent_boundary400_full400_cactus.pdf` 和 `figures/fig_local_reopen_guarded_full400_cactus.pdf`。正文建议主图放 full400 cactus，附录可放 old compact 或 compact stable 对照。

证据来源：

- `docs/online_consistent_boundary400_full400_eval.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/compact_risk_full400_eval.md`
- `runs/analysis/online_consistent_boundary400_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_summary.csv`

## 4.3 Instance-Level Analysis

Full400 的收益不是均匀分布在所有实例上，而是由少数 hard/timeout 实例主导。old compact 相比 one-shot 恢复 `6` 个 timeout，且没有 lost solution；Online-Consistent Selector 保留了同样的 solved count，但调整了若干边界决策。

决策审计显示，Online-Consistent Selector 与 old compact 的差异主要集中在两类样本：

- `new_opened_old_off`：新 selector 打开旧 compact 关闭的 adapter，例如 `3sat_140.cnf`，从 `41.0826s` 降到 `4.3394s`。
- `new_closed_old_on`：新 selector 关闭旧 compact 曾开启的 adapter。这一类既包含正确关闭的 slowdown 样本，例如 `3sat_82.cnf`，也包含被过保守关闭的 hard-speedup 样本，例如 `3sat_46.cnf` 和 `3sat_196.cnf`。

这一观察构成后续 boundary correction 的动机：主 selector 应保持保守，避免在 full400 上打开未知风险分支；少数 `new_closed_old_on` 边界错误则用局部 reopen 规则审计和修补。

建议正文保留一个小表展示代表实例：

| file | class | old_compact | online_consistent | diagnosis |
| --- | --- | --- | --- | --- |
| `3sat_140.cnf` | hard speedup | 41.0826s | 4.3394s | new selector opens useful adapter |
| `3sat_82.cnf` | avoided slowdown | 36.0880s | 21.7471s | new selector closes harmful adapter |
| `3sat_46.cnf` | boundary miss | 1.0575s | 29.8371s | conservative selector closes useful adapter |
| `3sat_196.cnf` | boundary miss | 10.3172s | 26.1159s | conservative selector closes useful adapter |

证据来源：

- `docs/online_consistent_boundary400_decision_audit.md`
- `runs/analysis/online_consistent_boundary400_decision_audit_summary.csv`
- `runs/analysis/online_consistent_boundary400_full400_per_instance.csv`

## 4.4 Stability Validation

稳定性验证只基于最终 full400 逐实例结果生成，不复用旧 selector cache，也不重新训练主模型。我们使用两种统计视角：

- paired bootstrap：按实例配对重采样 `2000` 次。
- repeated split：每次无放回抽 `100` 个实例，重复 `2000` 次。

Table 2 汇总稳定性结果。

| method | solved / 200 | mean_time | delta_mean_time_vs_one_shot | bootstrap 95% CI | bootstrap improve prob | split time improve rate |
| --- | --- | --- | --- | --- | --- | --- |
| `old_compact` | 56 | 46.3484s | -1.4033s | [-2.7286s, -0.2643s] | 0.9950 | 0.9905 |
| `online_consistent_boundary400` | 56 | 46.2217s | -1.5300s | [-2.8232s, -0.4075s] | 0.9975 | 0.9935 |
| `local_reopen_guarded` | 56 | 45.4976s | -2.2540s | [-3.6504s, -1.0676s] | 1.0000 | 1.0000 |

这些结果支持两个结论。第一，Online-Consistent Selector 相比 one-shot 的 mean-time 改善在 bootstrap 和 split 视角下都稳定。第二，`local_reopen_guarded` 的额外价值主要体现在 mean time，而不是 solved count；其 solved count 改善仍来自与主 selector 相同的 `6` 个 one-shot timeout recovery。

证据来源：

- `docs/paper_stability_validation.md`
- `runs/analysis/online_consistent_boundary400_stability.csv`

## 4.5 Local Boundary Correction Ablation

Online-Consistent Selector 采用保守策略，因此会关闭部分旧 compact 曾开启的 adapter 分支。局部 reopen ablation 的目标不是重新设计全局 selector，而是在 candidate guard 保护下，只修补 `new_closed_old_on` 中的少数边界错误。

正式 full400 patch 使用以下规则：

- `local_reopen_candidate >= 1`
- `warmup_c1000_minus_warmup_c750_decisions >= 294`
- `warmup_c2000_rho_event_corr >= 0.0365`

其中 `local_reopen_candidate` 来自 `data/new_closed_old_on_boundary/manifest.csv`。因此，即使 full400 中其他实例满足数值条件，也不会触发 reopen；该模块只在局部候选集内生效。

在 boundary26 ablation 上，local reopen 保持 solved count 为 `5/26`，但 mean time 从 `53.3406s` 降到 `51.6751s`。实际打开 4 个样本，其中 `3sat_46.cnf` 和 `3sat_196.cnf` 是 hard-speedup 正例，`3sat_66.cnf` 是近似零成本 neutral，`3sat_82.cnf` 和 `3sat_93.cnf` 两个 slowdown 负例保持关闭。

在 full400 上，candidate guard 使 local reopen 只打开 4 个样本：

| file | class | online_time | local_reopen_time | delta |
| --- | --- | --- | --- | --- |
| `3sat_188.cnf` | positive / recovered timeout region | 25.6299s | 25.7315s | +0.1015s |
| `3sat_196.cnf` | hard speedup | 26.1159s | 9.6220s | -16.4939s |
| `3sat_46.cnf` | hard speedup | 29.8371s | 0.5256s | -29.3115s |
| `3sat_66.cnf` | neutral timeout | 60.8271s | 60.4345s | -0.3925s |

这个 ablation 的论文表述应为：保守 selector 的局部边界错误可以被受保护的 reopen rule 修补；该修补在 full400 上没有提高 solved count，但降低了平均 wall-clock time。

证据来源：

- `docs/local_boundary_correction_ablation.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`
- `runs/analysis/local_reopen_guarded_full400_guidance_audit.csv`

## 4.6 Ablation Matrix and Negative Results

Table 3 建议作为论文消融矩阵。它只保留有论文价值、且不会扩大主模型叙事的消融。

| ablation | role | result | takeaway |
| --- | --- | --- | --- |
| no guard | boundary subset diagnostic | boundary26 `5/26`; mean time `53.3406s -> 51.6751s` | local correction has signal, but needs guard |
| candidate guard | full400 guarded patch | opens 4 candidates; `56/200`, `45.4976s` | guard keeps patch local and safe |
| no750 diagnostic | feature diagnostic only | opens `3` positive + `1` neutral on trace; neutral differs from formal full400 | signal is not entirely 750-dependent, but not official patch |
| local reopen on/off | final ablation | `56/200`; mean time `46.2217s -> 45.4976s` | final boundary correction claim |

需要特别固定 no750 的口径：正式 `local_reopen_guarded` full400 结果仍然是含 750 特征版本，配置使用 `intervention_conflicts: [500, 750, 1000, 2000]`，规则使用 `warmup_c1000_minus_warmup_c750_decisions`。no750 只是在 `new_closed_old_on` trace 上做的诊断性特征消融，其 neutral 是 `3sat_183.cnf`，不同于正式 full400 open set 中的 `3sat_66.cnf`。除非后续重跑 no750 full400，否则不能把最终 patch 写成 `500/1000/2000 only`。

负结果也应简洁呈现：

- `pairwise_veto`：full400 solved count 只有 `52/200`，不如 Online-Consistent Selector。
- `compact_stable`：用于说明 stable 分支不如 old compact，不作为 old compact 数字的主要证据。
- `polarity / SBE`：在 3SAT-400 上不稳定，存在 lost solution 或收益不能 scale 的问题，因此不进入主线。

证据来源：

- `docs/paper_ablation_matrix.md`
- `docs/compact_stable_full400_eval.md`
- `docs/literal_polarity_sbe_adapter.md`
- `docs/per_instance_win_loss_difficulty.md`

## 4.7 Discussion

这些实验支持一个保守但清晰的结论：神经反馈并不是在所有实例上均匀加速 SAT 求解，而是在少数 hard/timeout 实例上提供大幅收益，同时也可能在 easy/medium 实例上造成 slowdown。因此，主问题不是让 adapter 尽可能多地介入，而是学习一个在线一致的 selector，在 recovery potential 和 slowdown risk 之间做保守取舍。

Online-Consistent Selector 的价值在于，它在 full400 上稳定保留了 `6` 个 timeout recovery，并避免将不稳定分支写成主模型升级。`local_reopen_guarded` 的价值在于暴露并修补主 selector 的局部边界错误：当一个样本属于 `new_closed_old_on`，且 warmup trace 呈现强 decision drift 与正向 event correlation 时，重新打开 adapter 可以恢复 hard-speedup 行为。但由于该规则只改善平均时间、不增加 solved count，它应作为 boundary correction ablation，而不是主方法。

## 4.8 Tables and Figures to Include

建议正文图表优先级如下：

1. Table 1：full400 主结果表，包含 `one_shot`、`old_compact`、Online-Consistent Selector、`local_reopen_guarded`、`pairwise_veto`。
2. Figure 1：full400 cactus plot，主图使用 Online-Consistent Selector 与 local reopen 对照。
3. Table 2：稳定性表，来自 `runs/analysis/online_consistent_boundary400_stability.csv`。
4. Table 3：ablation matrix，来自 `docs/paper_ablation_matrix.md`。
5. Optional Table：边界样本审计表，展示 `3sat_46/196/188/66` 以及 `3sat_82/93`。

暂不建议正文放过多负结果图。`compact_stable`、`polarity / SBE`、pairwise veto 的详细表可以进附录，用来支撑“没有继续堆 selector 复杂度”的选择。
