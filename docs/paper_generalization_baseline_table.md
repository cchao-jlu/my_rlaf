# Generalization / Baseline Robustness Table

Scope: broaden the evidence around the final selector without tuning any
thresholds, adding selector branches, or moving Local Boundary Correction to
300/350.

## Audit Result

| Item | Status | Reason | Source |
| --- | --- | --- | --- |
| One-shot 300/350 | reused | current appendix rerun exists for 200 instances; old drift-prone CSVs not used | `runs/analysis/appendix_300350/raw/one_shot_{300,350}.csv` |
| Online-Consistent 300/350 | reused | current appendix rerun exists for 200 instances with local_reopen_candidate_manifest=null | `runs/analysis/appendix_300350/raw/online_consistent_{300,350}.csv` |
| Glucose default 300/350 | new run | only full400 had the same nominal 60s / external 65s baseline; old runs/glucose/solver_stats.csv uses a long CPU limit | `runs/glucose/solver_stats_{300,350}_cpu60.csv` |
| Old Compact 300/350 | new run | historical eval_compact_risk_disjoint_{300,350}.csv covers only 100 disjoint instances | `runs/analysis/generalization_baseline/raw/old_compact_{300,350}.csv` |
| Local Boundary Correction 300/350 | not run | 400-boundary guarded correction; do not migrate to 300/350 | `` |
| Full400 neural methods | reused | use existing 3-seed robustness table as the main full400 result | `runs/analysis/full400_seed_robustness/method_summary.csv` |

## Paper-Ready Table

Caption:

> Generalization and baseline robustness across held-out 3SAT sizes. The
> 300/350 rows are single-run appendix checks under the frozen protocol.
> The 400 neural rows are the main 3-seed solver robustness results.
> Local Boundary Correction is only evaluated on the 400-boundary setting.

| Size | Method | Protocol | Solved / 200 | Mean time (s) | Median time (s) | Source |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 300 | Glucose default | single_run | 197 | 20.222 | 18.630 | `runs/glucose/solver_stats_300_cpu60.csv` |
| 300 | One-shot | single_run | 200 | 15.311 | 14.099 | `runs/analysis/appendix_300350/raw/one_shot_300.csv` |
| 300 | Online-Consistent Selector | single_run | 200 | 7.272 | 6.061 | `runs/analysis/appendix_300350/raw/online_consistent_300.csv` |
| 300 | Old Compact | single_run | 200 | 8.907 | 7.597 | `runs/analysis/generalization_baseline/raw/old_compact_300.csv` |
| 350 | Glucose default | single_run | 73 | 47.453 | 60.000 | `runs/glucose/solver_stats_350_cpu60.csv` |
| 350 | One-shot | single_run | 108 | 43.741 | 57.104 | `runs/analysis/appendix_300350/raw/one_shot_350.csv` |
| 350 | Online-Consistent Selector | single_run | 109 | 33.815 | 40.065 | `runs/analysis/appendix_300350/raw/online_consistent_350.csv` |
| 350 | Old Compact | single_run | 103 | 34.918 | 46.533 | `runs/analysis/generalization_baseline/raw/old_compact_350.csv` |
| 400 | Glucose default | single_run | 13 | 57.615 | 60.000 | `runs/glucose/solver_stats_full400_cpu60.csv` |
| 400 | One-shot | 3_seed_robustness | 48.0 | 47.665 | 60.289 | `runs/analysis/full400_seed_robustness/method_summary.csv` |
| 400 | Online-Consistent Selector | 3_seed_robustness | 53.0 | 46.324 | 60.366 | `runs/analysis/full400_seed_robustness/method_summary.csv` |
| 400 | Old Compact | 3_seed_robustness | 54.0 | 46.278 | 60.373 | `runs/analysis/full400_seed_robustness/method_summary.csv` |
| 400 | + Local Boundary Correction | 3_seed_robustness | 54.0 | 45.914 | 60.369 | `runs/analysis/full400_seed_robustness/method_summary.csv` |

## Interpretation

- The result is not a full400-only story: on 300, Online-Consistent
  preserves solved count and is faster than both One-shot and Old Compact;
  on 350, it improves solved count over One-shot and Old Compact in this
  frozen single-run appendix protocol.
- Glucose default is a useful unguided CDCL reference, not the main neural
  baseline. It is strong on 300 but falls behind the neural-guided methods
  on 350 and 400 under the nominal 60s budget.
- Old Compact remains a strong baseline. It matches Online-Consistent
  solved count on 300 but is slower in mean time, is weaker in solved
  count on 350, and reaches one more solved instance on full400 before
  Local Boundary Correction matches its solved count and lowers mean time.
- Local Boundary Correction stays 400-only because the formal rule is a
  guarded boundary correction tied to the 400 candidate manifest.

## Generated Artifacts

- `runs/analysis/generalization_baseline/summary.csv`
- `runs/analysis/generalization_baseline/paper_table.csv`
- `runs/analysis/generalization_baseline/audit.csv`

Regenerate with:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_generalization_baseline.py
```
