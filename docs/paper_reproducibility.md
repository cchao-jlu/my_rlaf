# Paper Reproducibility Package

> Scope: minimal reproducibility map for the current paper experiment package.
> This document does not introduce new model lines. It records how to regenerate
> the paper-ready tables and figures from frozen artifacts, and what is still an
> external artifact.

## Environment

Use the project conda environment:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python
```

Build solver binaries before rerunning evaluations:

```bash
bash build_solvers.sh
```

The relevant unguided solver binary is:

```text
solvers/glucose/simp/glucose_static
```

Guided runs use the weighted solver through `evaluate_guided_solver.py` when
model guidance is present.

## Paper Tables and Figures

The paper-ready LaTeX tables and figure captions are collected in:

```text
docs/paper_tables_and_figures.md
```

The per-item artifact audit is collected in:

```text
docs/paper_artifact_manifest.md
```

Required paper outputs:

| Output | Source artifact |
| --- | --- |
| Table 1: Full400 main results | `runs/analysis/online_consistent_boundary400_full400_summary.csv`, `runs/analysis/local_reopen_guarded_full400_summary.csv`, tracked raw full400 CSVs listed below |
| Figure 1: Full400 cactus | `figures/fig_full400_cactus_paper.pdf`, `figures/fig_full400_cactus_paper.svg` |
| Table 2: Stability validation | `runs/analysis/online_consistent_boundary400_stability.csv` |
| Table 3: Ablation matrix | `docs/paper_ablation_matrix.md` |
| Appendix: repeated runtime audit | `docs/repeated_runtime_audit.md`, `runs/analysis/repeated_runtime_audit.csv`, `runs/analysis/repeated_runtime_audit/raw/` |
| Appendix: 300/350 generality check | `docs/paper_appendix_300350_eval.md`, `runs/analysis/appendix_300350/summary.csv`, `runs/analysis/appendix_300350/raw/` |
| Appendix: generalization / baseline robustness | `docs/paper_generalization_baseline_table.md`, `runs/analysis/generalization_baseline/paper_table.csv`, `runs/analysis/generalization_baseline/summary.csv` |
| Optional Glucose default baseline | `runs/analysis/glucose_default_full400_summary.csv`, `docs/glucose_default_full400_eval.md` |
| Optional CaDiCaL default baseline | `runs/analysis/cadical_default_full400_summary.csv`, `docs/cadical_default_full400_eval.md` |
| Optional boundary audit | `runs/analysis/local_reopen_guarded_full400_open_set.csv` |

The paper method names are fixed in `docs/paper_tables_and_figures.md`. In
particular, `online_consistent_boundary400` is written as Online-Consistent
Selector, and `local_reopen_guarded` is written as + Local Boundary Correction
only as an ablation.

Historical evaluation notes such as compact-risk markdown files are useful
context, but the minimal paper reproducibility package treats the tracked CSVs
and paper docs above as the authoritative inputs.

## Claim Consistency Gate

Before editing or submitting the paper, run the claim verifier:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python verify_paper_claims.py
```

The verifier checks that `paper/main.tex` and `docs/paper_tables_and_figures.md`
remain consistent with the frozen CSV evidence:

- portfolio repeats: `79, 80, 80`;
- repeated CaDiCaL 60s: `75, 80, 80`;
- matched deltas: `+4, 0, 0`;
- neural-stage counts: One-shot `48`, Online `53`, Old Compact `54`, Local
  Boundary Correction `54`;
- repeated-CaDiCaL overlap: Local/CaDiCaL strict complement `3`,
  Online/CaDiCaL strict complement `2`, Local-only boundary contribution `1`;
- stale historical single-run claims such as `50/200`, `56/200`,
  `47.752`, `46.222`, and `45.498` are absent from `paper/main.tex`;
- forbidden positive claims such as robust CaDiCaL dominance are absent.

This gate is intentionally narrow: it checks paper-claim consistency, not
whether the project has achieved a top-conference result.

## Regenerate From Frozen CSV Artifacts

Regenerate the Online-Consistent full400 summary and per-instance tables:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_online_consistent_boundary400_eval.py
```

Inputs:

```text
runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_full400.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch0.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch1.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch2.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch3.csv
runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv
```

Outputs:

```text
runs/analysis/online_consistent_boundary400_full400_actual_batched.csv
runs/analysis/online_consistent_boundary400_full400_summary.csv
runs/analysis/online_consistent_boundary400_full400_per_instance.csv
runs/analysis/online_consistent_boundary400_full400_bucket_summary.csv
runs/analysis/online_consistent_boundary400_full400_largest_changes.csv
```

Regenerate the guarded Local Boundary Correction summary:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_local_reopen_guarded_full400_eval.py
```

Inputs:

```text
runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_full400.csv
runs/analysis/online_consistent_boundary400_full400_actual_batched.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/eval_local_reopen_guarded_full400.csv
runs/analysis/local_reopen_guarded_full400_guidance_audit.csv
runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv
```

Outputs:

```text
runs/analysis/local_reopen_guarded_full400_summary.csv
runs/analysis/local_reopen_guarded_full400_per_instance.csv
runs/analysis/local_reopen_guarded_full400_bucket_summary.csv
runs/analysis/local_reopen_guarded_full400_largest_changes.csv
runs/analysis/local_reopen_guarded_full400_open_set.csv
figures/fig_local_reopen_guarded_full400_cactus.pdf
figures/fig_local_reopen_guarded_full400_cactus.svg
```

Regenerate the stability table:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_online_consistent_boundary400_stability.py
```

Input:

```text
runs/analysis/local_reopen_guarded_full400_per_instance.csv
```

Output:

```text
runs/analysis/online_consistent_boundary400_stability.csv
```

Regenerate the paper-ready cactus figure:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python figures/make_full400_cactus_paper.py
```

Inputs:

```text
runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_full400.csv
runs/analysis/online_consistent_boundary400_full400_actual_batched.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/eval_local_reopen_guarded_full400.csv
```

Outputs:

```text
figures/fig_full400_cactus_paper.pdf
figures/fig_full400_cactus_paper.svg
```

## Glucose Default Baseline

The unguided solver-default baseline uses a nominal 60s Glucose budget and a 65s
external wall-clock guard:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_glucose_default_full400_cpu60.py \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/glucose/solver_stats_full400_cpu60.csv \
  --cpu-lim 60 \
  --timeout 65 \
  --workers 8
```

Summary source:

```text
docs/glucose_default_full400_eval.md
runs/glucose/solver_stats_300_cpu60.csv
runs/glucose/solver_stats_350_cpu60.csv
runs/glucose/solver_stats_full400_cpu60.csv
runs/analysis/glucose_default_full400_summary.csv
```

Interpretation: this is an unguided CDCL reference. It should not replace
One-shot, which is the neural guidance baseline.

## Generalization / Baseline Robustness Appendix

The generalization / baseline robustness table combines:

- Glucose default on 300/350/400;
- CaDiCaL default on 400;
- One-shot and Online-Consistent Selector 300/350 appendix runs;
- matched Old Compact 300/350 reruns;
- full400 3-seed robustness rows for the neural methods.

Regenerate the combined table:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_generalization_baseline.py
```

Inputs:

```text
runs/glucose/solver_stats_300_cpu60.csv
runs/glucose/solver_stats_350_cpu60.csv
runs/glucose/solver_stats_full400_cpu60.csv
runs/cadical/solver_stats_full400_cpu60.csv
runs/analysis/cadical_default_full400_summary.csv
runs/analysis/cadical_default_full400_comparison.csv
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
runs/analysis/generalization_baseline/raw/old_compact_300.csv
runs/analysis/generalization_baseline/raw/old_compact_350.csv
runs/analysis/full400_seed_robustness/method_summary.csv
```

Outputs:

```text
docs/paper_generalization_baseline_table.md
runs/analysis/generalization_baseline/audit.csv
runs/analysis/generalization_baseline/summary.csv
runs/analysis/generalization_baseline/paper_table.csv
```

Interpretation: 300/350 rows are appendix single-run checks; full400 neural
rows are the main 3-seed robustness results. CaDiCaL default is a strong
unguided CDCL reference and should not be mixed with neural-guided Glucose
workflow rows. Local Boundary Correction is not applied to 300/350.

## CaDiCaL Default Baseline

The stronger unguided CDCL reference uses CaDiCaL 1.5.2 with a 60s wall-clock
limit:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_cadical_default_full400_cpu60.py \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/cadical/solver_stats_full400_cpu60.csv \
  --limit 60 \
  --timeout 65 \
  --workers 8
```

Summary source:

```text
docs/cadical_default_full400_eval.md
runs/cadical/solver_stats_full400_cpu60.csv
runs/cadical/solver_stats_full400_cpu60_repeat1.csv
runs/cadical/solver_stats_full400_cpu60_repeat2.csv
runs/analysis/cadical_repeat_stability/repeat_summary.csv
runs/analysis/cadical_repeat_stability/instance_summary.csv
runs/analysis/cadical_repeated_neural_overlap/summary.csv
```

Interpretation: repeated CaDiCaL 60s runs solve `75, 80, 80` on full400.
This constrains the paper claim: the Local5 -> CaDiCaL55 portfolio is
boundary-sensitive complementarity evidence, not a robust solved-count win over
CaDiCaL.

## Stronger External CDCL Solver Gate

This is a gate for top-conference baseline strength. It does not change the
neural model, selector, thresholds, Local Boundary Correction rule, or portfolio
schedule. Use it only after an external solver binary such as Kissat or MapleSAT
is available.

Current repository solver executables:

```text
solvers/cadical/cadical
solvers/glucose/simp/glucose_static
solvers/glucose_weighted/simp/glucose_static
solvers/march/march_nh
solvers/march_weighted/march_nh
```

There is no tracked Kissat / MapleSAT / CryptoMiniSat binary at the time of this
audit. Put external binaries under a non-committed artifact path, for example:

```text
external_solvers/kissat/kissat
external_solvers/maple/maplesat
```

Smoke-test an external solver on 5 full400 instances:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_external_solver_baseline.py \
  --solver external_solvers/kissat/kissat \
  --solver-name kissat \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/external_solvers/kissat_full400_cpu60_smoke.csv \
  --limit 60 \
  --timeout 65 \
  --workers 1 \
  --n 5 \
  --cmd-template '{solver} {file}'
```

Run full400 repeat 0 after smoke passes:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_external_solver_baseline.py \
  --solver external_solvers/kissat/kissat \
  --solver-name kissat \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/external_solvers/kissat_full400_cpu60.csv \
  --limit 60 \
  --timeout 65 \
  --workers 8 \
  --repeat 0 \
  --cmd-template '{solver} {file}'
```

For repeat 1 and repeat 2, rerun the same command with `--repeat 1` and
`--repeat 2`, using the same output CSV. Then summarize:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_external_solver_baseline.py \
  --input runs/external_solvers/kissat_full400_cpu60.csv \
  --output-dir runs/analysis/external_solvers/kissat_full400_cpu60
```

Some solvers require solver-specific timeout flags. Use `--cmd-template` for
those cases. Examples:

```text
CaDiCaL: '{solver} -q -t {limit} {file}'
generic external timeout only: '{solver} {file}'
```

Decision rule for paper use:

- If a stronger external solver solves at least as many instances as CaDiCaL and
  erases neural-only complementarity, the paper must remain a
  risk-control/failure-boundary paper.
- If Local/Online solve instances that a stronger external solver misses across
  repeated runs, then portfolio/complementarity framing becomes stronger.
- Do not tune the neural selector based on external-solver results; this gate is
  only a baseline robustness audit.
runs/cadical/solver_stats_full400_cpu60.csv
runs/analysis/cadical_default_full400_summary.csv
runs/analysis/cadical_default_full400_comparison.csv
```

Interpretation: CaDiCaL default is stronger than the neural-guided Glucose
workflow on full400 (`75/200` solved). It should be presented as a strong CDCL
reference, not as part of the neural-method main table.

## Repeated Runtime Appendix

The repeated runtime appendix is a same-seed key-claim audit. It checks the
six recovered-timeout instances and the four Local Boundary Correction open-set
instances. It is not a seed sensitivity study and should not be described as a
full repeated-run evaluation of Table 1.

Audit summary:

```text
docs/repeated_runtime_audit.md
runs/analysis/repeated_runtime_audit.csv
```

Raw repeat outputs:

```text
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat2.csv
```

Runner:

```text
run_repeated_runtime_audit.py
```

Interpretation:

- same-seed repeated runtime audit supports all six recovered timeouts.
- `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups.
- `3sat_188.cnf` is boundary-sensitive.
- `3sat_66.cnf` remains neutral timeout evidence.

## 300/350 Appendix Generality Check

The 300/350 appendix is a small generality check for the final
Online-Consistent Selector. It is not a main experiment, not a threshold-tuning
run, and does not apply Local Boundary Correction to 300/350.

Summary:

```text
docs/paper_appendix_300350_eval.md
runs/analysis/appendix_300350/summary.csv
```

Raw outputs:

```text
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
```

Interpretation: final Online-Consistent Selector does not collapse on smaller
held-out sizes. It preserves solved count on 300, improves solved count by one
on 350, and reduces mean time on both sizes. This does not change the main
3SAT-400 full400 claim.

## Raw Full400 Guided Evaluations

The paper tables can be regenerated from the frozen CSV artifacts above. Fully
rerunning the guided full400 evaluations additionally requires checkpoints and
the exact CNF datasets.

Known configs:

```text
configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml
configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml
```

Known checkpoints:

```text
runs/GNN_Glucose_3SAT_V1/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/best.pt
```

Known datasets / manifests:

```text
data/test/3sat/400/*.cnf
data/new_closed_old_on_boundary/3sat/400/*.cnf
data/new_closed_old_on_boundary/manifest.csv
```

The manifest CSV is tracked. The CNF datasets are treated as external data for
full reruns; they are not required to regenerate the paper tables from the
frozen CSV artifacts.

The formal Local Boundary Correction full400 run uses the 750-feature guarded
rule:

```text
intervention_conflicts: [500, 750, 1000, 2000]
local_reopen_candidate_manifest: data/new_closed_old_on_boundary/manifest.csv
```

The no750 results are diagnostic only and must not replace the formal full400
patch.

## Minimal Files To Keep Under Version Control

Paper docs and figures already committed:

```text
docs/paper_tables_and_figures.md
docs/paper_experiment_section_draft.md
docs/paper_method_section_draft.md
docs/paper_related_work_outline.md
docs/paper_intro_abstract_draft.md
docs/paper_ablation_matrix.md
docs/paper_stability_validation.md
figures/fig_full400_cactus_paper.pdf
figures/fig_full400_cactus_paper.svg
figures/make_full400_cactus_paper.py
```

Reproducibility addendum committed in `c7228bc`:

```text
docs/paper_reproducibility.md
docs/glucose_default_full400_eval.md
docs/paper_readiness_gap_audit.md
run_glucose_default_full400_cpu60.py
runs/glucose/solver_stats_full400_cpu60.csv
runs/analysis/glucose_default_full400_summary.csv
```

Guided-result package to keep under version control:

```text
configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml
configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml
summarize_online_consistent_boundary400_eval.py
summarize_local_reopen_guarded_full400_eval.py
summarize_online_consistent_boundary400_stability.py
runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_full400.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch0.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch1.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch2.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch3.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/eval_local_reopen_guarded_full400.csv
runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv
runs/analysis/local_reopen_guarded_full400_guidance_audit.csv
runs/analysis/online_consistent_boundary400_full400_summary.csv
runs/analysis/online_consistent_boundary400_full400_actual_batched.csv
runs/analysis/online_consistent_boundary400_full400_per_instance.csv
runs/analysis/local_reopen_guarded_full400_summary.csv
runs/analysis/local_reopen_guarded_full400_per_instance.csv
runs/analysis/local_reopen_guarded_full400_open_set.csv
runs/analysis/online_consistent_boundary400_stability.csv
data/new_closed_old_on_boundary/manifest.csv
```

These CSV artifacts are intentionally tracked so that the summary scripts and
paper cactus script can be rerun without rerunning checkpoint-dependent solver
evaluations.

The checkpoint files are about 20 MB each. Decide separately whether to track
them directly, store them with Git LFS, or publish them as external artifacts.

Repeated runtime audit package committed in `e51a5c7` and `3fa3063`:

```text
run_repeated_runtime_audit.py
docs/repeated_runtime_audit.md
runs/analysis/repeated_runtime_audit.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/local_reopen_guarded/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/local_open_set/online_consistent_boundary400/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/one_shot/repeat2.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat0.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat1.csv
runs/analysis/repeated_runtime_audit/raw/recovered_timeout/online_consistent_boundary400/repeat2.csv
```

300/350 appendix package committed in `7e4b785` and `fb73882`:

```text
docs/paper_appendix_300350_smoke.md
docs/paper_appendix_300350_eval.md
runs/analysis/appendix_300350/summary.csv
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
```
