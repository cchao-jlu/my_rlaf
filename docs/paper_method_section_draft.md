# 论文方法章节草稿

> 本文档整理可直接改写进论文正文的方法章节。
> 方法叙事只保留 Online-Consistent Selector 主线和 Local Boundary Correction ablation。
> `polarity / SBE / pairwise veto / no750` 不写成方法贡献，只在实验消融或讨论中出现。

## 3 Method

### 3.1 Overview

We study how to use neural guidance inside a CDCL SAT solver without turning every branching decision into a neural inference call. The key design is to keep neural intervention sparse and evidence-driven. The solver first obtains a one-shot neural guidance prior, then runs a short warmup rollout to collect event traces from the actual CDCL trajectory. These traces are converted into event-conditioned solver states and graph-level selector features. A conservative Online-Consistent Selector decides whether the solver should continue with the neural adapter or fall back to the safer one-shot guidance path. Finally, a guarded Local Boundary Correction can reopen a small set of over-conservative boundary cases.

The inference pipeline is:

1. Run the GNN once to produce the one-shot neural guidance prior.
2. Run a low-budget warmup rollout under this prior and collect CDCL event statistics.
3. Encode solver events as variable-level event states and graph-level selector features.
4. Apply the Online-Consistent Selector to decide whether to enable the event adapter.
5. Optionally apply Local Boundary Correction on guarded `new_closed_old_on` candidates.
6. Run the final CDCL solve with either the base one-shot guidance or the selected adapted guidance.

This design is intentionally conservative. The objective is not to maximize adapter usage. The objective is to recover hard or timeout instances when event evidence supports intervention, while avoiding lost solutions and avoidable slowdowns on already-solvable instances.

### 3.2 Problem Setup: SAT Guidance with a One-Shot Neural Prior

Given a CNF formula \(F\), the base neural solver encodes the formula as a bipartite literal-clause graph and predicts a variable-level guidance vector. In the implementation, this guidance is passed to a weighted CDCL solver as per-variable polarity and weight comments in the DIMACS input. The one-shot baseline therefore remains a neural guidance baseline: it uses a GNN prediction once before solving, but does not use feedback refinement after observing a solver trajectory.

Let \(g_\theta(F)\) denote the one-shot GNN prediction and \(S(F, g_\theta(F); B)\) denote running the CDCL solver with guidance \(g_\theta(F)\) under budget \(B\). A naive approach would repeatedly call the GNN throughout the solve. We avoid that. Instead, we use a small number of fixed warmup budgets to collect solver-side evidence, then make one intervention decision before the final solve.

### 3.3 Event-Conditioned Solver State

The warmup rollout records CDCL event statistics by enabling event collection in the solver. At the variable level, the solver exports counts such as:

- decision occurrences,
- propagation occurrences,
- conflict-literal occurrences,
- learnt-clause literal occurrences,
- variable activity.

The enhanced event state maps these raw counts into stable per-variable features. For each event type, the implementation uses log-scaled counts, rates, and ranks. This produces a variable-level event tensor attached to the graph before the event adapter is evaluated. In the full400 paper configuration, `event_state_features: enhanced` is used, which corresponds to the non-polarity event state. Polarity-specific event features exist as diagnostics but are not part of the final method story.

For a variable \(v\), let \(e_v\) denote the event-conditioned state extracted after warmup. The adapter receives the base variable embedding together with \(e_v\), and predicts a residual correction to the one-shot guidance. The event state can be updated with momentum across refinement rounds; in the final full400 configuration the pipeline uses one feedback round with `state_momentum = 0.5`.

### 3.4 Online-Consistent Selector

The selector addresses the central risk in neural feedback: the event adapter can help hard instances, but it can also slow down or lose instances that the one-shot path would already solve. Therefore, the selector operates at the instance level and decides whether the adapted branch should be used at all.

The final selector is online-consistent: its features are built from the same online warmup evidence available at inference time, rather than from stale or mismatched full400 caches. For each warmup point, the system extracts graph-level statistics such as decisions, propagations, CPU time, base guidance distribution summaries, event entropy, top-mass concentration, and correlations between the one-shot guidance and event activity. With multiple warmup conflict points, it also extracts drift features between neighboring points.

The selector is a conservative two-stage controller. It computes:

- \(p_{\mathrm{risk}}\): probability that using the adapter risks slowdown or lost solution;
- \(p_{\mathrm{recovery}}\): probability that using the adapter can recover a timeout or produce a hard-instance speedup;
- optionally \(p_{\mathrm{slowdown}}\): an auxiliary slowdown veto probability when available.

The main decision rule is:

\[
\texttt{use\_adapter}
= [p_{\mathrm{risk}} < \tau_{\mathrm{risk}}]
  \wedge [p_{\mathrm{recovery}} \ge \tau_{\mathrm{recovery}}].
\]

If a slowdown veto head is present, the selector additionally requires:

\[
p_{\mathrm{slowdown}} < \tau_{\mathrm{slowdown}}.
\]

This form makes the paper claim precise: the selector is not a generic accuracy-maximizing classifier. It is a risk controller whose first responsibility is to avoid unsafe adapter activation, then recover hard or timeout cases when evidence is strong enough.

### 3.5 Conservative Risk-Controlled Intervention

Training uses same-evidence counterfactual traces. The system first runs a warmup rollout under the same one-shot guidance and collects event evidence. It then evaluates two branches from this shared evidence:

- a base branch that continues with the one-shot guidance path;
- an adapter branch that applies event-conditioned neural correction.

Because the current Glucose wrapper cannot serialize and restore the full internal CDCL trail and clause database, these are same-evidence branch counterfactuals rather than exact in-process CDCL clone continuations. This distinction should be stated explicitly in the method or experiment setup to avoid overclaiming.

Training labels separate positive, negative, neutral, and warmup-solved cases. Positive cases include recovered timeouts and hard speedups. Negative cases include lost solutions, easy slowdowns, and general slowdowns. Neutral cases do not provide strong evidence for either branch. The two-stage selector is then trained so that risk and recovery are modeled separately:

- the risk head learns when adapter activation is unsafe;
- the recovery head learns when adapter activation has meaningful upside.

At inference time, only the selected branch is executed in the final solve. The selector therefore reduces runtime risk without requiring both final branches to be run.

### 3.6 Local Boundary Correction

The Online-Consistent Selector is intentionally conservative, which creates a specific failure mode: it can close adapter branches that old compact or counterfactual traces indicate were useful. These cases are the `new_closed_old_on` boundary: the new selector closes a branch that an earlier selector opened.

Local Boundary Correction is a guarded repair for this narrow failure mode. It is not a new global model. It only triggers when an instance is present in a candidate manifest, and then satisfies a small rule over warmup features. The formal full400 patch uses the 750-feature version:

- `local_reopen_candidate >= 1`
- `warmup_c1000_minus_warmup_c750_decisions >= 294`
- `warmup_c2000_rho_event_corr >= 0.0365`

The candidate guard is essential. It prevents the local rule from becoming a global threshold sweep over the full test set. If an instance is not in the candidate manifest, Local Boundary Correction cannot open it even if the numerical feature thresholds are satisfied.

In notation, let \(m(F)\) indicate membership in the candidate manifest and \(r(F)\) indicate the local reopen rule. The final adapter decision is:

\[
\texttt{use\_adapter\_final}
= \texttt{use\_adapter}
  \vee
  \left(\neg \texttt{use\_adapter} \wedge m(F) \wedge r(F)\right).
\]

The paper should describe this as a boundary correction ablation. On full400 it does not increase solved count; it reduces mean time by reopening a few over-conservative boundary cases.

The no750 version is only diagnostic. It shows that the boundary signal is not entirely dependent on the 750-conflict point, but it opens a different neutral instance and has not replaced the official full400 patch.

### 3.7 Training and Trace Generation Overview

The training pipeline has three levels of evidence:

1. One-shot guidance predictions from the base GNN.
2. Warmup CDCL event traces collected under fixed conflict budgets.
3. Same-evidence base-vs-adapter branch outcomes used to label selector examples.

For each formula, the trace generator runs warmup probes at configured conflict budgets. In the full400 local correction setting, the final guarded patch uses `[500, 750, 1000, 2000]` conflict points. For each point, the solver returns both aggregate statistics and variable-level event traces. These are attached to the graph as event states and also summarized as selector features.

The training target is not simply “adapter faster than base.” It distinguishes between:

- recovered timeout,
- hard speedup,
- lost solution,
- easy slowdown,
- slowdown,
- neutral,
- warmup solved.

This label structure supports a conservative intervention policy. The recovery head focuses on recovered timeout and hard-speedup evidence, while the risk head learns to suppress adapter activation on lost-solution and slowdown patterns.

### 3.8 Inference-Time Workflow

Algorithm 1 summarizes the inference workflow.

```latex
\begin{algorithm}[t]
\caption{Online-consistent event-conditioned guidance}
\label{alg:online-consistent-guidance}
\begin{algorithmic}[1]
\Require CNF formula $F$, base GNN $g_\theta$, CDCL solver $S$, selector $q_\phi$
\State $w_0 \gets g_\theta(F)$ \Comment{one-shot neural guidance prior}
\For{each configured intervention point $b \in \mathcal{B}$}
    \State Collect a cumulative warmup probe under $w_0$ up to conflict budget $b$
    \State Encode the resulting CDCL event trace $E_b$ as variable event state and graph-level selector features
\EndFor
\State Compute $p_{\mathrm{risk}}, p_{\mathrm{recovery}}$ from online warmup features
\State $u \gets [p_{\mathrm{risk}} < \tau_{\mathrm{risk}}] \wedge [p_{\mathrm{recovery}} \ge \tau_{\mathrm{recovery}}]$
\If{candidate manifest contains $F$ and local boundary rule is satisfied}
    \State $u \gets \mathrm{true}$ \Comment{guarded local boundary correction}
\EndIf
\If{$u$}
    \State $w \gets$ event-conditioned adapter guidance
\Else
    \State $w \gets w_0$
\EndIf
\State Run final CDCL solve $S(F, w)$ under the full time budget
\end{algorithmic}
\end{algorithm}
```

The key property is that neural calls are low frequency. The method does not call a GNN at every branching decision. It performs one base prediction, a small number of warmup probes to gather event evidence, one selector decision, and one final guided solve.

### 3.9 Contribution Wording

The paper contribution list should stay narrow:

1. We propose an event-conditioned online selector that uses real CDCL event traces to decide whether neural feedback should be activated.
2. We introduce conservative risk control for neural SAT guidance, separating recovery potential from slowdown and lost-solution risk.
3. We present guarded local boundary correction, a constrained repair mechanism for over-conservative selector errors.

The following should not be phrased as contributions:

- no750 diagnostic,
- polarity / SBE branches,
- pairwise veto,
- compact stable.

They belong in ablations or negative-results discussion.

### 3.10 Method Claims to Avoid

Avoid these claims in the paper:

- Do not claim the method frequently calls the GNN during CDCL branching.
- Do not claim Local Boundary Correction is a new main model.
- Do not claim no750 is the final full400 patch.
- Do not imply the counterfactual branch labels are exact CDCL state clone continuations.
- Do not frame polarity, SBE, or pairwise veto as successful method components.

The strongest defensible method claim is narrower and cleaner: low-frequency CDCL event traces provide enough online evidence for a conservative selector to decide when neural feedback should be used, and a guarded local correction can repair a small number of over-conservative boundary decisions.
