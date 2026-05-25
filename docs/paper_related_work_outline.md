# Related Work Outline

> 目标：给论文 Related Work 提供可直接扩写的结构、对比口径和引用锚点。
> 本文档只整理文献定位，不引入新实验，也不把负结果分支写成贡献。

## 写作目标

Related Work 要服务三件事：

1. 说明本文继承 learning-guided SAT solving，但不是又一个静态 one-shot 或 per-branching neural heuristic。
2. 说明本文的核心差异是低频 CDCL event trace + online-consistent conservative selector。
3. 说明本文对 event-conditioned identity / symmetry 的说法是经验性和工程性的，不声称解决 GNN 表达力瓶颈。

## 来源状态

已在 2026-05-25 核对主要引用锚点。当前建议把 RLAF 和 ImitSAT 都按 ICLR 2026 poster / OpenReview 版本引用，同时保留 arXiv 号作为预印本入口。NeuroSAT、Graph-Q-SAT、RDC-SAT、NeuroSelect、SATzilla、GNN expressivity 相关论文都有稳定的会议、journal 或 proceedings 锚点。

本文档仍是 outline，不直接替代 `.bib` 文件。写 LaTeX 正文前还需要从 OpenReview、NeurIPS proceedings、ICLR proceedings、DAC/ACM 或 arXiv 页面拉正式 BibTeX。

建议最终 Related Work 分成四组：

1. Learning-guided SAT solving
2. Dynamic / online solver feedback
3. Risk-aware neural combinatorial optimization
4. Symmetry breaking and event-conditioned identity

## 1. Learning-Guided SAT Solving

这一组用于放本文的直接上下文：神经网络如何进入 SAT solver。

### 主要文献

| Work | Core idea | How to position it |
| --- | --- | --- |
| NeuroSAT / "Learning a SAT Solver from Single-Bit Supervision" | Message-passing neural network trained from satisfiable/unsatisfiable labels; demonstrates that neural embeddings can capture SAT structure. | Foundation for neural SAT reasoning, but not a practical CDCL guidance mechanism for modern wall-clock solving. |
| NeuroCore / "Guiding High-Performance SAT Solvers with Unsat-Core Predictions" | Predict variables likely to appear in unsat cores; periodically inject predictions into variable activity scores of high-performance SAT solvers. | Closest early example of neural predictions guiding existing solvers; differs from our event-conditioned selector and risk-control framing. |
| Graph-Q-SAT | Uses GNN function approximation in an RL branching heuristic for MiniSAT. | Demonstrates learned branching can generalize, but motivates our avoidance of frequent neural calls in the solver loop. |
| NeuroBack | Predicts variable phases/backbones once before CDCL solving; emphasizes practical integration and avoiding repeated online GPU inference. | Shares the low-frequency inference motivation, but remains essentially static one-shot guidance rather than event-conditioned online selection. |
| RLAF | One-shot GNN predicts variable weights and polarities; trained with solver feedback / GRPO. | Direct baseline and starting point. Our method keeps the one-shot neural prior but adds online-consistent warmup event evidence and a conservative selector. |

### Paragraph Draft

Recent learning-guided SAT solvers inject neural predictions into complete CDCL solvers in several ways. NeuroSAT-style models showed that message passing can learn useful SAT representations, and NeuroCore demonstrated that neural unsat-core predictions can guide high-performance solvers through variable activity. Graph-Q-SAT moved closer to branching by learning a GNN-based RL branching heuristic, while NeuroBack and RLAF emphasized practical low-frequency guidance: predicting phases, weights, or polarities before search rather than querying a neural model at every decision. Our work follows this practical line but differs in one key respect: the guidance decision is not purely static. We use the one-shot neural guidance prior to collect warmup CDCL event evidence, then decide conservatively whether event-conditioned feedback should be activated for the final solve.

### What Not To Claim

- Do not say prior one-shot methods are weak; say they are static and do not use the observed search trajectory.
- Do not imply Graph-Q-SAT is impractical in all settings; say frequent or online neural branching motivates explicit wall-clock accounting and low-frequency intervention.
- Do not overstate RLAF as "only baseline"; it is the direct predecessor and should be treated respectfully.

## 2. Dynamic / Online Solver Feedback

这一组用于强调本文不是纯静态 one-shot，也不是高频 neural branching，而是低频 event trace + selector。

### 主要文献

| Work | Dynamic signal | How to position it |
| --- | --- | --- |
| Graph-Q-SAT | Solver state / evolving SAT graph during branching. | Dynamic branching with neural inference in the solver loop; contrasts with our low-frequency warmup-selector-final-solve workflow. |
| RDC-SAT | Dynamic current solving state in divide-and-conquer splitting, including learned clauses, variable activity, and LBD. | Shows solver-internal state is valuable for learned decisions; our setting uses CDCL event traces for selective guidance activation rather than D&C split selection. |
| ImitSAT | Expert KeyTrace distilled from CDCL runs into dense branching supervision. | Supports the value of solver traces as supervision; our traces are used for risk-controlled intervention selection, not direct imitation of every branch. |
| NeuroSelect | Learns to select clause-deletion policies in SAT solvers. | Supports using internal CDCL signals; differs because our intervention target is variable guidance activation, not clause database management. |

### Paragraph Draft

Several recent systems use solver-internal information rather than only static CNF structure. Graph-Q-SAT and RDC-SAT condition learned decisions on evolving solver states, while ImitSAT and NeuroSelect show that traces, clauses, activities, and other CDCL artifacts can provide dense learning signals. Our use of solver feedback is narrower and more conservative. We do not learn a full branching policy, splitting policy, or clause-deletion policy. Instead, we collect event traces at configured intervention points and use them to decide whether a pre-existing neural guidance adapter should be activated for the final solve.

### Method Contrast Sentence

Use this sentence if space is tight:

> In contrast to learned branching or splitting policies that repeatedly interact with the solver state, our method uses CDCL events as low-frequency evidence for a single risk-controlled intervention decision.

## 3. Risk-Aware Neural Combinatorial Optimization

这一组用于给 conservative selector 找合理性：不是平均最快，而是不丢解、不明显拖慢。

### Framing

Many neural combinatorial optimization methods optimize expected cost or average runtime. In complete solvers, however, a learned heuristic can be harmful even when its average effect is positive: it may lose solutions that the base solver would find, or it may slow down easy and medium instances enough to erase gains from hard-instance speedups. SAT solver integration therefore needs safety-oriented evaluation, not only average reward.

### How This Paper Fits

本文把 risk-aware 写成工程化的 conservative risk control：

- `risk head`: suppresses adapter activation when event evidence resembles slowdown or lost-solution cases.
- `recovery head`: opens adapter only when evidence resembles recovered-timeout or hard-speedup cases.
- optional slowdown veto: further blocks cases with high slowdown probability.
- final claim: solved count and wall-clock mean must both be reported; local correction is only an ablation because it improves mean time but not solved count.

### Related Framing Anchors

| Area | How to use it |
| --- | --- |
| SATzilla / per-instance SAT algorithm selection | Shows that per-instance solver decisions are a standard SAT idea. Our selector is narrower: it selects whether to activate neural feedback, not which solver from a portfolio to run. |
| Empirical hardness / algorithm selection | Supports reporting instance-level behavior, not only aggregate mean runtime. |
| Neural combinatorial optimization | Provides broad context for learned heuristics, but the paper should avoid claiming a new NCO theory. Our contribution is a risk-controlled intervention mechanism for a complete solver. |

### Paragraph Draft

Neural guidance for complete combinatorial solvers should be evaluated under asymmetric risk. A heuristic that improves a few hard instances can still be undesirable if it loses solutions or slows many easy instances. This motivates treating adapter activation as a risk-controlled intervention rather than a generic binary classification problem. Our selector separates recovery potential from slowdown and lost-solution risk, and activates neural feedback only when the recovery evidence is strong and the risk evidence is low. This framing also explains our experimental emphasis: solved count, lost-solution behavior, per-instance win/loss, and wall-clock mean are all part of the evidence.

### What Not To Claim

- Do not introduce a broad new "risk-aware NCO" theory unless the paper later adds formalism.
- Do not claim calibrated probabilities unless calibration is explicitly evaluated.
- Do not claim Local Boundary Correction is risk-free; say it is guarded and empirically safe on the evaluated open set.

## 4. Symmetry Breaking and Event-Conditioned Identity

这一组要轻写。它可以解释为什么 CDCL event traces are useful，但不要拔高成“解决 GNN WL bottleneck”。

### 主要文献

| Work | Core point | How to use it |
| --- | --- | --- |
| How Powerful are Graph Neural Networks? | Message-passing GNN expressivity is connected to 1-WL / neighborhood aggregation limits. | Motivates why static graph structure can be insufficient on symmetric CNF graphs. |
| Weisfeiler and Leman Go Neural | Relates GNN expressivity to 1-WL and proposes higher-order variants. | Supports the broader expressivity framing without making this paper theoretical. |
| CDCL event traces in this work | Decisions, propagations, conflicts, learnt-literal occurrences, activity. | Search-induced evidence can distinguish variables that look similar in the static CNF graph. |

### Paragraph Draft

Static message-passing GNNs are limited by their neighborhood aggregation view of the input graph, a limitation often analyzed through the lens of the Weisfeiler-Leman hierarchy. SAT instances can contain variables that are structurally similar in the CNF graph but behave differently once CDCL search begins. We use CDCL events as search-induced evidence: decisions, propagations, conflicts, learnt-literal occurrences, and activity provide dynamic distinctions among variables and instances. We do not claim that this solves the theoretical expressivity limits of GNNs. Rather, it supplies practical online features that help decide when neural feedback is likely to be useful.

### Safe Claim

> CDCL event traces provide search-induced distinctions among otherwise similar variables, giving the selector information not present in the static CNF graph alone.

### Unsafe Claim

> CDCL event traces solve the 1-WL limitation of message-passing GNNs.

Do not use the unsafe claim.

## Suggested Related Work Section Skeleton

```latex
\section{Related Work}

\paragraph{Learning-guided SAT solving.}
Discuss NeuroSAT, NeuroCore, Graph-Q-SAT, NeuroBack, and RLAF. End by saying our work keeps the practical low-frequency guidance philosophy of one-shot methods but adds online event evidence and a conservative selector.

\paragraph{Solver-state and trace-based learning.}
Discuss dynamic solver-state methods such as Graph-Q-SAT and RDC-SAT, and trace-supervised systems such as ImitSAT and NeuroSelect. End by emphasizing that our method uses traces for one risk-controlled intervention decision, not for every branch or clause-management action.

\paragraph{Risk-controlled neural intervention.}
Explain why complete solvers require conservative activation: average runtime alone is not enough if the learned branch can lose solutions or slow easy instances. Position the risk/recovery selector here.

\paragraph{Event-conditioned identity.}
Briefly mention GNN expressivity limits and static CNF symmetry. Use CDCL events as practical search-induced identity, not as a theoretical expressivity claim.
```

## Contribution Framing After Related Work

Keep the final contribution list to three bullets:

1. Event-conditioned online selector using real CDCL event traces.
2. Conservative risk control separating recovery potential from slowdown/lost-solution risk.
3. Guarded local boundary correction for over-conservative selector errors.

Do not list no750, polarity/SBE, compact stable, or pairwise veto as contributions.

## Citation Anchors

Use these as citation placeholders when moving to LaTeX:

- RLAF: Tönshoff and Grohe, "Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs", ICLR 2026 poster / arXiv:2505.16053. OpenReview: https://openreview.net/forum?id=NfWrLOKnfk
- NeuroSAT: Selsam et al., "Learning a SAT Solver from Single-Bit Supervision", ICLR 2019 / arXiv:1802.03685. OpenReview: https://openreview.net/forum?id=HJMC_iA5tm
- NeuroCore: Selsam and Bjørner, "Guiding High-Performance SAT Solvers with Unsat-Core Predictions", arXiv:1903.04671. arXiv: https://arxiv.org/abs/1903.04671
- Graph-Q-SAT: Kurin et al., "Can Q-Learning with Graph Networks Learn a Generalizable Branching Heuristic for a SAT Solver?", NeurIPS 2020. Proceedings: https://proceedings.neurips.cc/paper/2020/hash/6d70cb65d15211726dcce4c0e971e21c-Abstract.html
- NeuroBack: Wang et al., "NeuroBack: Improving CDCL SAT Solving using Graph Neural Networks", ICLR 2024 / arXiv:2110.14053. OpenReview: https://openreview.net/forum?id=samyfu6G93
- RDC-SAT: Zhai and Ge, "Learning Splitting Heuristics in Divide-and-Conquer SAT Solvers with Reinforcement Learning", ICLR 2025. Proceedings: https://proceedings.iclr.cc/paper_files/paper/2025/hash/f5c683b93319b82689af3afc71257df2-Abstract-Conference.html
- ImitSAT: Zhang et al., "Boolean Satisfiability via Imitation Learning", ICLR 2026 poster / arXiv:2509.25411. OpenReview: https://openreview.net/forum?id=LNqWbY5iIf
- NeuroSelect: Liu et al., "NeuroSelect: Learning to Select Clauses in SAT Solvers", DAC 2024, DOI 10.1145/3649329.3656250. DBLP: https://dblp.org/rec/conf/dac/LiuXPYZYH024
- SATzilla / algorithm selection: Xu et al., "SATzilla: Portfolio-based Algorithm Selection for SAT", JAIR 2008 / arXiv:1111.2249, DOI 10.1613/jair.2490. arXiv: https://arxiv.org/abs/1111.2249
- Algorithm selection survey: Kotthoff, "Algorithm Selection for Combinatorial Search Problems: A Survey", arXiv:1210.7959.
- GNN expressivity: Xu et al., "How Powerful are Graph Neural Networks?", ICLR 2019. OpenReview / ICLR: https://iclr.cc/virtual/2019/poster/791
- Higher-order GNN / WL: Morris et al., "Weisfeiler and Leman Go Neural: Higher-Order Graph Neural Networks", AAAI 2019, DOI 10.1609/aaai.v33i01.33014602. AAAI: https://ojs.aaai.org/index.php/AAAI/article/view/4384

## Open BibTeX Tasks

- Pull official BibTeX from OpenReview, NeurIPS proceedings, ICLR proceedings, DAC/ACM, AAAI, and arXiv pages.
- Decide whether ImitSAT belongs in main text or appendix. Current recommendation: main text if space allows, because it is trace-heavy and directly clarifies how our trace use differs from decision-level imitation.
- Decide whether NeuroSelect is main related work or a short clause-management aside. Current recommendation: short aside under solver-state and trace-based learning.
