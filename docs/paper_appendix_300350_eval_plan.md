# 300/350 Appendix Evaluation Plan

> Scope: pre-run audit and run design for a small appendix generality check.
> This does not introduce a new selector, tune thresholds, migrate Local
> Boundary Correction, or change the main full400 claim.

## Appendix Claim

Use 3SAT-300 and 3SAT-350 only as an appendix sanity check:

- Verify whether the final Online-Consistent Selector fails catastrophically on
  smaller held-out sizes.
- Do not upgrade the main claim beyond the frozen 3SAT-400 full400 result.
- Do not tune thresholds or train a new selector on 300/350.
- Do not force Local Boundary Correction onto 300/350. The formal correction is
  a 400-boundary ablation with a 400-specific candidate manifest and 750-feature
  rule.

## Read-Only Audit Findings

Existing reusable baseline evidence is mixed:

| artifact | status | note |
| --- | --- | --- |
| `runs/GNN_Glucose_3SAT_V1/eval_oneshot_300.csv` | exists | `200/200`, mean `7.5060s`; older run, not safe as final appendix baseline |
| `runs/GNN_Glucose_3SAT_V1/eval_oneshot_300_rerun_current.csv` | exists | `151/200`, mean `28.9624s`; shows one-shot 300 drift under a later rerun |
| `runs/GNN_Glucose_3SAT_V1/eval_oneshot_350.csv` | exists | `108/200`, mean `34.5932s` |
| `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_disjoint_300.csv` | exists | old compact disjoint subset only, `100` instances |
| `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/eval_compact_risk_disjoint_350.csv` | exists | old compact disjoint subset only, `100` instances |
| final `online_consistent_boundary400` 300/350 eval CSV | missing | no directly reusable final-method 300/350 result found |

Conclusion: do not mix old clean / polarity / SBE / fixed-rho / compact
disjoint artifacts into the final appendix table. If the appendix check is
needed, rerun One-shot and Online-Consistent under the same current evaluation
protocol and compare only those two methods.

## Important Config Risk

`configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml`
contains:

```text
feedback_refinement.local_reopen_candidate_manifest: data/new_closed_old_on_boundary/manifest.csv
```

`evaluate_guided_solver.py` loads this manifest by matching CNF basename. Since
`3sat_46.cnf` and similar basenames also exist in 300/350, leaving the manifest
enabled would incorrectly mark smaller-size instances as 400-boundary local
reopen candidates. For the Online-Consistent appendix run, override it to null:

```text
feedback_refinement.local_reopen_candidate_manifest=null
```

This preserves the final Online-Consistent Selector checkpoint and thresholds
while preventing the 400-boundary correction signal from leaking into 300/350.

## Proposed Evaluation Matrix

Datasets:

```text
data/test/3sat/300/*.cnf
data/test/3sat/350/*.cnf
```

Methods:

| method | config/checkpoint | role |
| --- | --- | --- |
| One-shot | `config_eval_guided_solver` + `checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt` + `feedback_refinement.enabled=False` | neural one-shot baseline |
| Online-Consistent Selector | `config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400` + `feedback_refinement.local_reopen_candidate_manifest=null` | final selector sanity check |

Metrics:

- solved / 200
- mean wall-clock time
- median wall-clock time
- delta solved vs One-shot
- delta mean time vs One-shot

No Local Boundary Correction row should be included for 300/350 unless a new,
properly scoped boundary-candidate set is defined and rerun as a separate
diagnostic. That should not be part of this appendix check.

## Output Layout

Use a single contained appendix directory:

```text
runs/analysis/appendix_300350/
```

Suggested files:

```text
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
runs/analysis/appendix_300350/summary.csv
docs/paper_appendix_300350_eval.md
```

## Smoke Design

Before full runs, smoke on a tiny deterministic subset to validate commands and
output paths:

```text
runs/analysis/appendix_300350/smoke/300/*.cnf
runs/analysis/appendix_300350/smoke/350/*.cnf
```

Use 5-10 symlinked CNFs per size. The smoke result is only for command
validation and should not enter the paper table.

## Full-Run Command Sketch

One-shot 300:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python evaluate_guided_solver.py \
  --config-name config_eval_guided_solver \
  checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  feedback_refinement.enabled=False \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.params.rnd-freq=0.0 \
  solver.params.K=0.1 \
  save_file=/home/sunshixin/chenchao/my_rlaf/runs/analysis/appendix_300350/raw/one_shot_300.csv
```

One-shot 350:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python evaluate_guided_solver.py \
  --config-name config_eval_guided_solver \
  checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  feedback_refinement.enabled=False \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.params.rnd-freq=0.0 \
  solver.params.K=0.1 \
  save_file=/home/sunshixin/chenchao/my_rlaf/runs/analysis/appendix_300350/raw/one_shot_350.csv
```

Online-Consistent 300:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400 \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  feedback_refinement.local_reopen_candidate_manifest=null \
  solver.params.cpu-lim=60 \
  solver.params.rnd-freq=0.0 \
  solver.params.K=0.1 \
  save_file=/home/sunshixin/chenchao/my_rlaf/runs/analysis/appendix_300350/raw/online_consistent_300.csv
```

Online-Consistent 350:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python evaluate_guided_solver.py \
  --config-name config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400 \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  feedback_refinement.local_reopen_candidate_manifest=null \
  solver.params.cpu-lim=60 \
  solver.params.rnd-freq=0.0 \
  solver.params.K=0.1 \
  save_file=/home/sunshixin/chenchao/my_rlaf/runs/analysis/appendix_300350/raw/online_consistent_350.csv
```

Use absolute `save_file` paths because `evaluate_guided_solver.py` joins
relative save paths under the checkpoint directory.

## Decision Before Running

Run only if the paper needs a small appendix generality check. The expected
paper wording should be conservative:

> Appendix results on 3SAT-300/350 test whether the final Online-Consistent
> Selector remains usable outside the full400 setting. These runs are not used
> for model selection and do not change the main 3SAT-400 claim.
