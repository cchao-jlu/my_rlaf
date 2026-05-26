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

> Full400 wall-clock results on 200 held-out 3SAT-400 instances. One-shot is the neural guidance baseline without feedback refinement. Online-Consistent Selector is the main selector. + Local Boundary Correction is a guarded boundary correction ablation, not a separate main model.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Full400 wall-clock results on 200 held-out 3SAT-400 instances. One-shot is the neural guidance baseline without feedback refinement. Online-Consistent Selector is the main selector. + Local Boundary Correction is a guarded boundary correction ablation, not a separate main model.}
\label{tab:full400-main}
\begin{tabular}{lrrrr}
\toprule
Method & Solved & Mean time (s) & Median time (s) & $\Delta$ mean vs. One-shot (s) \\
\midrule
One-shot & 50 & 47.752 & 60.766 & 0.000 \\
Old Compact & 56 & 46.348 & 60.881 & -1.403 \\
Pairwise Veto & 52 & 46.876 & 60.959 & -0.876 \\
Online-Consistent Selector & 56 & 46.222 & 60.882 & -1.530 \\
+ Local Boundary Correction & 56 & 45.498 & 60.346 & -2.254 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

Online-Consistent Selector recovers the same six one-shot timeouts as Old Compact while slightly reducing mean wall-clock time. + Local Boundary Correction keeps the solved count unchanged but further reduces mean time, so its role is boundary repair rather than a main-model upgrade.

Sources:

- `docs/online_consistent_boundary400_full400_eval.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/compact_risk_full400_eval.md`
- `runs/analysis/online_consistent_boundary400_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_summary.csv`

## Table 2: Stability Validation

Caption:

> Paired bootstrap and repeated split stability on the final full400 per-instance results. All deltas are measured against One-shot. Bootstrap uses 2000 paired resamples; repeated split samples 100 instances without replacement for 2000 trials.

LaTeX:

```latex
\begin{table}[t]
\centering
\caption{Paired bootstrap and repeated split stability on the final full400 per-instance results. All deltas are measured against One-shot. Bootstrap uses 2000 paired resamples; repeated split samples 100 instances without replacement for 2000 trials.}
\label{tab:full400-stability}
\begin{tabular}{lrrrrr}
\toprule
Method & Solved & Mean time (s) & $\Delta$ mean (s) & Bootstrap 95\% CI & Split improve rate \\
\midrule
Old Compact & 56 & 46.348 & -1.403 & $[-2.729,\,-0.264]$ & 0.991 \\
Online-Consistent Selector & 56 & 46.222 & -1.530 & $[-2.823,\,-0.407]$ & 0.994 \\
+ Local Boundary Correction & 56 & 45.498 & -2.254 & $[-3.650,\,-1.068]$ & 1.000 \\
\bottomrule
\end{tabular}
\end{table}
```

Optional wider version with bootstrap improvement probability:

```latex
\begin{table}[t]
\centering
\caption{Stability validation on final full400 per-instance results.}
\label{tab:full400-stability-wide}
\begin{tabular}{lrrrrrr}
\toprule
Method & Solved & Mean (s) & $\Delta$ mean (s) & 95\% CI & Bootstrap $p_{\mathrm{improve}}$ & Split improve rate \\
\midrule
Old Compact & 56 & 46.348 & -1.403 & $[-2.729,\,-0.264]$ & 0.995 & 0.991 \\
Online-Consistent Selector & 56 & 46.222 & -1.530 & $[-2.823,\,-0.407]$ & 0.998 & 0.994 \\
+ Local Boundary Correction & 56 & 45.498 & -2.254 & $[-3.650,\,-1.068]$ & 1.000 & 1.000 \\
\bottomrule
\end{tabular}
\end{table}
```

Recommended text:

The stability analysis supports the same interpretation as the raw full400 results. Online-Consistent Selector is a stable improvement over One-shot, while + Local Boundary Correction mainly improves mean time rather than solved count.

Sources:

- `docs/paper_stability_validation.md`
- `runs/analysis/online_consistent_boundary400_stability.csv`

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
Candidate guard & full400 & opens 4 candidates; 56/200; mean 45.498 & Guard keeps correction local \\
no750 diagnostic & trace only & opens 3 positive + 1 neutral & Diagnostic only; not official full400 patch \\
Local correction on/off & full400 & 56/200; mean 46.222 $\rightarrow$ 45.498 & Final boundary correction claim \\
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

> Cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector preserves the timeout recovery of Old Compact while reducing mean time. Local Boundary Correction keeps the solved count unchanged and further reduces mean time by repairing a small set of guarded boundary cases.

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
\caption{Cactus plot over solved instances on the full 3SAT-400 test set. Curves sort solved instances by wall-clock solving time. Online-Consistent Selector preserves the timeout recovery of Old Compact while reducing mean time. Local Boundary Correction keeps the solved count unchanged and further reduces mean time by repairing a small set of guarded boundary cases.}
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
