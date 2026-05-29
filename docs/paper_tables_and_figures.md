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
| `online_consistent_boundary400` | Online-Consistent Selector | main selector |
| `local_reopen_guarded` | + Local Boundary Correction | boundary correction ablation |
| `pairwise_veto` / `pairwise_veto_actual` | Pairwise Veto | negative branch |

固定口径：

- Online-Consistent Selector 是主线 selector。
- + Local Boundary Correction 只作为 ablation，不作为新主模型。
- 正式 + Local Boundary Correction full400 patch 是含 750 特征版本。
- no750 只作为 diagnostic feature ablation；它的 open set 与正式 full400 patch 不同，不能替代正式结果。

## Table 1: Full400 Main Results

Caption:

> Full400 solver-seed robustness results on 200 held-out 3SAT-400 instances. Values are means over Glucose seeds 1, 2, and 3. One-shot is the neural guidance baseline without feedback refinement. Online-Consistent Selector is the main selector. + Local Boundary Correction is a guarded boundary correction ablation, not a separate main model.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Full400 solver-seed robustness results on 200 held-out 3SAT-400 instances. Values are means over Glucose seeds 1, 2, and 3. One-shot is the neural guidance baseline without feedback refinement. Online-Consistent Selector is the main selector. + Local Boundary Correction is a guarded boundary correction ablation, not a separate main model.}
\label{tab:full400-main}
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

Online-Consistent Selector is stable over One-shot across seeds 1/2/3, improving solved count from 48/200 to 53/200. Old Compact remains a strong matched baseline at 54/200. + Local Boundary Correction matches Old Compact solved count and gives the lowest mean time, so its role remains guarded boundary repair rather than an unrestricted main-model upgrade.

Sources:

- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_seed_robustness/method_summary.csv`
- `runs/analysis/full400_seed_robustness/seed_summary.csv`
- `runs/analysis/full400_seed_robustness/per_instance_summary.csv`

Historical single-run sources remain useful context but should not be the main table:

- `docs/online_consistent_boundary400_full400_eval.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/compact_risk_full400_eval.md`

## Table 2: Stability Validation

Caption:

> Full400 runtime and solver-seed robustness. Same-seed repeats use three full400 reruns with the default seed. Solver-seed robustness uses Glucose seeds 1, 2, and 3. The model, thresholds, and Local Boundary Correction guard are unchanged.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Full400 runtime and solver-seed robustness. Same-seed repeats use three full400 reruns with the default seed. Solver-seed robustness uses Glucose seeds 1, 2, and 3. The model, thresholds, and Local Boundary Correction guard are unchanged.}
\label{tab:full400-stability}
\begin{tabular}{lrrrr}
\toprule
Method & Repeat solved & Seed solved & Seed solved std & Seed mean time (s) \\
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

The stability analysis supports the same interpretation as the main full400 table. Online-Consistent Selector is stable over One-shot, Old Compact remains the strongest uncorrected reference in solved count, and + Local Boundary Correction matches Old Compact solved count while giving the lowest mean time. The older bootstrap / repeated-split table remains useful historical single-run evidence but should not replace the full400 repeated and seed-robustness results.

Sources:

- `docs/full400_repeated_runtime.md`
- `docs/full400_seed_robustness.md`
- `runs/analysis/full400_repeated_runtime/summary.csv`
- `runs/analysis/full400_seed_robustness/method_summary.csv`

## Table 3: Ablation Matrix

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

## Figure 1: Full400 Cactus Plot

Recommended title:

> Cactus plot on 3SAT-400 full400.

Caption:

> Cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector recovers most of the One-shot timeout loss. Local Boundary Correction matches Old Compact solved count and further reduces mean time by repairing a small set of guarded boundary cases.

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
\caption{Cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector recovers most of the One-shot timeout loss. Local Boundary Correction matches Old Compact solved count and further reduces mean time by repairing a small set of guarded boundary cases.}
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

> Generalization and baseline robustness across held-out 3SAT sizes. The 300/350 rows are single-run appendix checks under the frozen protocol. The 400 neural rows are the main 3-seed solver robustness results. Local Boundary Correction is only evaluated on the 400-boundary setting.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Generalization and baseline robustness across held-out 3SAT sizes. The 300/350 rows are single-run appendix checks under the frozen protocol. The 400 neural rows are the main 3-seed solver robustness results. Local Boundary Correction is only evaluated on the 400-boundary setting.}
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
