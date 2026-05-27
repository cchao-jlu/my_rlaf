# Full400 Seed Smoke

This is a small seed-sensitivity smoke test on selected full400 instances.
It changes only the Glucose `-rnd-seed` value through `+solver.params.seed=<seed>`.
The model, thresholds, `rnd-freq=0.0`, and candidate manifest policy are unchanged.

Important scope: this is not a full400 multi-seed evaluation.
It is a decision check for whether full400 multi-seed robustness is worth running.

Decision reading: the selected key instances show no solved-pattern instability across seeds 1/2/3.
This supports treating the current full400 repeated table as same-seed runtime stability plus low seed-sensitivity evidence on boundary cases.
It does not require immediate full400 multi-seed reruns unless the submission needs a stronger robustness table.

Seeds: 1, 2, 3.
Methods: Online-Consistent Selector, Old Compact, + Local Boundary Correction.

Selected instances:

- `3sat_188.cnf`
- `3sat_163.cnf`
- `3sat_189.cnf`
- `3sat_85.cnf`
- `3sat_89.cnf`
- `3sat_97.cnf`
- `3sat_0.cnf`
- `3sat_8.cnf`
- `3sat_192.cnf`
- `3sat_195.cnf`
- `3sat_1.cnf`
- `3sat_86.cnf`
- `3sat_140.cnf`
- `3sat_190.cnf`

Outputs:

- `runs/analysis/full400_seed_smoke/combined.csv`
- `runs/analysis/full400_seed_smoke/summary.csv`
- `runs/analysis/full400_seed_smoke/per_instance_summary.csv`
- `runs/analysis/full400_seed_smoke/pair_summary.csv`

## Per-Seed Summary

| method | seed | solved | mean time | median time |
| --- | ---: | ---: | ---: | ---: |
| Online-Consistent Selector | 1 | 9 | 27.4822 | 15.7865 |
| Old Compact | 1 | 10 | 28.3863 | 24.0749 |
| + Local Boundary Correction | 1 | 10 | 25.2518 | 15.6217 |
| Online-Consistent Selector | 2 | 9 | 27.3774 | 15.7875 |
| Old Compact | 2 | 10 | 28.5722 | 24.7559 |
| + Local Boundary Correction | 2 | 10 | 25.3731 | 15.9270 |
| Online-Consistent Selector | 3 | 9 | 27.3732 | 15.9633 |
| Old Compact | 3 | 10 | 28.3370 | 24.3784 |
| + Local Boundary Correction | 3 | 10 | 25.3706 | 16.2023 |

## Pair Summary

| comparison | delta solved seed sum | recovered all seeds | lost all seeds | mean delta time | max slowdown | max speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Online-Consistent Selector vs Old Compact | 3 | 1 | 0 | 1.0209 | 43.7019 | -28.8982 |
| Online-Consistent Selector vs + Local Boundary Correction | 3 | 1 | 0 | -2.0791 | 0.0980 | -28.6863 |
| Old Compact vs + Local Boundary Correction | 0 | 0 | 0 | -3.1000 | 0.6563 | -43.7443 |

## Seed Stability

Unstable method-instance outcomes across seeds: 0.

## Boundary Instance

| instance | method | solved seeds | mean time | min time | max time |
| --- | --- | ---: | ---: | ---: | ---: |
| 3sat_188.cnf | + Local Boundary Correction | 3/3 | 31.7004 | 31.3814 | 32.1511 |
| 3sat_188.cnf | Old Compact | 3/3 | 31.4885 | 30.8603 | 32.0580 |
| 3sat_188.cnf | Online-Consistent Selector | 0/3 | 60.3867 | 60.3715 | 60.4087 |
