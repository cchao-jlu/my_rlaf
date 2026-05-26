# 300/350 Appendix Smoke

> Scope: smoke test for the appendix 300/350 evaluation chain. This is not a
> paper result table, not a seed-sensitivity study, and not a full 300/350
> appendix run.

## Purpose

The smoke test validates:

- absolute `save_file` paths write to `runs/analysis/appendix_300350/smoke/raw/`;
- One-shot and Online-Consistent outputs share summary-compatible columns;
- `feedback_refinement.local_reopen_candidate_manifest=null` is used for
  Online-Consistent 300/350, preventing 400-boundary manifest leakage;
- no threshold tuning, new selector, or Local Boundary Correction migration is
  involved.

## Smoke Dataset

Each size uses the first 10 sorted CNF files from the corresponding held-out
test directory, symlinked into:

```text
runs/analysis/appendix_300350/smoke/300/
runs/analysis/appendix_300350/smoke/350/
```

The smoke subset is only for command validation and should not enter the paper
table.

## Results

| method | size | rows | solved | mean_time | median_time | raw CSV |
| --- | --- | --- | --- | --- | --- | --- |
| One-shot | 300 | 10 | 10/10 | 4.4502s | 1.3752s | `runs/analysis/appendix_300350/smoke/raw/one_shot_300.csv` |
| One-shot | 350 | 10 | 6/10 | 36.3355s | 45.2832s | `runs/analysis/appendix_300350/smoke/raw/one_shot_350.csv` |
| Online-Consistent Selector | 300 | 10 | 10/10 | 4.4193s | 1.3965s | `runs/analysis/appendix_300350/smoke/raw/online_consistent_300.csv` |
| Online-Consistent Selector | 350 | 10 | 6/10 | 31.3954s | 33.0433s | `runs/analysis/appendix_300350/smoke/raw/online_consistent_350.csv` |

## Validation

All four smoke CSVs include the columns needed for the appendix summary:

```text
Result
file
CPU time
GPU time
time
refinement CPU time
refinement GPU time
```

Online-Consistent runs completed without loading local reopen candidates, which
is the expected behavior under:

```text
feedback_refinement.local_reopen_candidate_manifest=null
```

## Next Decision

The run chain is clean enough for a full appendix run if the paper still needs a
300/350 generality check. Full runs should still use only:

- One-shot 300
- One-shot 350
- Online-Consistent Selector 300
- Online-Consistent Selector 350

Do not add Local Boundary Correction, tune thresholds, or introduce a new
selector based on the smoke outcome.
