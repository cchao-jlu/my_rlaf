# Paper Manuscript Assembly Plan

> 目标：把已有论文素材组织成可拼 LaTeX 初稿的最小闭环。
> 本文档不引入新实验，不扩模型，只规定正文结构、素材来源、表图优先级和 camera-ready 前检查项。

## 1. Manuscript Structure

建议论文正文按以下顺序装配：

1. Abstract
2. Introduction
3. Related Work
4. Method
5. Experiments
6. Discussion / Limitations
7. Conclusion

主叙事只保留一条：

```text
one-shot neural guidance
-> low-frequency CDCL warmup event traces
-> Online-Consistent Selector
-> conservative risk-controlled intervention
-> guarded Local Boundary Correction as ablation
```

不要把 Local Boundary Correction 写成单独主方法；它是对保守 selector 边界错误的 guarded ablation。

## 2. Section Source Map

| Paper section | Primary source document | How to use |
| --- | --- | --- |
| Abstract | `docs/paper_intro_abstract_draft.md` | 使用 `Abstract Draft`，保留 “As an ablation” 的 Local Boundary Correction 表述。 |
| Introduction | `docs/paper_intro_abstract_draft.md` | 按 Problem / Gap / Method / Result / Contributions 扩写。 |
| Related Work | `docs/paper_related_work_outline.md` | 按四组写：learning-guided SAT、solver-state feedback、risk-controlled intervention、event-conditioned identity。 |
| Method | `docs/paper_method_section_draft.md` | 直接改写为正式 Method；保留低频调用、online-consistent trace、same-evidence counterfactual 的谨慎表述。 |
| Experiments | `docs/paper_experiment_section_draft.md` | 作为实验章节正文骨架；结果只引用最终 full400 wall-clock 和稳定性表。 |
| Tables / Figures | `docs/paper_tables_and_figures.md` | 复制 LaTeX 表格、caption 和 figure include 路径。 |
| Ablation details | `docs/paper_ablation_matrix.md` | 只保留正文消融矩阵；no750 明确为 diagnostic。 |
| Stability details | `docs/paper_stability_validation.md` | 支撑 Table 2 和稳定性段落。 |

## 3. Required Main-Text Tables and Figures

正文必须包含以下四个表图：

| Priority | Item | Source | Main claim |
| --- | --- | --- | --- |
| 1 | Table 1: Full400 main results | `docs/paper_tables_and_figures.md` | Online-Consistent Selector 将 one-shot 从 `50/200` 提升到 `56/200`，mean time `47.752s -> 46.222s`。 |
| 2 | Figure 1: paper-ready full400 cactus | `figures/fig_full400_cactus_paper.pdf` / `.svg` | Online-Consistent Selector 与 + Local Boundary Correction 的 solved-time distribution。 |
| 3 | Table 2: stability validation | `docs/paper_tables_and_figures.md`, `docs/paper_stability_validation.md` | mean-time 改善在 bootstrap / repeated split 下稳定。 |
| 4 | Table 3: ablation matrix | `docs/paper_tables_and_figures.md`, `docs/paper_ablation_matrix.md` | Local Boundary Correction 是 guarded boundary repair；no750 只是 diagnostic。 |

正文图表命名建议：

- `One-shot`
- `Old Compact`
- `Online-Consistent Selector`
- `+ Local Boundary Correction` in tables
- `Local Boundary Correction` in figure legend if the plus sign hurts visual clarity

需要统一的一点：正文叙述第一次出现时写 `+ Local Boundary Correction`，说明它是在 Online-Consistent Selector 上的 ablation；后文可简写为 `Local Boundary Correction`。

## 4. Appendix or Discussion Only

以下内容只能进附录或 discussion，不能进入主贡献：

| Content | Placement | Rule |
| --- | --- | --- |
| polarity / SBE | appendix negative results or limitations | 写成不稳定分支，不作为方法组件。 |
| pairwise veto | appendix negative results | full400 solved count `52/200`，说明复杂 selector 没有带来主线收益。 |
| compact stable | appendix negative results / baseline discussion | 用于说明 stable 分支不如 old compact；不要作为 old compact 数字的主要证据。 |
| no750 diagnostic | ablation appendix or short note under Table 3 | 不能替代正式 750-feature full400 patch。 |
| boundary audit optional table | appendix or short experiment audit | 可展示 `3sat_188/196/46/66`，但不要让它抢主结果表的位置。 |
| old internal cactus figures | appendix only if needed | 正文使用 `figures/fig_full400_cactus_paper.pdf`。 |

负结果 discussion 的推荐主题：

- 为什么不继续堆 selector 复杂度。
- 为什么 solved count 和 mean wall-clock time 都要报告。
- 为什么 boundary correction 改善 mean time 但不作为主方法突破。

## 5. Camera-Ready Checklist

LaTeX 初稿前必须处理：

- 拉正式 BibTeX：
  - RLAF / ImitSAT from OpenReview ICLR 2026
  - NeuroSAT / NeuroBack from OpenReview
  - Graph-Q-SAT from NeurIPS proceedings
  - RDC-SAT from ICLR proceedings
  - NeuroSelect from DAC / ACM / DBLP
  - SATzilla / algorithm selection
  - GNN expressivity / WL papers
- 统一命名：
  - 代码/结果名：`online_consistent_boundary400`
  - 论文名：`Online-Consistent Selector`
  - 表格名：`+ Local Boundary Correction`
  - 正文简写：`Local Boundary Correction`
- 确认所有 paper-ready 文件是否纳入仓库：
  - `docs/paper_intro_abstract_draft.md`
  - `docs/paper_method_section_draft.md`
  - `docs/paper_related_work_outline.md`
  - `docs/paper_experiment_section_draft.md`
  - `docs/paper_tables_and_figures.md`
  - `docs/paper_ablation_matrix.md`
  - `docs/paper_stability_validation.md`
  - `figures/fig_full400_cactus_paper.pdf`
  - `figures/fig_full400_cactus_paper.svg`
  - `figures/make_full400_cactus_paper.py`
- 检查 caption 是否避免过度主张：
  - 不说 Local Boundary Correction 是主模型。
  - 不说 no750 是最终 full400 patch。
  - 不说 CDCL event traces 解决 GNN / WL 表达力瓶颈。
  - 不说 same-evidence counterfactual 是 exact CDCL clone continuation。
- 确认 abstract / intro 不保留内部审计日期，比如 “checked on 2026-05-25”。
- 确认所有 full400 结论都来自最终在线一致结果和真实 wall-clock，不复用旧 cache。

## 6. Minimal LaTeX Build Order

建议按以下顺序拼第一版 LaTeX：

1. 从 `docs/paper_intro_abstract_draft.md` 放入 Abstract 和 Introduction。
2. 从 `docs/paper_method_section_draft.md` 放入 Method，并保留 Algorithm 1。
3. 从 `docs/paper_tables_and_figures.md` 放入 Table 1 和 Figure 1。
4. 从 `docs/paper_experiment_section_draft.md` 放入 Experiments 主体。
5. 放入 Table 2 和 Table 3。
6. 从 `docs/paper_related_work_outline.md` 压缩成 Related Work。
7. 写 Discussion / Limitations，集中处理 negative branches 和 boundary correction 的定位。
8. 最后写 Conclusion，只重复三条贡献，不新增 claim。

## 7. Claim Boundaries

可以写：

- Online-Consistent Selector uses real CDCL event traces to make a conservative intervention decision.
- The selector improves full400 solved count over one-shot from `50/200` to `56/200`.
- Guarded Local Boundary Correction preserves solved count and reduces mean time from `46.222s` to `45.498s`.
- CDCL event traces provide search-induced distinctions not present in the static CNF graph alone.

不要写：

- Local Boundary Correction is the main model.
- no750 is the final full400 patch.
- More complex selector branches improve the main result.
- CDCL event traces solve the WL / GNN expressivity limitation.
- Counterfactual labels are exact continuations from cloned CDCL internal states.
