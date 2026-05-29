# 论文实验章节草稿

> 当前草稿只整理实验叙事、表格口径和图表引用，不引入新模型或新实验结论。
> 代码/结果名使用 `online_consistent_boundary400`，论文简称使用 Online-Consistent Selector。
> `local_reopen_guarded` 仅作为 local boundary correction ablation。

## 4 Experiments

本节评估神经反馈引导在 3SAT 求解中的实际收益，重点回答三个问题：

1. 在线一致的保守 selector 是否能在完整 3SAT-400 测试集上稳定改善 one-shot baseline？
2. 这种改善来自哪些实例类型，是否主要依赖少数 timeout recovery？
3. 对保守 selector 的局部边界错误，是否可以用受保护的 local reopen 规则做小范围修补？

实验结论以 full400 solver-seed robustness 为主：Online-Consistent Selector 在 seeds 1/2/3 上稳定将 solved count 从 One-shot 的 `48/200` 提升到 `53/200`，平均时间从 `47.6647s` 降到 `46.3236s`。Old Compact 仍是强 baseline，达到 `54/200`、mean `46.2777s`。进一步的 `local_reopen_guarded` 匹配 Old Compact 的 `54/200` solved count，并把平均时间降到 `45.9139s`。因此，本文把 Online-Consistent Selector 作为主线 selector，把 `local_reopen_guarded` 作为 guarded boundary correction ablation，而不是新的无约束全局主模型。旧 `50/200 -> 56/200 -> 56/200` 结果只作为 historical single-run context，不再作为核心主表。

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
| `one_shot` | 48.0 | 47.6647s | 60.2889s | baseline |
| `online_consistent_boundary400` | 53.0 | 46.3236s | 60.3665s | main selector |
| `old_compact` | 54.0 | 46.2777s | 60.3725s | stable reference baseline |
| `local_reopen_guarded` | 54.0 | 45.9139s | 60.3689s | boundary correction ablation |

Online-Consistent Selector 相比 one-shot 稳定多解出 `5` 个实例，并将 mean time 降低约 `1.3411s`。与 old compact 相比，它少解 `1` 个边界实例，因此不能写成单独超过 Old Compact；更准确的结论是 Online-Consistent Selector 稳定恢复了 One-shot 的主要 timeout loss，而 Old Compact 仍是强 matched baseline。

`local_reopen_guarded` 的 full400 结果进一步说明了边界修正的定位。它将 Online-Consistent Selector 的 `53/200` 提升到 `54/200`，匹配 Old Compact solved count，并将 mean time 从 `46.3236s` 降到 `45.9139s`。由于它依赖 candidate manifest guard，论文中仍应写作 guarded boundary correction ablation，而不是 unrestricted main model。

**Figure 1.** Full400 cactus plot 使用 paper-ready 版本 `figures/fig_full400_cactus_paper.pdf` / `figures/fig_full400_cactus_paper.svg`。正文建议主图放 full400 cactus，附录可放 old compact 或 compact stable 对照。

证据来源：

- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_seed_robustness/method_summary.csv`
- `runs/analysis/full400_seed_robustness/seed_summary.csv`
- `runs/analysis/full400_seed_robustness/per_instance_summary.csv`

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

稳定性验证只基于最终 full400 逐实例结果生成，不复用旧 selector cache，也不重新训练主模型。当前论文主口径使用两种运行级稳定性视角：

- full400 same-seed repeats：四个方法各跑 `3` 次，保持默认 solver seed。
- full400 solver-seed robustness：四个方法在 Glucose seeds `1/2/3` 上各跑一次。

Table 2 汇总稳定性结果。

| method | same-seed repeat solved | seed robustness solved | seed solved std | seed mean_time |
| --- | --- | --- | --- | --- |
| `one_shot` | 48.0 | 48.0 | 0.0 | 47.6647s |
| `online_consistent_boundary400` | 53.0 | 53.0 | 0.0 | 46.3236s |
| `old_compact` | 54.0 | 54.0 | 0.0 | 46.2777s |
| `local_reopen_guarded` | 54.0 | 54.0 | 0.0 | 45.9139s |

这些结果支持两个结论。第一，Online-Consistent Selector 相比 one-shot 的 solved-count 改善在 full400 repeats 和 seeds 1/2/3 下稳定。第二，`local_reopen_guarded` 匹配 Old Compact solved count，并给出最低 mean time；但由于它依赖 candidate manifest guard，仍应作为 boundary correction ablation。

我们另外做了 full400 same-seed repeated runtime 和 full400 solver-seed robustness。same-seed full400 repeats 显示 One-shot `48/200`、Online-Consistent Selector `53/200`、Old Compact `54/200`、+ Local Boundary Correction `54/200`，三个 repeats 的 solved count 均不变。solver-seed robustness 使用 seeds 1/2/3，四个方法的 solved std 也均为 `0.0`。这支持主表从旧 frozen single-run 切换到 full400 repeated / seed robustness 口径。

同时，我们保留了一个更小的 same-seed key-claim audit，只覆盖论文中最容易被质疑的关键样本。该 audit 固定 `9` 个 unique instances，每个 pair 跑 `3` 次：`6` 个 recovered timeout 用 One-shot vs Online-Consistent Selector 比较，`4` 个 Local Boundary Correction open-set 用 Online-Consistent Selector vs + Local Boundary Correction 比较。结果表明：same-seed repeated runtime audit supports all six recovered timeouts. `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups. `3sat_188.cnf` is boundary-sensitive. `3sat_66.cnf` remains neutral timeout evidence. 这部分应放在 appendix 或稳定性补充段落中，并明确它是 same-seed runtime audit，不是跨机器复现。

Appendix 300/350/400 generalization and baseline robustness results show the final Online-Consistent Selector does not collapse on smaller held-out sizes: it preserves solved count on 300, solves one additional instance over One-shot on 350, and reduces mean time on both sizes. The broader appendix table also includes Glucose default and matched Old Compact: Glucose default is `197/200` on 300, `73/200` on 350, and `13/200` on 400; matched Old Compact is `200/200` on 300 and `103/200` on 350. Local Boundary Correction is still not applied to 300/350.

证据来源：

- `docs/paper_stability_validation.md`
- `runs/analysis/online_consistent_boundary400_stability.csv`
- `docs/full400_repeated_runtime.md`
- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_repeated_runtime/summary.csv`
- `runs/analysis/full400_seed_robustness/method_summary.csv`
- `docs/repeated_runtime_audit.md`
- `runs/analysis/repeated_runtime_audit.csv`
- `docs/paper_appendix_300350_eval.md`
- `runs/analysis/appendix_300350/summary.csv`
- `docs/paper_generalization_baseline_table.md`
- `runs/analysis/generalization_baseline/paper_table.csv`

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
| candidate guard | full400 guarded patch | opens 4 candidates; `54/200`, `45.9139s` in 3-seed robustness | guard keeps correction local and safe |
| no750 diagnostic | feature diagnostic only | opens `3` positive + `1` neutral on trace; neutral differs from formal full400 | signal is not entirely 750-dependent, but not official patch |
| local reopen on/off | final ablation | `53.0 -> 54.0` solved; mean time `46.3236s -> 45.9139s` in 3-seed robustness | final boundary correction claim |

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

Online-Consistent Selector 的价值在于，它在 full400 solver-seed robustness 下稳定恢复 One-shot 的主要 timeout loss，并避免将不稳定分支写成主模型升级。`local_reopen_guarded` 的价值在于暴露并修补主 selector 的局部边界错误：当一个样本属于 `new_closed_old_on`，且 warmup trace 呈现强 decision drift 与正向 event correlation 时，重新打开 adapter 可以恢复 hard-speedup 行为。在 repeated / seed robustness 口径下，它匹配 Old Compact solved count 并降低 mean time；但由于该规则依赖 candidate manifest guard，它仍应作为 boundary correction ablation，而不是 unrestricted main method。

## 4.8 Tables and Figures to Include

建议正文图表优先级如下：

1. Table 1：full400 3-seed robustness 主结果表，包含 `one_shot`、Online-Consistent Selector、`old_compact`、`local_reopen_guarded`。
2. Figure 1：full400 cactus plot，主图使用 Online-Consistent Selector 与 local reopen 对照。
3. Table 2：稳定性表，来自 `runs/analysis/online_consistent_boundary400_stability.csv`。
4. Table 3：ablation matrix，来自 `docs/paper_ablation_matrix.md`。
5. Optional Table：边界样本审计表，展示 `3sat_46/196/188/66` 以及 `3sat_82/93`。
6. Appendix Table：300/350/400 generalization / baseline robustness，包含 Glucose default、One-shot、Online-Consistent Selector、Old Compact；Local Boundary Correction 只在 400 出现。

暂不建议正文放过多负结果图。`compact_stable`、`polarity / SBE`、pairwise veto 的详细表可以进附录，用来支撑“没有继续堆 selector 复杂度”的选择。
