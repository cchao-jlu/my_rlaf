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
| Optional appendix: Glucose default baseline | `runs/glucose/solver_stats_full400_cpu60.csv`; `runs/analysis/glucose_default_full400_summary.csv`; `docs/glucose_default_full400_eval.md` | `run_glucose_default_full400_cpu60.py` | Yes | CNF dataset only for rerun |
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
run_repeated_runtime_audit.py
```

## Repeated Runtime Audit Scope

The repeated runtime appendix is a same-seed key-claim audit, not seed
sensitivity and not a full repeated-run evaluation of Table 1.

Fixed interpretation:

- same-seed repeated runtime audit supports all six recovered timeouts.
- `3sat_196.cnf` and `3sat_46.cnf` are stable hard speedups.
- `3sat_188.cnf` is boundary-sensitive.
- `3sat_66.cnf` remains neutral timeout evidence.

## External Artifact Decision

Do not commit checkpoints until there is an explicit decision between direct
tracking, Git LFS, or external artifact hosting. The frozen CSV package is
sufficient for regenerating the paper-ready tables and figures without rerunning
checkpoint-dependent solver evaluations.
