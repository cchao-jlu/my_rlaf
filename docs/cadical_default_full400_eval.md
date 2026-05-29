# CaDiCaL Default Full400 Baseline

## Purpose

This run adds a stronger unguided CDCL reference for the paper baseline audit.
It does not modify the neural model, selector, thresholds, Local Boundary
Correction rule, or any guided result.

## Command

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_cadical_default_full400_cpu60.py \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/cadical/solver_stats_full400_cpu60.csv \
  --limit 60 \
  --timeout 65 \
  --workers 8
```

Solver executable:

```text
solvers/cadical/cadical
```

Solver version:

```text
1.5.2
```

Solver parameters:

```text
-q -t 60
```

CaDiCaL's `-t` option is a wall-clock time limit. The wrapper also uses a 65s
external guard. In this run, all unresolved instances returned `UNKNOWN` from
CaDiCaL around 60s; there were no external timeouts.

## Result

Source CSV:

```text
runs/cadical/solver_stats_full400_cpu60.csv
```

Summary CSV:

```text
runs/analysis/cadical_default_full400_summary.csv
```

Comparison CSV:

```text
runs/analysis/cadical_default_full400_comparison.csv
```

| Method | Dataset | Solved | SAT | UNSAT | Unknown | Mean time | Median time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CaDiCaL default | 3SAT-400 full400 | 75/200 | 75 | 0 | 125 | 42.924s | 60.000s |

Additional run diagnostics:

| Metric | Value |
| --- | ---: |
| rows | 200 |
| unique files | 200 |
| external timeouts | 0 |
| mean wall time | 42.929s |
| median wall time | 60.007s |

## Comparison To Current Paper Rows

| Method | Solved / 200 | Mean time (s) | Median time (s) |
| --- | ---: | ---: | ---: |
| Glucose default | 13 | 57.615 | 60.000 |
| CaDiCaL default | 75 | 42.924 | 60.000 |
| One-shot | 48.0 | 47.665 | 60.289 |
| Online-Consistent Selector | 53.0 | 46.324 | 60.366 |
| Old Compact | 54.0 | 46.278 | 60.373 |
| + Local Boundary Correction | 54.0 | 45.914 | 60.369 |

## Paper Interpretation

This is a strong unguided CDCL reference. Under the current 60s full400
protocol, CaDiCaL default solves more instances than the neural-guided Glucose
workflow. The paper should therefore not claim to beat modern CDCL defaults.

The correct positioning is narrower:

- One-shot, Online-Consistent Selector, Old Compact, and + Local Boundary
  Correction compare neural-guided Glucose workflows.
- Glucose default and CaDiCaL default are unguided solver references.
- CaDiCaL should appear in the baseline robustness appendix or experimental
  setup to answer the strong-CDCL reviewer question.
- The method contribution remains risk-controlled activation of neural feedback,
  not overall dominance over standalone CDCL solvers.
