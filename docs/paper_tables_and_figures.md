# Paper-Ready Tables and Figures

> 本文档集中整理实验章节可直接使用的 LaTeX 表格、图标题、caption 和引用来源。
> 数字默认保留三位小数；概率保留三位；solved count 保留整数。
> `one_shot` 在论文中写作 One-shot neural guidance baseline。

## Naming Conventions

论文正文统一使用以下方法名：

| Code / result name | Paper name | Role |
| --- | --- | --- |
| `one_shot` / `oneshot` | One-shot | one-shot neural guidance baseline |
| `old_compact` | Old Compact | stable reference baseline |
| `online_consistent_boundary400` | Online-Consistent Selector | neural-stage selector |
| `local_reopen_guarded` | + Local Boundary Correction | boundary correction ablation |
| `portfolio_e2e_local5_cadical55` | Local5 -> CaDiCaL55 Portfolio | main portfolio result |
| `pairwise_veto` / `pairwise_veto_actual` | Pairwise Veto | negative branch |

固定口径：

- 当前最强证据是 `Local5 -> CaDiCaL55 Portfolio` 的 boundary-sensitive complementarity，不是 neural-only full400 表。
- Online-Consistent Selector 和 + Local Boundary Correction 是 portfolio 的 neural-first stage / mechanism analysis。
- + Local Boundary Correction 只作为 guarded neural-stage component，不作为 unrestricted neural main model。
- 正式 + Local Boundary Correction full400 patch 是含 750 特征版本。
- no750 只作为 diagnostic feature ablation；它的 open set 与正式 full400 patch 不同，不能替代正式结果。
- portfolio-only evidence 必须拆分为 neural-first complement 和 second-stage CaDiCaL runtime-boundary evidence。
- full overlap evidence 也要单独报告：Local/CaDiCaL strict complement 是 3 个实例，Online/CaDiCaL strict complement 是 2 个实例，Local-only strict boundary contribution 是 1 个实例。
- March strict-60 baseline 是当前最强 baseline：184/200，mean capped time 26.702s。它解掉 CaDiCaL-strict complement 的 `3sat_140.cnf`, `3sat_147.cnf`, `3sat_188.cnf`，所以不能再写 strong-SAT-baseline complementarity claim。

## Table 1: Full400 Portfolio Main Results

Caption:

> End-to-end full400 portfolio and repeated CaDiCaL baseline on 200 held-out 3SAT-400 instances. The portfolio runs + Local Boundary Correction for at most 5s, then CaDiCaL for at most 55s on unsolved instances. CaDiCaL repeats are standalone 60s runs. The model, selector, correction guard, solver binaries, and time split are fixed.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{End-to-end full400 portfolio and repeated CaDiCaL baseline on 200 held-out 3SAT-400 instances. The portfolio runs + Local Boundary Correction for at most 5s, then CaDiCaL for at most 55s on unsolved instances. CaDiCaL repeats are standalone 60s runs. The model, selector, correction guard, solver binaries, and time split are fixed.}
\label{tab:portfolio-main}
\begin{tabular}{lrrrrrr}
\toprule
Run & Portfolio & Local & C2 solves & CaDiCaL & Delta & C-only loss \\
\midrule
0 & 79 & 40 & 39 & 75 & +4 & 0 \\
1 & 80 & 40 & 40 & 80 & +0 & 0 \\
2 & 80 & 40 & 40 & 80 & +0 & 0 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The end-to-end neural-first/CDCL-second portfolio solves 79-80/200 instances over three full400 repeats. The original standalone CaDiCaL 60s run solved 75/200, but repeated CaDiCaL 60s runs solve 75, 80, and 80 instances. Matched same-repeat deltas are therefore +4, 0, and 0. This is boundary-sensitive complementarity evidence, not robust solved-count dominance over CaDiCaL.

Sources:

- `docs/portfolio_e2e_local5_cadical55_stability.md`
- `runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv`
- `runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_aggregate.csv`
- `runs/analysis/portfolio_e2e_local5_cadical55/repeat_instance_overlap.csv`
- `docs/cadical_repeat_stability.md`
- `runs/analysis/cadical_repeat_stability/portfolio_vs_cadical_repeats.csv`

## Table 2: Repeated-CaDiCaL Overlap Audit

Caption:

> Full repeated-CaDiCaL overlap audit on 200 held-out 3SAT-400 instances. Neural solved means solved in all three neural solver-seed runs. CaDiCaL unsolved means unsolved in all three standalone CaDiCaL 60s repeats. Local-only is the strict boundary-correction contribution beyond Online-Consistent Selector.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Full repeated-CaDiCaL overlap audit on 200 held-out 3SAT-400 instances. Neural solved means solved in all three neural solver-seed runs. CaDiCaL unsolved means unsolved in all three standalone CaDiCaL 60s repeats. Local-only is the strict boundary-correction contribution beyond Online-Consistent Selector.}
\label{tab:cadical-overlap}
\begin{tabular}{lr}
\toprule
Overlap question & Count \\
\midrule
CaDiCaL solved in any repeat / Local unsolved & 29 \\
CaDiCaL solved in all repeats / Local unsolved & 26 \\
Local solved / CaDiCaL unsolved in all repeats & 3 \\
Online solved / CaDiCaL unsolved in all repeats & 2 \\
Local-only over Online / CaDiCaL unsolved in all repeats & 1 \\
One-shot timeout recovered by Online; CaDiCaL solved all & 5 \\
Local Correction open set; CaDiCaL solved all & 2/4 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The full repeated-baseline overlap audit separates neural-workflow recovery from CaDiCaL-specific complementarity. Local Boundary Correction solves three instances that CaDiCaL misses in all three repeats: `3sat_140.cnf`, `3sat_147.cnf`, and `3sat_188.cnf`. Online-Consistent Selector already solves `3sat_140.cnf` and `3sat_147.cnf`, leaving `3sat_188.cnf` as the only strict Local-only gain beyond Online and repeated CaDiCaL. The five one-shot timeouts recovered by Online are all solved by CaDiCaL in all three repeats. After the March audit, this should not be described as strong-SAT-baseline complementarity.

Sources:

- `docs/cadical_repeated_neural_overlap_audit.md`
- `runs/analysis/cadical_repeated_neural_overlap/summary.csv`
- `runs/analysis/cadical_repeated_neural_overlap/local_solved_cadical_unsolved_all.csv`
- `runs/analysis/cadical_repeated_neural_overlap/local_only_solved_cadical_unsolved_all.csv`
- `runs/analysis/cadical_repeated_neural_overlap/oneshot_timeout_recovered_by_online.csv`

## Table 3: March Strong-Baseline Audit

Caption:

> March full400 baseline using the existing unweighted March binary. Because the current March runner uses an external 65s guard rather than an internal 60s limit, strict 60s treats solutions with wall time greater than 60s as timeouts.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{March full400 baseline using the existing unweighted March binary. Because the current March runner uses an external 65s guard rather than an internal 60s limit, strict 60s treats solutions with wall time greater than 60s as timeouts.}
\label{tab:march-baseline}
\begin{tabular}{lrrrr}
\toprule
Solver & Solved ext-65 & Solved strict-60 & Mean strict-60 (s) & Median strict-60 (s) \\
\midrule
March & 192 & 184 & 26.702 & 28.759 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The March baseline changes the interpretation of the strong-baseline story. Under strict 60s, March solves 184/200, far above the Local5 -> CaDiCaL55 portfolio and all neural-guided Glucose variants. It solves all three Local-solved / repeated-CaDiCaL-unsolved instances (`3sat_140.cnf`, `3sat_147.cnf`, `3sat_188.cnf`). Therefore the current evidence cannot support a strong-SAT-baseline complementarity or performance claim; the defensible direction is risk-controlled neural feedback and failure-boundary analysis.

Sources:

- `docs/march_full400_baseline_audit.md`
- `runs/march/solver_stats_full400_cpu60.csv`
- `runs/analysis/march_full400_cpu60/strict60_summary.csv`
- `runs/analysis/march_full400_cpu60/neural_vs_march_overlap.csv`
- `runs/analysis/march_full400_cpu60/strict_complement_keys.csv`

## Table 4: Portfolio Claim Split

Caption:

> Portfolio-only evidence under the original CaDiCaL 60s run, with repeated-CaDiCaL audit. Neural-first complement means + Local Boundary Correction solves the instance within the 5s first-stage budget while the original standalone CaDiCaL 60s run times out. Repeated CaDiCaL runs show that only one such instance remains unsolved by CaDiCaL across all repeats.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Portfolio-only evidence under the original CaDiCaL 60s run, with repeated-CaDiCaL audit. Neural-first complement means + Local Boundary Correction solves the instance within the 5s first-stage budget while the original standalone CaDiCaL 60s run times out. Repeated CaDiCaL runs show that only one such instance remains unsolved by CaDiCaL across all repeats.}
\label{tab:portfolio-claim-split}
\begin{tabular}{p{0.46\linewidth}rrr}
\toprule
Evidence class & Inst. & PO reps & Repeated-CaDiCaL strict \\
\midrule
Original-run neural-first complement & 3 & 9 & 1 \\
Stable second-stage runtime boundary & 1 & 3 & 0 \\
Unstable second-stage runtime boundary & 1 & 2 & 0 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

Under the original CaDiCaL run, portfolio-only neural-first complement consists of `3sat_132.cnf`, `3sat_140.cnf`, and `3sat_25.cnf`; repeated CaDiCaL runs solve `3sat_132.cnf` and `3sat_25.cnf`, leaving `3sat_140.cnf` as the strict repeated-baseline complement within this original-run portfolio-only split. `3sat_111.cnf` and `3sat_48.cnf` are CaDiCaL runtime-boundary cases. Therefore, the paper may report the original-run portfolio-only evidence, but must not describe the entire +4/+5 original delta as repeated-baseline robust. Do not confuse this table with the full overlap audit above, where Local/CaDiCaL strict complement is 3 and Local-only over Online is 1.

Sources:

- `docs/portfolio_claim_split.md`
- `runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv`
- `runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split_summary.csv`
- `runs/analysis/cadical_repeat_stability/key_boundary_audit.csv`

## Table 5: Neural-Stage Mechanism Results

Caption:

> Neural-stage full400 solver-seed robustness on 200 held-out 3SAT-400 instances. Values are means over Glucose seeds 1, 2, and 3. These rows explain the neural first stage used in the portfolio; they are not the top-line strong-CDCL result.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Neural-stage full400 solver-seed robustness on 200 held-out 3SAT-400 instances. Values are means over Glucose seeds 1, 2, and 3. These rows explain the neural first stage used in the portfolio; they are not the top-line strong-CDCL result.}
\label{tab:neural-stage}
\begin{tabular}{lrrrr}
\toprule
Method & Solved & Mean time (s) & Median time (s) & Solved std \\
\midrule
One-shot & 48.0 & 47.665 & 60.289 & 0.0 \\
Online-Consistent Selector & 53.0 & 46.324 & 60.366 & 0.0 \\
Old Compact & 54.0 & 46.278 & 60.373 & 0.0 \\
+ Local Boundary Correction & 54.0 & 45.914 & 60.369 & 0.0 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

Online-Consistent Selector is stable over One-shot across seeds 1/2/3, improving solved count from 48/200 to 53/200. Old Compact remains a strong matched neural-stage reference at 54/200. + Local Boundary Correction matches Old Compact solved count and gives the lowest mean time. This table explains the Local first-stage component used in the portfolio; it should not be presented as beating CaDiCaL.

Sources:

- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_seed_robustness/method_summary.csv`
- `runs/analysis/full400_seed_robustness/seed_summary.csv`
- `runs/analysis/full400_seed_robustness/per_instance_summary.csv`

Historical single-run sources remain useful context but should not be used as a main table:

- `docs/online_consistent_boundary400_full400_eval.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/compact_risk_full400_eval.md`

## Table 6: Stability Validation

Caption:

> Neural-stage full400 runtime and solver-seed robustness. Same-seed repeats use three full400 reruns with the default seed. Solver-seed robustness uses Glucose seeds 1, 2, and 3. The model, thresholds, and Local Boundary Correction guard are unchanged.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Neural-stage full400 runtime and solver-seed robustness. Same-seed repeats use three full400 reruns with the default seed. Solver-seed robustness uses Glucose seeds 1, 2, and 3. The model, thresholds, and Local Boundary Correction guard are unchanged.}
\label{tab:full400-stability}
\begin{tabular}{lrrrr}
\toprule
Method & Repeat & Seed & Std & Mean (s) \\
\midrule
One-shot & 48.0 & 48.0 & 0.0 & 47.665 \\
Online-Consistent Selector & 53.0 & 53.0 & 0.0 & 46.324 \\
Old Compact & 54.0 & 54.0 & 0.0 & 46.278 \\
+ Local Boundary Correction & 54.0 & 54.0 & 0.0 & 45.914 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The neural-stage stability analysis supports the same interpretation as the mechanism table. Online-Consistent Selector is stable over One-shot, Old Compact remains the strongest uncorrected neural-stage reference in solved count, and + Local Boundary Correction matches Old Compact solved count while giving the lowest mean time. Portfolio-level stability is reported separately in Table 1.

Sources:

- `docs/full400_repeated_runtime.md`
- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_repeated_runtime/summary.csv`
- `runs/analysis/full400_seed_robustness/method_summary.csv`

## Table 7: Ablation Matrix

Caption:

> Ablations used in the paper narrative. The official full400 boundary correction uses the 750-feature guarded rule. The no750 row is diagnostic only and has not replaced the official full400 patch.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Ablations used in the paper narrative. The official full400 boundary correction uses the 750-feature guarded rule. The no750 row is diagnostic only and has not replaced the official full400 patch.}
\label{tab:boundary-ablation}
\begin{tabular}{llll}
\toprule
Ablation & Scope & Result & Takeaway \\
\midrule
No guard & boundary subset & 5/26; mean 53.341 $\rightarrow$ 51.675 & Local signal exists, but needs a guard \\
Candidate guard & full400 3-seed & opens 4 candidates; 54/200; mean 45.914 & Guard keeps correction local \\
no750 diagnostic & trace only & opens 3 positive + 1 neutral & Diagnostic only; not official full400 patch \\
Local correction on/off & full400 3-seed & 53.0 $\rightarrow$ 54.0 solved; mean 46.324 $\rightarrow$ 45.914 & Final boundary correction claim \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The boundary correction should be presented as a local repair mechanism. The official full400 patch uses `intervention_conflicts: [500, 750, 1000, 2000]` and `warmup_c1000_minus_warmup_c750_decisions`; it opens `3sat_188.cnf`, `3sat_196.cnf`, `3sat_46.cnf`, and neutral `3sat_66.cnf`. The no750 diagnostic opens neutral `3sat_183.cnf` instead, so it cannot be mixed with the official full400 result.

Sources:

- `docs/paper_ablation_matrix.md`
- `docs/local_boundary_correction_ablation.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/new_closed_old_on_local_reopen_gate_no750.md`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`
- `runs/analysis/new_closed_old_on_local_reopen_gate_no750_best_selection.csv`

## Figure 1: Portfolio Main Figure

Recommended title:

> Local5 -> CaDiCaL55 portfolio on 3SAT-400.

Caption:

> Portfolio and CaDiCaL repeat audit on 200 held-out 3SAT-400 instances. Left: the original CaDiCaL 60s run solves 75/200, but repeated CaDiCaL 60s runs solve 80/200, matching the best portfolio repeats. Right: original-run portfolio-only evidence split by source; within that portfolio-only split, repeated CaDiCaL reduces strict neural-first complement to one instance.

Recommended LaTeX:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=0.9\linewidth]{fig_portfolio_full400_paper.pdf}
\caption{Portfolio and CaDiCaL repeat audit on 200 held-out 3SAT-400 instances. Left: the original CaDiCaL 60s run solves 75/200, but repeated CaDiCaL 60s runs solve 80/200, matching the best portfolio repeats. Right: original-run portfolio-only evidence split by source; within that portfolio-only split, repeated CaDiCaL reduces strict neural-first complement to one instance.}
\label{fig:portfolio-main}
\end{figure}
```

Sources:

- `figures/fig_portfolio_full400_paper.pdf`
- `figures/fig_portfolio_full400_paper.svg`
- `figures/make_portfolio_results_paper.py`
- `runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv`
- `runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split_summary.csv`
- `runs/analysis/cadical_repeat_stability/repeat_summary.csv`

## Figure 2: Neural-Stage Cactus Plot

Recommended title:

> Neural-stage cactus plot on 3SAT-400 full400.

Caption:

> Neural-stage cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector recovers most of the One-shot timeout loss. Local Boundary Correction matches Old Compact solved count and further reduces mean time by repairing a small set of guarded boundary cases. This is a mechanism figure for the neural first stage, not the portfolio main result.

Paper-ready legend names:

1. One-shot
2. Old Compact
3. Online-Consistent Selector
4. Local Boundary Correction

Current figure check:

- Paper-ready figure: `figures/fig_full400_cactus_paper.pdf`
- Editable vector version: `figures/fig_full400_cactus_paper.svg`
- The older `figures/fig_local_reopen_guarded_full400_cactus.pdf` still uses lowercase/internal-style labels and should be treated as a diagnostic source figure.
- The older `figures/fig_online_consistent_boundary400_full400_cactus.pdf` includes Pairwise Veto and uses `boundary400`; use it only as a diagnostic or appendix figure unless relabeled.

Recommended LaTeX:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=0.78\linewidth]{figures/fig_full400_cactus_paper.pdf}
\caption{Neural-stage cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector recovers most of the One-shot timeout loss. Local Boundary Correction matches Old Compact solved count and further reduces mean time by repairing a small set of guarded boundary cases. This is a mechanism figure for the neural first stage, not the portfolio main result.}
\label{fig:full400-cactus}
\end{figure}
```

Sources:

- `figures/fig_full400_cactus_paper.pdf`
- `figures/fig_full400_cactus_paper.svg`
- `figures/make_full400_cactus_paper.py`
- `runs/analysis/local_reopen_guarded_full400_per_instance.csv`

## Optional Boundary Audit Table

Caption:

> Open set of the official guarded boundary correction on full400. This is the formal 750-feature patch, not the no750 diagnostic.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Open set of the official guarded boundary correction on full400. This is the formal 750-feature patch, not the no750 diagnostic.}
\label{tab:boundary-open-set}
\begin{tabular}{lrrrl}
\toprule
Instance & Online (s) & +Correction (s) & $\Delta$ (s) & Class \\
\midrule
3sat\_188.cnf & 25.630 & 25.731 & +0.102 & positive / recovered-timeout region \\
3sat\_196.cnf & 26.116 & 9.622 & -16.494 & hard speedup \\
3sat\_46.cnf & 29.837 & 0.526 & -29.311 & hard speedup \\
3sat\_66.cnf & 60.827 & 60.435 & -0.393 & neutral timeout \\
\bottomrule
\end{tabular}
\end{table}
```

Use this table only if the paper needs a compact audit of the local boundary correction. Otherwise keep it for appendix.

Sources:

- `docs/local_reopen_guarded_full400_eval.md`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`

## Appendix Table: Repeated Runtime Audit

Caption:

> Same-seed repeated runtime audit for the key recovered-timeout and guarded boundary-correction claims. This audit repeats only the fixed key instances and does not test seed sensitivity.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Same-seed repeated runtime audit for the key recovered-timeout and guarded boundary-correction claims. This audit repeats only the fixed key instances and does not test seed sensitivity.}
\label{tab:repeated-runtime-audit}
\begin{tabular}{llll}
\toprule
Instance & Comparison & Stable? & Interpretation \\
\midrule
3sat\_163.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_188.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_189.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_85.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_89.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_97.cnf & One-shot vs Online-Consistent Selector & yes & recovered timeout stable \\
3sat\_188.cnf & Online-Consistent Selector vs + Local Boundary Correction & mixed & boundary-sensitive \\
3sat\_196.cnf & Online-Consistent Selector vs + Local Boundary Correction & yes & stable hard speedup \\
3sat\_46.cnf & Online-Consistent Selector vs + Local Boundary Correction & yes & stable hard speedup \\
3sat\_66.cnf & Online-Consistent Selector vs + Local Boundary Correction & yes & neutral timeout evidence \\
\bottomrule
\end{tabular}
\end{table}
```

Paper wording:

same-seed repeated runtime audit supports all six recovered timeouts. `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups. `3sat_188.cnf` is boundary-sensitive. `3sat_66.cnf` remains neutral timeout evidence.

Use this as an appendix table or short stability-caption note. Do not merge it into the main full400 result table.

Sources:

- `docs/repeated_runtime_audit.md`
- `runs/analysis/repeated_runtime_audit.csv`
- `runs/analysis/repeated_runtime_audit/raw/`

## Appendix Table: 300/350 Generality Check

Caption:

> Appendix generality check on smaller held-out 3SAT sizes. These runs compare only One-shot and Online-Consistent Selector; Local Boundary Correction is not applied to 300/350.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Appendix generality check on smaller held-out 3SAT sizes. These runs compare only One-shot and Online-Consistent Selector; Local Boundary Correction is not applied to 300/350.}
\label{tab:appendix-300350}
\begin{tabular}{llrrrr}
\toprule
Size & Method & Solved & Mean time (s) & Median time (s) & $\Delta$ mean vs. One-shot (s) \\
\midrule
300 & One-shot & 200 & 15.311 & 14.099 & 0.000 \\
300 & Online-Consistent Selector & 200 & 7.272 & 6.061 & -8.039 \\
350 & One-shot & 108 & 43.741 & 57.104 & 0.000 \\
350 & Online-Consistent Selector & 109 & 33.815 & 40.065 & -9.925 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

Appendix 300/350 results show the final Online-Consistent Selector does not collapse on smaller held-out sizes: it preserves solved count on 300 and improves solved count by one instance on 350 while reducing mean time in both cases. These runs are a generality check only and do not include Local Boundary Correction.

Sources:

- `docs/paper_appendix_300350_eval.md`
- `runs/analysis/appendix_300350/summary.csv`
- `runs/analysis/appendix_300350/raw/one_shot_300.csv`
- `runs/analysis/appendix_300350/raw/one_shot_350.csv`
- `runs/analysis/appendix_300350/raw/online_consistent_300.csv`
- `runs/analysis/appendix_300350/raw/online_consistent_350.csv`

## Appendix Table: Generalization / Baseline Robustness

Caption:

> Generalization and baseline robustness across held-out 3SAT sizes. The 300/350 rows are single-run appendix checks under the frozen protocol. The 400 neural rows are neural-stage 3-seed solver robustness results. Local Boundary Correction is only evaluated on the 400-boundary setting.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Generalization and baseline robustness across held-out 3SAT sizes. The 300/350 rows are single-run appendix checks under the frozen protocol. The 400 neural rows are neural-stage 3-seed solver robustness results. Local Boundary Correction is only evaluated on the 400-boundary setting.}
\label{tab:generalization-baseline}
\begin{tabular}{llrrr}
\toprule
Size & Method & Solved & Mean time (s) & Median time (s) \\
\midrule
300 & Glucose default & 197 & 20.222 & 18.630 \\
300 & One-shot & 200 & 15.311 & 14.099 \\
300 & Online-Consistent Selector & 200 & 7.272 & 6.061 \\
300 & Old Compact & 200 & 8.907 & 7.597 \\
350 & Glucose default & 73 & 47.453 & 60.000 \\
350 & One-shot & 108 & 43.741 & 57.104 \\
350 & Online-Consistent Selector & 109 & 33.815 & 40.065 \\
350 & Old Compact & 103 & 34.918 & 46.533 \\
400 & Glucose default & 13 & 57.615 & 60.000 \\
400 & CaDiCaL default & 75 & 42.924 & 60.000 \\
400 & One-shot & 48.0 & 47.665 & 60.289 \\
400 & Online-Consistent Selector & 53.0 & 46.324 & 60.366 \\
400 & Old Compact & 54.0 & 46.278 & 60.373 \\
400 & + Local Boundary Correction & 54.0 & 45.914 & 60.369 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

This table broadens the evidence without changing the model. Online-Consistent Selector does not collapse on 300/350: it preserves solved count on 300 and improves solved count over One-shot and Old Compact on 350 under the frozen single-run appendix protocol. Glucose default and CaDiCaL default are unguided CDCL references, not neural baselines. CaDiCaL default is stronger than the neural-guided Glucose workflow on full400, so the paper should not claim dominance over modern CDCL defaults. Local Boundary Correction remains 400-only because the formal guarded rule is tied to the 400 candidate manifest.

Sources:

- `docs/paper_generalization_baseline_table.md`
- `runs/analysis/generalization_baseline/paper_table.csv`
- `runs/analysis/generalization_baseline/summary.csv`
- `runs/glucose/solver_stats_300_cpu60.csv`
- `runs/glucose/solver_stats_350_cpu60.csv`
- `runs/glucose/solver_stats_full400_cpu60.csv`
- `docs/cadical_default_full400_eval.md`
- `runs/cadical/solver_stats_full400_cpu60.csv`
- `runs/analysis/cadical_default_full400_summary.csv`
- `runs/analysis/cadical_default_full400_comparison.csv`
