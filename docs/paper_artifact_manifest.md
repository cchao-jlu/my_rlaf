# Paper Artifact Manifest

> Scope: git-tracked artifact manifest for the current paper package. This
> manifest covers table/figure reproduction from frozen artifacts. It does not
> add new experiments or change model/config choices.

## Summary

The frozen CSV, paper figure, summary scripts, guided eval configs, repeated
runtime audit artifacts, and boundary manifest needed for the current paper
tables are tracked in git.

Checkpoints and CNF datasets are external artifacts for full solver reruns:

```text
runs/GNN_Glucose_3SAT_V1/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/best.pt
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/best.pt
data/test/3sat/400/*.cnf
data/new_closed_old_on_boundary/3sat/400/*.cnf
```

`data/new_closed_old_on_boundary/manifest.csv` is tracked because it is part of
the formal guarded Local Boundary Correction rule.

## Table And Figure Items

| Paper item | Source CSV / figure artifact | Script / config | Committed? | External artifact? |
| --- | --- | --- | --- | --- |
| Table 1: Full400 main results | `runs/analysis/online_consistent_boundary400_full400_summary.csv`; `runs/analysis/local_reopen_guarded_full400_summary.csv`; raw one-shot / old compact / online-consistent / local-correction full400 CSVs under `runs/GNN_*` | `summarize_online_consistent_boundary400_eval.py`; `summarize_local_reopen_guarded_full400_eval.py`; guided eval configs listed below | Yes | Checkpoints and CNF datasets only for full rerun |
| Figure 1: Full400 cactus | `figures/fig_full400_cactus_paper.pdf`; `figures/fig_full400_cactus_paper.svg`; raw full400 CSVs used by the plotting script | `figures/make_full400_cactus_paper.py` | Yes | Checkpoints and CNF datasets only for full rerun |
| Table 2: Stability validation | `runs/analysis/online_consistent_boundary400_stability.csv`; `runs/analysis/local_reopen_guarded_full400_per_instance.csv` | `summarize_online_consistent_boundary400_stability.py` | Yes | No for frozen-table regeneration |
| Table 3: Ablation matrix | `docs/paper_ablation_matrix.md` | Manual paper table from frozen ablation docs/results | Yes | No for paper table; historical failed-branch artifacts are not required |
| Appendix: repeated runtime audit | `docs/repeated_runtime_audit.md`; `runs/analysis/repeated_runtime_audit.csv`; 12 raw repeat CSVs under `runs/analysis/repeated_runtime_audit/raw/` | `run_repeated_runtime_audit.py` | Yes | Checkpoints and CNF datasets only to rerun the audit |
| Appendix: 300/350 generality check | `docs/paper_appendix_300350_eval.md`; `runs/analysis/appendix_300350/summary.csv`; four raw CSVs under `runs/analysis/appendix_300350/raw/` | direct `evaluate_guided_solver.py` runs from `docs/paper_appendix_300350_eval.md`; no Local Boundary Correction | Yes | Checkpoints and 300/350 CNF datasets only for rerun |
| Appendix: generalization / baseline robustness | `docs/paper_generalization_baseline_table.md`; `runs/analysis/generalization_baseline/paper_table.csv`; `runs/analysis/generalization_baseline/summary.csv`; `runs/glucose/solver_stats_300_cpu60.csv`; `runs/glucose/solver_stats_350_cpu60.csv`; matched Old Compact 300/350 raw CSVs | `summarize_generalization_baseline.py`; `run_glucose_default_full400_cpu60.py`; direct matched `evaluate_guided_solver.py` Old Compact reruns | Yes | Checkpoints and CNF datasets only to rerun guided rows |
| Optional appendix: Glucose default baseline | `runs/glucose/solver_stats_full400_cpu60.csv`; `runs/analysis/glucose_default_full400_summary.csv`; `docs/glucose_default_full400_eval.md` | `run_glucose_default_full400_cpu60.py` | Yes | CNF dataset only for rerun |
| Optional appendix: CaDiCaL default baseline | `runs/cadical/solver_stats_full400_cpu60.csv`; `runs/analysis/cadical_default_full400_summary.csv`; `runs/analysis/cadical_default_full400_comparison.csv`; `docs/cadical_default_full400_eval.md` | `run_cadical_default_full400_cpu60.py` | Yes | CNF dataset only for rerun |
| Stronger-CDCL gate: external solver baseline | `runs/external_solvers/<solver>_full400_cpu60.csv`; `runs/analysis/external_solvers/<solver>_full400_cpu60/{repeat_summary,aggregate,instance_summary}.csv` after a binary is provided | `run_external_solver_baseline.py`; `summarize_external_solver_baseline.py` | Runner: Yes; solver binary/results: No until provided | External Kissat/MapleSAT/CryptoMiniSat binary plus CNF dataset |
| Optional appendix: boundary open-set audit | `runs/analysis/local_reopen_guarded_full400_open_set.csv`; `runs/analysis/local_reopen_guarded_full400_guidance_audit.csv`; `data/new_closed_old_on_boundary/manifest.csv` | `summarize_local_reopen_guarded_full400_eval.py`; `configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml` | Yes | Checkpoints and CNF datasets only for full rerun |

## Tracked Guided Result Inputs

```text
runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_full400.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch0.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch1.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch2.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/eval_online_consistent_boundary400_full400_batch3.csv
runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/eval_local_reopen_guarded_full400.csv
runs/analysis/positive_floor_pairwise_slowdown_veto_full400_actual_batched.csv
```

## Tracked Derived Analysis CSVs

```text
runs/analysis/online_consistent_boundary400_full400_actual_batched.csv
runs/analysis/online_consistent_boundary400_full400_summary.csv
runs/analysis/online_consistent_boundary400_full400_per_instance.csv
runs/analysis/local_reopen_guarded_full400_summary.csv
runs/analysis/local_reopen_guarded_full400_per_instance.csv
runs/analysis/local_reopen_guarded_full400_open_set.csv
runs/analysis/local_reopen_guarded_full400_guidance_audit.csv
runs/analysis/online_consistent_boundary400_stability.csv
runs/analysis/glucose_default_full400_summary.csv
runs/analysis/repeated_runtime_audit.csv
runs/analysis/appendix_300350/summary.csv
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
runs/glucose/solver_stats_300_cpu60.csv
runs/glucose/solver_stats_350_cpu60.csv
runs/glucose/solver_stats_full400_cpu60.csv
runs/cadical/solver_stats_full400_cpu60.csv
runs/analysis/cadical_default_full400_summary.csv
runs/analysis/cadical_default_full400_comparison.csv
runs/analysis/generalization_baseline/audit.csv
runs/analysis/generalization_baseline/summary.csv
runs/analysis/generalization_baseline/paper_table.csv
runs/analysis/generalization_baseline/raw/old_compact_300.csv
runs/analysis/generalization_baseline/raw/old_compact_350.csv
```

## Tracked Scripts And Configs

```text
configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml
configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml
summarize_online_consistent_boundary400_eval.py
summarize_local_reopen_guarded_full400_eval.py
summarize_online_consistent_boundary400_stability.py
figures/make_full400_cactus_paper.py
run_glucose_default_full400_cpu60.py
run_cadical_default_full400_cpu60.py
run_external_solver_baseline.py
summarize_external_solver_baseline.py
run_repeated_runtime_audit.py
summarize_generalization_baseline.py
```

## Repeated Runtime Audit Scope

The repeated runtime appendix is a same-seed key-claim audit, not seed
sensitivity and not a full repeated-run evaluation of Table 1.

Fixed interpretation:

- same-seed repeated runtime audit supports all six recovered timeouts.
- `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups.
- `3sat_188.cnf` is boundary-sensitive.
- `3sat_66.cnf` remains neutral timeout evidence.

## 300/350 Appendix Scope

The 300/350 appendix is a generality check only. It compares One-shot and the
final Online-Consistent Selector on `data/test/3sat/300/*.cnf` and
`data/test/3sat/350/*.cnf`.

Fixed interpretation:

- 300: Online-Consistent Selector preserves solved count and reduces mean time.
- 350: Online-Consistent Selector solves one additional instance and reduces
  mean time.
- Local Boundary Correction is not applied to 300/350.
- The result does not change the main 3SAT-400 full400 claim.

## Generalization / Baseline Robustness Scope

The broader appendix table answers baseline and size-width questions without
changing the model:

- Glucose default is included for 300/350/400 as an unguided CDCL reference.
- CaDiCaL default is included for 400 as a stronger unguided CDCL reference; it
  solves `75/200` under the 60s full400 protocol and should constrain paper
  claims accordingly.
- Old Compact 300/350 uses matched 200-instance reruns; the older
  `eval_compact_risk_disjoint_{300,350}.csv` files cover only 100 disjoint
  instances and are not used for the paper table.
- Online-Consistent 300/350 reuses the current appendix reruns with
  `feedback_refinement.local_reopen_candidate_manifest=null`.
- Full400 neural rows use the 3-seed robustness table.
- Local Boundary Correction appears only at 400.

## External Artifact Decision

Do not commit checkpoints until there is an explicit decision between direct
tracking, Git LFS, or external artifact hosting. The frozen CSV package is
sufficient for regenerating the paper-ready tables and figures without rerunning
checkpoint-dependent solver evaluations.

External stronger CDCL solvers are also artifact-gated. The current repository
contains CaDiCaL, Glucose, weighted Glucose, March, and weighted March binaries,
but no tracked Kissat / MapleSAT / CryptoMiniSat binary. If one is added for
baseline auditing, keep the binary under an external artifact path unless there
is an explicit licensing and tracking decision. The runner and summarizer are
tracked so that such a baseline can be reproduced without changing model code.
