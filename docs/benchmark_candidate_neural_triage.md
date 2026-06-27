# Benchmark Candidate Frozen-Neural Triage

Scope: frozen neural triage on candidate instances that the candidate
smoke marked as March/CaDiCaL both-unknown. This does not train models,
tune thresholds, or migrate Local Boundary Correction.

## Candidate Subsets

| family | size | file_key |
| --- | --- | --- |
| 3sat | 450 | 3sat_0.cnf |
| 3sat | 450 | 3sat_4.cnf |
| 3sat | 450 | 3sat_7.cnf |
| 3sat | 500 | 3sat_0.cnf |
| 3sat | 500 | 3sat_1.cnf |
| 3sat | 500 | 3sat_2.cnf |
| 3sat | 500 | 3sat_4.cnf |
| 3sat | 500 | 3sat_6.cnf |
| 3sat | 500 | 3sat_7.cnf |

## Method Summary

| family | size | paper_name | seeds | solved_mean | solved_min | solved_max | mean_time_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat | 450 | One-shot | 3 | 0.000 | 0 | 0 | 60.137 |
| 3sat | 450 | Online-Consistent Selector | 3 | 0.000 | 0 | 0 | 60.200 |
| 3sat | 500 | One-shot | 3 | 0.000 | 0 | 0 | 60.273 |
| 3sat | 500 | Online-Consistent Selector | 3 | 0.000 | 0 | 0 | 60.358 |

## Strict Complement Summary

Solved means solved in all requested neural seeds. Pattern order is `One-shot / Online-Consistent Selector`.

| family | size | n | one_shot_strict | online_strict | online_only_strict |
| --- | --- | --- | --- | --- | --- |
| 3sat | 450 | 3 | 0 | 0 | 0 |
| 3sat | 500 | 6 | 0 | 0 | 0 |

## Pattern Counts

| family | size | pattern | count |
| --- | --- | --- | --- |
| 3sat | 450 | 00 | 3 |
| 3sat | 500 | 00 | 6 |

## Decision

- Frozen Online-Consistent guidance solves no candidate instance that
  the current March/CaDiCaL smoke left both-unknown.
- Together with the 3SAT-450 repeated hard-subset gate, this weakens the
  current frozen-workflow performance route. New benchmark design or
  new method work would be required for a top-conference performance claim.

Generated artifacts:

```text
runs/analysis/benchmark_candidate_neural_triage/both_unknown_subset.csv
runs/analysis/benchmark_candidate_neural_triage/combined.csv
runs/analysis/benchmark_candidate_neural_triage/summary.csv
runs/analysis/benchmark_candidate_neural_triage/overlap.csv
```
