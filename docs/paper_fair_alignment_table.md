# Fair Alignment Table for Historical and Current 3SAT Results

Purpose: align the old RLAF / Balanced-improver numbers with the current paper
protocol without changing models or running new experiments. This table is
diagnostic. It should prevent mixing the historical long-run results with the
current 60s wall-clock paper protocol.

## Key Protocol Difference

The historical `Balanced improver` 350/400 results were not evaluated under the
current 60s timeout protocol. The corresponding CSVs contain no
`INDETERMINATE` rows and have CPU times far above 60s:

- `runs/GNN_Glucose_3SAT_FeedbackImprover_Balanced/solver_stats_feedback_350.csv`
  has max CPU time `265.413s`.
- `runs/GNN_Glucose_3SAT_FeedbackImprover_Balanced/solver_stats_feedback_400.csv`
  has max CPU time `5449.880s`.

Therefore, historical long-run `200/200` solved counts must not be compared
directly with current fixed-budget solved counts. The post-hoc 60s cap rows
below are diagnostic only; they are computed from completed long-run traces, not
from a strict external-timeout rerun.

## Alignment Summary

| Size | Method | Protocol | Solved / 200 | Mean time (s) | Max CPU in source (s) |
| --- | --- | --- | ---: | ---: | ---: |
| 300 | Old RLAF / one-shot eval | 60s eval | 200 | 7.506 | 34.060 |
| 350 | Old RLAF / one-shot eval | 60s eval | 108 | 34.593 | 60.002 |
| 400 | Old RLAF / one-shot eval | 60s eval | 50 | 47.730 | 59.999 |
| 300 | Balanced improver | historical long-run | 200 | 4.835 | 23.569 |
| 350 | Balanced improver | historical long-run | 200 | 47.006 | 265.413 |
| 400 | Balanced improver | historical long-run | 200 | 763.915 | 5449.880 |
| 300 | Balanced improver | post-hoc 60s cap diagnostic | 200 | 4.684 | 23.569 |
| 350 | Balanced improver | post-hoc 60s cap diagnostic | 132 | 30.961 | 265.413 |
| 400 | Balanced improver | post-hoc 60s cap diagnostic | 52 | 45.975 | 5449.880 |
| 300 | Current One-shot | current 60s paper protocol | 200 | 15.311 | n/a |
| 300 | Current Online-Consistent Selector | current 60s paper protocol | 200 | 7.272 | n/a |
| 350 | Current One-shot | current 60s paper protocol | 108 | 43.741 | n/a |
| 350 | Current Online-Consistent Selector | current 60s paper protocol | 109 | 33.815 | n/a |
| 400 | Current One-shot | current 60s paper protocol | 50 | 47.752 | n/a |
| 400 | Current Online-Consistent Selector | current 60s paper protocol | 56 | 46.222 | n/a |
| 400 | Current + Local Boundary Correction | current 60s paper protocol | 56 | 45.498 | n/a |

## Interpretation

The defensible main comparison remains within the current 60s paper protocol:

- 3SAT-300: Online-Consistent Selector preserves `200/200` solved and reduces
  mean time from `15.311s` to `7.272s`.
- 3SAT-350: Online-Consistent Selector improves solved count from `108/200` to
  `109/200` and reduces mean time from `43.741s` to `33.815s`.
- 3SAT-400: Online-Consistent Selector improves solved count from `50/200` to
  `56/200` and reduces mean time from `47.752s` to `46.222s`.
- 3SAT-400 + Local Boundary Correction keeps solved count at `56/200` and
  reduces mean time to `45.498s`.

Historical Balanced improver results should be used to describe prior long-run
search-effort reduction, not as a solved-count baseline under the current paper
protocol. If cited, they should be clearly labeled as historical long-run
results. The post-hoc cap rows can be used only as a diagnostic sanity check.

## Source Files

- Old RLAF / one-shot eval:
  - `runs/GNN_Glucose_3SAT_V1/eval_oneshot_300.csv`
  - `runs/GNN_Glucose_3SAT_V1/eval_oneshot_350.csv`
  - `runs/GNN_Glucose_3SAT_V1/eval_oneshot_400.csv`
- Historical Balanced improver:
  - `runs/GNN_Glucose_3SAT_FeedbackImprover_Balanced/solver_stats_feedback_300.csv`
  - `runs/GNN_Glucose_3SAT_FeedbackImprover_Balanced/solver_stats_feedback_350.csv`
  - `runs/GNN_Glucose_3SAT_FeedbackImprover_Balanced/solver_stats_feedback_400.csv`
- Current 300/350 paper protocol:
  - `runs/analysis/appendix_300350/summary.csv`
- Current full400 paper protocol:
  - `runs/analysis/local_reopen_guarded_full400_summary.csv`
