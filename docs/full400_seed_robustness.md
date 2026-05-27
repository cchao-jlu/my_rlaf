# Full400 Solver-Seed Robustness

This is a full400 solver-seed robustness evaluation for the paper's main result table.
It changes only the Glucose `-rnd-seed` value via `+solver.params.seed=<seed>`.
The model, thresholds, `rnd-freq=0.0`, and Local Boundary Correction candidate manifest are unchanged.

Scope:

- seeds 1, 2, 3
- One-shot
- Online-Consistent Selector
- Old Compact
- + Local Boundary Correction

Seed 1 raw CSVs are imported from `runs/analysis/full400_repeated_runtime/raw/*/repeat0.csv`.
Those runs used the default `solve_cnf(seed=1)` and are equivalent to explicit `+solver.params.seed=1` under this evaluation path.

Outputs:

- `runs/analysis/full400_seed_robustness/combined.csv`
- `runs/analysis/full400_seed_robustness/seed_summary.csv`
- `runs/analysis/full400_seed_robustness/method_summary.csv`
- `runs/analysis/full400_seed_robustness/per_instance_summary.csv`
- `runs/analysis/full400_seed_robustness/pair_summary.csv`
- `runs/analysis/full400_seed_robustness/solved_pattern_overlap.csv`
- `runs/analysis/full400_seed_robustness/local_vs_old_harm_audit.csv`

## Method Summary

| method | seeds | solved mean | solved std | solved range | mean time mean | mean time std |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| One-shot | 3 | 48.000 | 0.000 | 48-48 | 47.6647 | 0.0207 |
| Online-Consistent Selector | 3 | 53.000 | 0.000 | 53-53 | 46.3236 | 0.0098 |
| Old Compact | 3 | 54.000 | 0.000 | 54-54 | 46.2777 | 0.0176 |
| + Local Boundary Correction | 3 | 54.000 | 0.000 | 54-54 | 45.9139 | 0.0150 |

## Per-Seed Summary

| method | seed | solved | mean time | median time |
| --- | ---: | ---: | ---: | ---: |
| One-shot | 1 | 48 | 47.6417 | 60.2724 |
| Online-Consistent Selector | 1 | 53 | 46.3304 | 60.3739 |
| Old Compact | 1 | 54 | 46.2694 | 60.3602 |
| + Local Boundary Correction | 1 | 54 | 45.9115 | 60.3737 |
| One-shot | 2 | 48 | 47.6605 | 60.2978 |
| Online-Consistent Selector | 2 | 53 | 46.3098 | 60.3603 |
| Old Compact | 2 | 54 | 46.2616 | 60.3640 |
| + Local Boundary Correction | 2 | 54 | 45.8969 | 60.3512 |
| One-shot | 3 | 48 | 47.6918 | 60.2965 |
| Online-Consistent Selector | 3 | 53 | 46.3306 | 60.3652 |
| Old Compact | 3 | 54 | 46.3023 | 60.3934 |
| + Local Boundary Correction | 3 | 54 | 45.9333 | 60.3816 |

## Robustness Diagnostics

- Method-instance solved-pattern instability count: 0.
- Old Compact over Online all-seed solved instances: 3sat_188.cnf.
- Local Correction over Online all-seed solved instances: 3sat_188.cnf.
- Local-vs-Old solved mismatch count: 0.
- Local-vs-Old same-solved slowdown count >0.1s: 7.
- Local-vs-Old same-solved slowdown count >0.5s: 2.
- Local-vs-Old same-solved slowdown count >1.0s: 0.
- Maximum Local-vs-Old same-solved slowdown is 0.5239s on `3sat_86.cnf`.

Solved pattern order: `One-shot / Online-Consistent / Old Compact / + Local Boundary Correction`.

| pattern | count |
| --- | ---: |
| 0000 | 146 |
| 0011 | 1 |
| 0111 | 5 |
| 1111 | 48 |

## Pair Summary

| comparison | delta solved mean | recovered all seeds | lost all seeds | mean delta time |
| --- | ---: | ---: | ---: | ---: |
| One-shot vs Online-Consistent Selector | 5.000 | 5 | 0 | -1.3411 |
| One-shot vs Old Compact | 6.000 | 6 | 0 | -1.3869 |
| Online-Consistent Selector vs Old Compact | 1.000 | 1 | 0 | -0.0459 |
| Online-Consistent Selector vs + Local Boundary Correction | 1.000 | 1 | 0 | -0.4097 |
| Old Compact vs + Local Boundary Correction | 0.000 | 0 | 0 | -0.3639 |
| One-shot vs + Local Boundary Correction | 6.000 | 6 | 0 | -1.7508 |

## Paper-Facing Reading

Use this table as solver-seed robustness evidence, not as a new model result.
The intended claim is whether the repeated full400 conclusions remain stable under seeds 1/2/3.
Do not tune thresholds or alter model branches based on this table.
