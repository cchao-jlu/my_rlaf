# Full400 Repeated Runtime Evaluation

This is a full-test same-seed repeated runtime evaluation for the paper's wall-clock stability claim.
It does not change the model, thresholds, configs, or solver seed.

Important interpretation: the absolute solved counts differ from the frozen single-run paper table,
which is expected wall-clock drift. The evidence here is the repeated-run stability of the deltas:
Online-Consistent Selector is +5 solved over One-shot in all three repeats, and
+ Local Boundary Correction is +6 solved over One-shot in all three repeats.

Scope:

- One-shot x 3 repeats
- Online-Consistent Selector x 3 repeats
- + Local Boundary Correction x 3 repeats
- Old Compact is not included in this run; it remains the frozen reference baseline unless explicitly rerun with a matched config.

Outputs:

- `runs/analysis/full400_repeated_runtime/combined.csv`
- `runs/analysis/full400_repeated_runtime/repeat_summary.csv`
- `runs/analysis/full400_repeated_runtime/summary.csv`
- `runs/analysis/full400_repeated_runtime/per_instance_summary.csv`
- `runs/analysis/full400_repeated_runtime/pair_summary.csv`

## Method Summary

| method | repeats | solved mean | solved range | mean time mean | mean time std |
| --- | ---: | ---: | --- | ---: | ---: |
| One-shot | 3 | 48.000 | 48-48 | 47.6532 | 0.0148 |
| Online-Consistent Selector | 3 | 53.000 | 53-53 | 46.3120 | 0.0246 |
| + Local Boundary Correction | 3 | 54.000 | 54-54 | 45.9017 | 0.0074 |

## Per-Repeat Summary

| method | repeat | solved | mean time | median time |
| --- | ---: | ---: | ---: | ---: |
| One-shot | 0 | 48 | 47.6417 | 60.2724 |
| Online-Consistent Selector | 0 | 53 | 46.3304 | 60.3739 |
| + Local Boundary Correction | 0 | 54 | 45.9115 | 60.3737 |
| One-shot | 1 | 48 | 47.6437 | 60.2689 |
| Online-Consistent Selector | 1 | 53 | 46.2772 | 60.3465 |
| + Local Boundary Correction | 1 | 54 | 45.9001 | 60.3647 |
| One-shot | 2 | 48 | 47.6740 | 60.3030 |
| Online-Consistent Selector | 2 | 53 | 46.3284 | 60.3775 |
| + Local Boundary Correction | 2 | 54 | 45.8936 | 60.3599 |

## Pair Summary

| comparison | delta solved mean | recovered all repeats | lost all repeats | mean delta time | faster instances | slower instances |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| One-shot vs Online-Consistent Selector | 5.000 | 5 | 0 | -1.3411 | 16 | 58 |
| Online-Consistent Selector vs + Local Boundary Correction | 1.000 | 1 | 0 | -0.4103 | 6 | 7 |
| One-shot vs + Local Boundary Correction | 6.000 | 6 | 0 | -1.7515 | 16 | 58 |
