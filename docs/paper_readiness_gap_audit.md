# Paper Readiness Gap Audit

> 目标：判断当前论文骨架离顶会投稿还差哪些硬证据。
> 本文档是投稿前差距审计，不提出新模型线，不扩 selector 复杂度。

## Executive Summary

当前论文已经可以进入 LaTeX 初稿拼装，但还不建议直接投稿。主线叙事、方法草稿、实验章节、表图包、related work 和 Glucose default reference 都已经形成闭环；主要风险不在“故事能不能写”，而在审稿人会追问的复现与稳定性边界：

- 结果是否只在 3SAT-400 上成立？
- 相比强 CDCL / solver default 是否仍有意义？这一项已有 Glucose default reference，剩余问题是放正文还是附录。
- single-run wall-clock 是否受运行噪声影响？
- 复现 Table 1 / Figure 1 是否有清晰入口？

建议结论：

| Category | Items |
| --- | --- |
| Must fix before submission | 复现闭环；明确统计稳定性边界 |
| Resolved / placement pending | Glucose default / solver default full400 baseline |
| Should fix if time allows | final method 的 300/350 附录验证；runtime repeated seed；更尖锐的新颖性对照 |
| Can defer to appendix / rebuttal | 负结果细节；no750 诊断；boundary audit 表；旧 clean stability 结果 |

## 1. Experimental Strength

### Current Evidence

- 主结果只冻结在 `data/test/3sat/400/*.cnf` 的 full400 真实 wall-clock 上。
- Online-Consistent Selector：`56/200`, mean `46.2217s`。
- One-shot：`50/200`, mean `47.7517s`。
- Local Boundary Correction：`56/200`, mean `45.4976s`，只作为 ablation。
- 现有 300/350 资料主要来自 clean fixed-rho / polarity / SBE / earlier selector 线，不是最终 `online_consistent_boundary400` 主线。

### Gap

当前 hard evidence 还不足以回答：

> 这个 selector 是只在 3SAT-400 长尾上有效，还是跨 300/350/400 都有稳健行为？

已有 `docs/clean_stability_and_cactus_results.md` 可以说明早期方法在 300/350/400 的趋势，但不能直接支撑最终 Online-Consistent Selector 的跨规模泛化。

### Recommendation

Must fix before submission:

- 在正文中明确主 claim 限定为 3SAT-400 full400，避免暗示跨规模泛化已经证明。

Should fix if time allows:

- 补 final Online-Consistent Selector 在 300/350 上的附录评估，至少给出 one-shot / Online-Consistent / + Local Boundary Correction 的 solved 和 mean time。
- 如果 300/350 不适合跑 local correction，就只补 Online-Consistent Selector，并明确 local correction 只针对 400 boundary audit。

Can defer to appendix / rebuttal:

- 旧 clean 300/350/400 表可以作为负结果或方法演化背景，但不要放进主结果支撑。

## 2. Baseline Sufficiency

### Current Evidence

当前 paper-ready 主表包含：

- One-shot neural guidance baseline.
- Old Compact reference.
- Pairwise Veto negative branch.
- Online-Consistent Selector.
- + Local Boundary Correction.

README 中有 `evaluate_base_solver.py` 的原生 solver 评估入口；当前已补一版 paper-ready 的 Glucose default / solver default full400 对照：

- source: `docs/glucose_default_full400_eval.md`
- CSV: `runs/glucose/solver_stats_full400_cpu60.csv`
- summary: `runs/analysis/glucose_default_full400_summary.csv`
- result: `13/200`, mean `57.6145s`, median `60.0000s`

### Status

顶会审稿人很可能问：

> 你提升的是相对 neural one-shot baseline，还是相对强 CDCL solver？

当前实验主表主要回答“相对 RLAF-style one-shot neural guidance baseline 是否更好”。新增 Glucose default 对照显示，unguided solver default 在当前 full400 口径下为 `13/200`，明显弱于 one-shot neural guidance baseline 的 `50/200`。这可以回答 solver-default reference 问题，但论文仍应避免把结果泛化成全面击败所有强 CDCL solvers。

该项已从 hard evidence 缺口降级为 placement pending：后续只需决定 Glucose default 放在正文 baseline 表、实验设置段落，还是附录 baseline 表。

### Recommendation

Resolved / placement pending:

- 已补 solver default / unguided Glucose full400 baseline；后续需要决定放入正文 baseline 表还是 appendix baseline 表。
- 在实验设置中明确 One-shot 是 neural baseline，不是 solver default。
- 如果强 CDCL baseline 不输或更强，也要如实定位：本文贡献是 risk-controlled neural intervention，而不是全面击败所有 CDCL defaults。

Should fix if time allows:

- 加入 RLAF original checkpoint / original one-shot checkpoint 的可复现说明，确认当前 one-shot 与 RLAF baseline 的关系。
- 如果有 Kissat 或 Glucose default 的强基线，至少在 appendix 给出结果，避免审稿人认为 baseline 不充分。

Can defer to appendix / rebuttal:

- Pairwise Veto、compact stable 作为 negative learned-selector baselines，保留附录即可。

## 3. Statistical Stability

### Current Evidence

已有稳定性：

- paired bootstrap：2000 paired resamples。
- repeated split：2000 次 100-instance subset sampling。
- 结果显示 Online-Consistent Selector 相比 one-shot 的 mean-time 改善稳定。

### Gap

当前稳定性主要是 per-instance result stability，不是 runtime repeated-run stability。它没有完全回答：

> 单实例 wall-clock 结果是否受 solver/runtime 噪声或随机漂移影响？

项目中已有 `docs/recovered_timeout_stability.md` 和 `docs/pre_warmup_skip_classifier_full400_eval.md` 提醒：个别 recovered timeout 可能存在运行噪声，1 个实例漂移会影响 solved-count 叙事。

### Recommendation

Must fix before submission:

- 在实验章节明确 bootstrap / repeated split 的含义：它验证 per-instance aggregate robustness，不等价于 repeated runtime seed。
- 避免把 bootstrap improve probability 写成“运行重复稳定性”。

Should fix if time allows:

- 对 Table 1 的关键方法补 3-run repeated wall-clock：
  - One-shot
  - Online-Consistent Selector
  - + Local Boundary Correction
  - optionally Old Compact
- 至少对 6 个 recovered timeout 和 4 个 local correction open-set 样本做 repeated run audit。

Can defer to appendix / rebuttal:

- 若资源不足，正文保留 paired bootstrap，appendix 加一句 runtime repeat 是 limitation。

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

关键运行入口存在：

- `configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml`
- `configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml`
- `summarize_online_consistent_boundary400_eval.py`
- `summarize_online_consistent_boundary400_stability.py`
- `summarize_local_reopen_guarded_full400_eval.py`

但这些 configs、scripts、runs、data、checkpoints 多数仍未纳入刚才的 paper package commit。

### Gap

如果别人 clone 当前仓库，不一定能直接复现：

- Table 1；
- Figure 1；
- stability table；
- local correction open set；
- checkpoint-dependent full400 evaluation。

当前已开始整理 reproducibility package：`docs/paper_reproducibility.md` 已列出 Table 1 / Figure 1 / Table 2 / Table 3 的输入 CSV、生成脚本、Glucose default 命令、guided full400 configs、checkpoint 路径和 external artifact 边界。剩余缺口是决定哪些 guided-result CSV、configs、summarization scripts 和 manifest 要实际纳入 git。

### Recommendation

Must fix before submission:

- 已新增最小复现清单 `docs/paper_reproducibility.md`；下一步需要把清单中的最小 guided-result artifacts 纳入仓库或明确为 external artifact。
- 决定哪些文件纳入仓库，哪些作为 external artifact：
  - configs；
  - summarization scripts；
  - `runs/analysis/*summary.csv` / `*per_instance.csv`；
  - `data/new_closed_old_on_boundary/manifest.csv`；
  - paper-ready figures；
  - checkpoints。
- 更新 README 或新增 `docs/paper_reproducibility.md`，让读者知道怎么复现 paper tables。

Should fix if time allows:

- 提供一个 `make paper-results` 或单个 shell-free command list，把 Table 1 / Figure 1 / Table 2 / Table 3 重新生成。

Can defer to appendix / rebuttal:

- 全量 training trace generation 和 all failed branches 不需要在主仓库里默认复现；可以说明需要额外 artifact。

## Overall Decision

当前状态：

```text
Writing readiness: high
Submission readiness: medium
Evidence risk: medium after Glucose default baseline; remaining risk is reproducibility closure and runtime-repeat scope
```

可以开始拼 LaTeX 初稿，但投稿前必须补齐最小硬证据：

1. 复现闭环。
2. 统计稳定性的边界说明，最好补 runtime repeated run。
3. Glucose default baseline 的正文/附录 placement。

如果时间有限，优先顺序是：

1. paper reproducibility package；
2. repeated runtime audit；
3. 300/350 final method appendix；
4. negative-results appendix table。
