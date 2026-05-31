# Paper Readiness Gap Audit

> 目标：判断当前论文骨架离顶会投稿还差哪些硬证据。
> 本文档是投稿前差距审计，不提出新模型线，不扩 selector 复杂度。

## Executive Summary

当前论文已经有完整素材包，但不建议按“性能提升论文”投稿。主线叙事、方法草稿、实验章节、表图包、related work、Glucose default reference、full400 solver-seed robustness、300/350/400 generalization baseline table、CaDiCaL baseline repeats、repeated-CaDiCaL overlap audit 和 March baseline audit 都已经形成闭环；主要风险已经从“故事能不能写”转为“证据已经反证 strong-CDCL 性能 claim”：

- 结果是否只在 3SAT-400 上成立？这一项已有 300/350/400 generalization / baseline robustness table，但主 claim 仍限定在 full400。
- 相比强 CDCL 是否仍有意义？Glucose default 不是瓶颈；CaDiCaL repeat audit 已经削弱 portfolio solved-count delta；March strict-60 baseline `184/200` 进一步消除了当前 neural / Local 对 strong SAT baseline 的 solved-count complement。
- single-run wall-clock 是否受运行噪声影响？这一项已有 full400 same-seed repeats 和 solver-seed robustness，剩余问题是是否需要更多机器/环境复现。
- 复现 Table 1 / Figure 1 是否有清晰入口？这一项已有 `docs/paper_reproducibility.md` 和 `docs/paper_artifact_manifest.md`。

建议结论：

| Category | Items |
| --- | --- |
| Resolved / reproducibility package | paper tables, figures, appendix CSVs, scripts, configs, and manifest are tracked |
| Resolved / robustness evidence | full400 same-seed repeats and full400 seeds 1/2/3 robustness |
| Resolved / appendix evidence | 300/350/400 generalization and baseline robustness table |
| Resolved / placement pending | Glucose default / solver default 300/350/400 baseline |
| Must reposition before submission | March strict-60 baseline rules out current strong-CDCL performance/complementarity claim |
| Should fix if time allows | 多机器/环境复现；更尖锐的新颖性对照 |
| Can defer to appendix / rebuttal | 负结果细节；no750 诊断；boundary audit 表；旧 clean stability 结果 |

## 1. Experimental Strength

### Current Evidence

- 主结果现在应使用 `data/test/3sat/400/*.cnf` 的 full400 solver-seed robustness 表，而不是旧 frozen single-run 表。
- One-shot：`48.0/200`, mean `47.6647s`，seeds 1/2/3 solved std `0.0`。
- Online-Consistent Selector：`53.0/200`, mean `46.3236s`，seeds 1/2/3 solved std `0.0`。
- Old Compact：`54.0/200`, mean `46.2777s`，仍是强 matched baseline。
- Local Boundary Correction：`54.0/200`, mean `45.9139s`，只作为 guarded boundary correction ablation。
- 已补 300/350/400 generalization / baseline robustness table：300/350 只作为 appendix single-run check，full400 neural rows 使用 3-seed robustness；不迁移 Local Boundary Correction 到 300/350。
- 300 appendix：One-shot `200/200`, mean `15.3115s`；Online-Consistent Selector `200/200`, mean `7.2723s`。
- 350 appendix：One-shot `108/200`, mean `43.7406s`；Online-Consistent Selector `109/200`, mean `33.8154s`。
- 300/350 matched Old Compact：300 `200/200`, mean `8.9073s`；350 `103/200`, mean `34.9183s`。
- Glucose default：300 `197/200`, mean `20.2219s`；350 `73/200`, mean `47.4535s`；400 `13/200`, mean `57.6145s`。

### Status

当前 hard evidence 已经能回答一个较弱的 appendix 问题：

> final Online-Consistent Selector 在 300/350 held-out sizes 上是否明显崩掉？

答案是否定的：300/350 appendix run 显示它没有 collapse，并在两个 size 上降低 mean time。不过这仍不是跨规模主 claim；正文主结论仍应限定为 3SAT-400 full400，300/350 只作为 appendix generality evidence。

### Recommendation

Resolved / appendix evidence:

- 已补 `docs/paper_appendix_300350_eval.md`。
- 已补 `docs/paper_generalization_baseline_table.md`。
- 已纳入 `runs/analysis/appendix_300350/summary.csv` 和四个 raw CSV。
- 已纳入 `runs/analysis/generalization_baseline/paper_table.csv`、`runs/analysis/generalization_baseline/summary.csv`、Glucose 300/350 raw CSV 和 matched Old Compact 300/350 raw CSV。
- 论文中只写作 appendix generality / baseline robustness check，不写成跨规模主 claim。
- 明确 300/350 不包含 Local Boundary Correction；该模块仍是 400-boundary ablation。

Must fix before submission:

- 在正文中明确主 claim 限定为 3SAT-400 full400，避免暗示跨规模泛化已经证明。

Should fix if time allows:

- 如果需要更强的跨规模主张，再单独设计 scale-generalization 实验；不要把当前 appendix check 扩写成主 claim。

Can defer to appendix / rebuttal:

- 旧 clean 300/350/400 表可以作为负结果或方法演化背景，但不要放进主结果支撑。

## 2. Baseline Sufficiency

### Current Evidence

当前 neural-workflow 主表包含：

- One-shot neural guidance baseline.
- Old Compact reference.
- Online-Consistent Selector.
- + Local Boundary Correction.
- Glucose default reference in appendix / baseline robustness table.

README 中有 `evaluate_base_solver.py` 的原生 solver 评估入口；已补 paper-ready 的 Glucose default / solver default 300/350/400 对照：

- source: `docs/glucose_default_full400_eval.md`
- generalized source: `docs/paper_generalization_baseline_table.md`
- CSV: `runs/glucose/solver_stats_300_cpu60.csv`
- CSV: `runs/glucose/solver_stats_350_cpu60.csv`
- CSV: `runs/glucose/solver_stats_full400_cpu60.csv`
- summary: `runs/analysis/glucose_default_full400_summary.csv`
- generalization summary: `runs/analysis/generalization_baseline/paper_table.csv`
- results: 300 `197/200`, mean `20.2219s`; 350 `73/200`, mean `47.4535s`; 400 `13/200`, mean `57.6145s`

另外，已经补了更强的 CaDiCaL full400 audit：

- CaDiCaL 60s repeats: `75, 80, 80` solved.
- End-to-end `Local 5s -> CaDiCaL 55s` portfolio repeats: `79, 80, 80`.
- Matched repeated-CaDiCaL deltas: `+4, 0, 0`.
- Full repeated-baseline strict Local/CaDiCaL complement: `3` instances
  (`3sat_140.cnf`, `3sat_147.cnf`, `3sat_188.cnf`).
- Online/CaDiCaL strict complement: `2` instances
  (`3sat_140.cnf`, `3sat_147.cnf`).
- Local-only strict boundary contribution beyond Online and repeated CaDiCaL:
  `1` instance (`3sat_188.cnf`).
- Online recovers `5` one-shot timeouts, but CaDiCaL solves all `5/5` in all
  three repeats.
- Local Correction open set: CaDiCaL solves `3sat_46.cnf` and
  `3sat_196.cnf` in all repeats; only `3sat_188.cnf` is a Local-solved
  CaDiCaL-strict-unsolved boundary point.

March audit adds a stronger baseline from an existing solver family:

- March external-65 raw run solves `192/200`.
- Strict 60s count, treating wall time greater than 60s as timeout, is
  `184/200`, mean strict-capped time `26.702s`.
- March solves all three Local-solved / CaDiCaL-unsolved-all instances:
  `3sat_140.cnf`, `3sat_147.cnf`, and `3sat_188.cnf`.
- Local solved / March unsolved is `0`; March solved / Local unsolved is `130`.

Sources:

```text
docs/cadical_repeat_stability.md
docs/cadical_repeated_neural_overlap_audit.md
docs/march_full400_baseline_audit.md
runs/analysis/cadical_repeat_stability/portfolio_vs_cadical_repeats.csv
runs/analysis/cadical_repeated_neural_overlap/summary.csv
runs/analysis/cadical_repeated_neural_overlap/local_only_solved_cadical_unsolved_all.csv
runs/analysis/march_full400_cpu60/strict60_summary.csv
runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv
```

### Status

顶会审稿人很可能问：

> 你提升的是相对 neural one-shot baseline，还是相对强 CDCL solver？

当前实验可以回答两个不同层次的问题：

- 相对 RLAF-style one-shot neural guidance baseline，Online-Consistent Selector 是稳定改进。
- 相对 Glucose default，neural guidance 明显更强。
- 相对 CaDiCaL，不能声称 robust dominance。证据只支持 cautious complementarity / boundary-sensitive risk-control framing。
- 相对 March，当前 neural workflow 和 Local Boundary Correction 没有 solved-count complementarity；March strict60 `184/200` 大幅强于 Local5 -> CaDiCaL55 portfolio `79-80/200`。

因此 baseline sufficiency 的状态不是简单的 placement pending。Glucose default 已 resolved；CaDiCaL baseline 已经揭示 claim 风险；March baseline 进一步说明当前结果不能支撑顶会性能论文。必须在投稿前完成定位重写。

### Recommendation

Resolved:

- 已补 solver default / unguided Glucose 300/350/400 baseline。
- 已补 CaDiCaL 60s full400 baseline repeats 和 repeated-CaDiCaL overlap audit。
- 已补 March full400 strict-60 baseline audit。
- 在实验设置中明确 One-shot 是 neural baseline，不是 solver default。

Must fix before submission:

- 主 claim 必须从“性能上超过强 CDCL”降级。March baseline 之后，
  “boundary-sensitive neural/CDCL complementarity” 也只能限定为相对
  CaDiCaL/Glucose workflow 的诊断，不再是 strong-SAT-baseline claim。
- 更合适的主线是 neural guidance failure boundary + risk-controlled
  intervention / negative evidence；如果坚持顶会，必须提出新的硬贡献或
  新 benchmark protocol，不能沿用当前性能叙事。
- 正文必须同时报告 `75, 80, 80` CaDiCaL repeats 和 `79, 80, 80` portfolio
  repeats，不能只报原始 `75 -> 79/80`。
- Local Boundary Correction 只能说在 strict repeated-CaDiCaL 口径下打开
  `3sat_188.cnf` 这个 Local-only boundary point；不能把
  `3sat_46.cnf` / `3sat_196.cnf` 写成 strong-CDCL complement。
- March strict-60 `184/200` 必须进入 baseline discussion 或 limitation；
  如果不放，审稿人一旦发现 March 结果，当前 strong baseline claim 会崩。

Should fix if time allows:

- 加入 RLAF original checkpoint / original one-shot checkpoint 的可复现说明，确认当前 one-shot 与 RLAF baseline 的关系。
- 更强 CDCL baseline 只读审计结果：当前仓库可执行 solver 只有
  `solvers/cadical/cadical`、`solvers/glucose/simp/glucose_static`、
  `solvers/glucose_weighted/simp/glucose_static`、March/March-weighted；
  没有现成 Kissat / MapleSAT / CryptoMiniSat binary 或 runner。若要补
  Kissat/Maple，下一步不是调模型，而是先引入外部 solver artifact 和一个
  base-solver runner，按 CaDiCaL 60s full400 同口径跑 smoke -> full -> repeat。
  这属于 stronger-CDCL gate，不应和当前 neural selector 线混在一起。

Can defer to appendix / rebuttal:

- Pairwise Veto、compact stable 作为 negative learned-selector baselines，保留附录即可。

## 3. Statistical Stability

### Current Evidence

已有稳定性：

- paired bootstrap：2000 paired resamples。
- repeated split：2000 次 100-instance subset sampling。
- 结果显示 Online-Consistent Selector 相比 one-shot 的 mean-time 改善稳定。
- full400 same-seed repeated runtime：One-shot `48/200`，Online-Consistent Selector `53/200`，Old Compact `54/200`，+ Local Boundary Correction `54/200`，每个方法 `3` 次 repeat。
- full400 solver-seed robustness：seeds 1/2/3 solved count std 为 `0.0`；Online-Consistent Selector 稳定优于 One-shot，Local Boundary Correction 稳定匹配 Old Compact solved count 并降低 mean time。
- same-seed repeated runtime audit：固定 `9` 个 unique key instances，每个 pair 跑 `3` 次，覆盖 `6` 个 recovered timeout 和 `4` 个 Local Boundary Correction open-set 样本。
- same-seed repeated runtime audit supports all six recovered timeouts.
- `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups.
- `3sat_188.cnf` is boundary-sensitive.
- `3sat_66.cnf` remains neutral timeout evidence.

### Status

当前稳定性分成四层。paired bootstrap / repeated split 验证 per-instance aggregate robustness；same-seed key-claim audit 验证关键 recovered timeout 和 local correction open-set 的 wall-clock 重复稳定性；full400 same-seed repeats 验证全量表在同 seed 下的 runtime repeat；full400 solver-seed robustness 验证 seeds 1/2/3 下 solved pattern 不变。它仍没有完全回答：

> 换机器、换系统负载或更大 seed set 后，wall-clock 是否仍完全一致？

因此 runtime repeat / seed sensitivity 已从 hard evidence 缺口降级为 resolved / scoped limitation：论文可以引用 full400 repeat 和 3-seed robustness，但不要把它写成跨机器 runtime reproducibility。

### Recommendation

Resolved / robustness evidence:

- 已补 `docs/repeated_runtime_audit.md` 和 `runs/analysis/repeated_runtime_audit.csv`。
- 已补 `docs/full400_repeated_runtime.md`、`docs/full400_repeated_runtime_instance_audit.md` 和 `runs/analysis/full400_repeated_runtime/`。
- 已补 `docs/full400_seed_robustness.md` 和 `runs/analysis/full400_seed_robustness/`。
- 在实验章节明确 bootstrap / repeated split 的含义：它验证 per-instance aggregate robustness，不等价于 repeated runtime seed。
- 在 appendix 或 caption 中说明 key-claim repeated runtime audit 是 same-seed small-set audit；full400 seed robustness 是 seeds 1/2/3，不是跨机器复现。

Must fix before submission:

- 避免把 bootstrap improve probability 写成“运行重复稳定性”。

Should fix if time allows:

- 如果资源允许，再做跨机器/跨负载复现，但不要把它和当前 seed robustness 混写。

Can defer to appendix / rebuttal:

- 若资源不足，正文保留 paired bootstrap / repeated split，appendix 放 same-seed repeated runtime audit，并把 seed sensitivity 写成 limitation。

## 4. Method Novelty

### Current Evidence

当前 novelty framing 是：

- low-frequency CDCL event trace；
- Online-Consistent Selector；
- conservative risk control；
- guarded Local Boundary Correction as ablation。

Related Work 已经把 SATzilla / algorithm selection、NeuroCore、RLAF、Graph-Q-SAT、RDC-SAT、ImitSAT、NeuroSelect 分组区分。

### Gap

审稿人可能把方法理解成：

> 在 RLAF 后面加了一个分类器判断是否用 adapter。

这不是致命问题，但必须把差异写尖锐：

- selector 的输入不是静态 CNF 特征，而是真实 CDCL warmup event trace；
- selector 的目标不是 average accuracy，而是 asymmetric risk control；
- online-consistent cache 避免离线/在线证据错配；
- Local Boundary Correction 不是主模型，而是 conservative selector boundary audit。

### Recommendation

Must fix before submission:

- Method / Introduction 中明确 “not just a classifier on RLAF output”：它是 event-conditioned intervention selection under asymmetric risk。
- Related Work 中把 SATzilla 对照写清楚：SATzilla 是 per-instance solver/portfolio selection；本文是 neural feedback activation decision within one solver workflow。

Should fix if time allows:

- 加一个小方法图或流程图，突出 `one-shot prior -> warmup events -> selector -> final solve`，避免读者误解为 per-branching neural policy。

Can defer to appendix / rebuttal:

- 更形式化的风险理论、probability calibration、general NCO framing 都可以不做。

## 5. Negative Results Usage

### Current Evidence

已有负结果：

- polarity / SBE：不稳定，不能进主线。
- pairwise veto：full400 `52/200`，弱于 Online-Consistent Selector。
- compact stable：没有超过 old compact。
- no750：诊断性特征消融，不替代正式 750-feature full400 patch。

### Gap

负结果太多会稀释主线。正文如果放太多，会让论文看起来像实验日志，而不是清晰方法论文。

### Recommendation

Must fix before submission:

- 正文只保留 Table 3 ablation matrix 和一句 negative branch summary。
- no750 只写 diagnostic，不写成 final patch。

Should fix if time allows:

- appendix 放一张 compact negative-results table，统一列 polarity / SBE、pairwise veto、compact stable。

Can defer to appendix / rebuttal:

- 具体失败样本、旧 selector sweep、polarity/SBE 训练细节都不进正文。

## 6. Code and Reproducibility

### Current Evidence

已提交 paper package：

- `docs/paper_intro_abstract_draft.md`
- `docs/paper_method_section_draft.md`
- `docs/paper_related_work_outline.md`
- `docs/paper_experiment_section_draft.md`
- `docs/paper_tables_and_figures.md`
- `docs/paper_ablation_matrix.md`
- `docs/paper_stability_validation.md`
- `docs/paper_manuscript_assembly_plan.md`
- `figures/fig_full400_cactus_paper.pdf`
- `figures/fig_full400_cactus_paper.svg`
- `figures/make_full400_cactus_paper.py`

新增复现入口：

- `docs/paper_reproducibility.md`
- `docs/glucose_default_full400_eval.md`
- `run_glucose_default_full400_cpu60.py`
- `runs/glucose/solver_stats_full400_cpu60.csv`
- `runs/analysis/glucose_default_full400_summary.csv`

关键运行入口和 frozen artifacts 已纳入 git：

- `configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml`
- `configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml`
- `summarize_online_consistent_boundary400_eval.py`
- `summarize_online_consistent_boundary400_stability.py`
- `summarize_local_reopen_guarded_full400_eval.py`
- `docs/paper_artifact_manifest.md`
- `runs/analysis/online_consistent_boundary400_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_summary.csv`
- `runs/analysis/online_consistent_boundary400_stability.csv`
- `runs/analysis/repeated_runtime_audit.csv`
- `runs/analysis/appendix_300350/summary.csv`
- `data/new_closed_old_on_boundary/manifest.csv`

### Status

当前最小复现闭环已经覆盖：

- Table 1；
- Figure 1；
- Table 2 stability；
- Table 3 ablation matrix；
- repeated runtime appendix；
- 300/350 appendix；
- local correction open set；
- Glucose default baseline。

剩余边界是 full rerun 需要 checkpoint 和 CNF dataset external artifacts；frozen CSV package 已足够重建当前 paper tables 和 figures。

### Recommendation

Resolved / reproducibility package:

- `docs/paper_reproducibility.md` 和 `docs/paper_artifact_manifest.md` 已列出主表、图、appendix 表、CSV、脚本、configs 和 external artifact 边界。
- checkpoint 和 full CNF datasets 仍按 external artifact / Git LFS 待定处理，不阻塞 frozen-result table reproduction。

Should fix if time allows:

- 提供一个 `make paper-results` 或单个 shell-free command list，把 Table 1 / Figure 1 / Table 2 / Table 3 和 appendix tables 重新生成。

Can defer to appendix / rebuttal:

- 全量 training trace generation 和 all failed branches 不需要在主仓库里默认复现；可以说明需要额外 artifact。

## Overall Decision

当前状态：

```text
Writing readiness: medium for a risk-control / negative-results manuscript
Submission readiness: low for a top-conference performance-improvement claim
Evidence risk: March strict-60 baseline (184/200) dominates current neural and portfolio results. The strongest defensible claim is no longer strong-CDCL complementarity; it is failure-boundary analysis and risk-controlled neural intervention under a weaker neural-guided Glucose workflow.
```

不能继续按旧的 neural-only、portfolio-dominance 或 strong-CDCL-complementarity 叙事推进。投稿前剩余需要决策的核心是 claim positioning，其次才是 packaging：

1. 是否接受“failure boundary / risk-control / negative evidence”作为顶会目标，而不是性能 dominance。
2. 是否补 Kissat / Maple / March repeats 作为 stronger-CDCL audit。
3. checkpoint / CNF dataset 用 Git LFS 还是 external artifact。
4. seed sensitivity 是否仅作为 limitation，还是资源允许时补充。

如果时间有限，优先顺序是：

1. 更新 paper/main.tex 和 paper tables，加入 March baseline 并移除 strong-CDCL complementarity 暗示；
2. 决定是否继续跑 March repeats / Kissat / MapleSAT，或正式转为 failure-boundary 论文；
3. checkpoint/data artifact packaging decision；
4. negative-results appendix table；
5. 跨机器或更多 CaDiCaL repeats，只在资源允许时做。
