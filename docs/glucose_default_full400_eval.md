# Glucose Default Full400 Baseline

## Purpose

This run adds an unguided solver-default baseline for the paper readiness audit.
It does not modify the neural model, selector, local correction rule, or any paper
mainline method.

## Command

The original `evaluate_base_solver.py` path uses `glucose_static` with
`var_params=None`, but it only writes results after all workers finish and the
internal Glucose `-cpu-lim=60` did not reliably terminate long instances in this
environment. For the paper baseline, the run used a small resumable wrapper with
an external wall-clock guard:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_glucose_default_full400_cpu60.py \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/glucose/solver_stats_full400_cpu60.csv \
  --cpu-lim 60 \
  --timeout 65 \
  --workers 8
```

Solver executable:

```text
solvers/glucose/simp/glucose_static
```

Solver parameters:

```text
-rnd-seed=1 -cpu-lim=60 -rnd-freq=0.0 -K=0.1
```

The paper cutoff should be described as a nominal 60s solver budget with a 65s
external wall-clock guard. The external timeout is only a safety guard.
Externally timed-out instances are recorded as `INDETERMINATE` with `time=60.0`.
Instances solved by Glucose before the external guard keep the solver-reported
CPU time, which can be slightly above 60s because Glucose checks its internal
limit cooperatively.

## Result

Source CSV:

- `runs/glucose/solver_stats_full400_cpu60.csv`

Summary CSV:

- `runs/analysis/glucose_default_full400_summary.csv`

| Method | Dataset | Solved | SAT | UNSAT | Timeouts | Mean time | Median time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Glucose default | 3SAT-400 full400 | 13/200 | 13 | 0 | 187 | 57.615s | 60.000s |

Additional run diagnostics:

| Metric | Value |
| --- | ---: |
| rows | 200 |
| unique files | 200 |
| external timeouts | 187 |
| mean wall time | 62.304s |
| median wall time | 65.013s |
| max solver-reported time | 61.338s |

Solved files:

```text
3sat_127.cnf
3sat_129.cnf
3sat_142.cnf
3sat_150.cnf
3sat_20.cnf
3sat_27.cnf
3sat_47.cnf
3sat_54.cnf
3sat_65.cnf
3sat_88.cnf
3sat_92.cnf
3sat_93.cnf
3sat_96.cnf
```

## Paper Interpretation

This baseline answers a different question from the one-shot neural guidance
baseline. The paper main table currently compares neural-guided workflows:
One-shot, Old Compact, Online-Consistent Selector, and Local Boundary
Correction. The Glucose default baseline is an unguided CDCL reference and should
be used to clarify that One-shot is not solver default.

For the current full400 setting, unguided Glucose default is much weaker than the
one-shot neural guidance baseline (`13/200` versus `50/200`). This supports
keeping One-shot as the main neural baseline while adding Glucose default as a
solver-default reference in the experiment setup or appendix baseline table.
