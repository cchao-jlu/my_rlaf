# 300/350 Appendix Evaluation

> Scope: appendix generality check for the final Online-Consistent Selector.
> This does not change the main 3SAT-400 full400 claim and was not used for
> threshold tuning or model selection.

## Protocol

This appendix run uses the same minimal scope validated by the smoke test:

- compare only One-shot vs Online-Consistent Selector;
- do not run + Local Boundary Correction on 300/350;
- do not tune thresholds or train a new selector;
- rerun One-shot under the same current evaluation protocol instead of reusing
  old 300/350 CSVs, because earlier 300 results showed runtime drift;
- set `feedback_refinement.local_reopen_candidate_manifest=null` for
  Online-Consistent runs to avoid leaking the 400-boundary candidate manifest
  into 300/350 by basename matching.

Inputs:

```text
data/test/3sat/300/*.cnf
data/test/3sat/350/*.cnf
```

Raw outputs:

```text
runs/analysis/appendix_300350/raw/one_shot_300.csv
runs/analysis/appendix_300350/raw/one_shot_350.csv
runs/analysis/appendix_300350/raw/online_consistent_300.csv
runs/analysis/appendix_300350/raw/online_consistent_350.csv
```

Summary:

```text
runs/analysis/appendix_300350/summary.csv
```

## Results

| size | method | solved / total | mean_time | median_time | delta_solved_vs_one_shot | delta_mean_time_vs_one_shot |
| --- | --- | --- | --- | --- | --- | --- |
| 300 | One-shot | 200 / 200 | 15.3115s | 14.0989s | 0 | 0.0000s |
| 300 | Online-Consistent Selector | 200 / 200 | 7.2723s | 6.0607s | 0 | -8.0391s |
| 350 | One-shot | 108 / 200 | 43.7406s | 57.1037s | 0 | 0.0000s |
| 350 | Online-Consistent Selector | 109 / 200 | 33.8154s | 40.0652s | +1 | -9.9252s |

## Interpretation

These appendix results support a limited generality check: the final
Online-Consistent Selector does not visibly collapse on 3SAT-300/350 under the
same frozen selector protocol. On 300 it preserves solved count and lowers mean
time. On 350 it solves one additional instance and lowers mean time.

This should remain an appendix result. The main paper claim is still the
full400 result on 3SAT-400. The appendix does not justify migrating Local
Boundary Correction to 300/350, changing thresholds, or introducing another
selector line.

## Reproducibility Notes

Online-Consistent commands used:

```text
--config-name config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400
feedback_refinement.local_reopen_candidate_manifest=null
solver.params.cpu-lim=60
solver.params.rnd-freq=0.0
solver.params.K=0.1
```

One-shot commands used:

```text
--config-name config_eval_guided_solver
checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt
feedback_refinement.enabled=False
solver.params.cpu-lim=60
solver.params.rnd-freq=0.0
solver.params.K=0.1
```

Use these results as appendix evidence only:

- good result wording: appendix generality check;
- bad result wording, if future reruns differ: limitation / scale sensitivity;
- never tune the model or thresholds to rescue the appendix outcome.
