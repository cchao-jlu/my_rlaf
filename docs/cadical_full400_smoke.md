# CaDiCaL Full400 Smoke

Scope: read-only baseline feasibility check for a stronger CDCL reference. This
does not change the neural model, selector, thresholds, or paper main claim.

## Solver

```text
solvers/cadical/cadical
version: 1.5.2
```

The existing project has a CaDiCaL binary and an UNSAT-core helper in
`src/solving/core.py`, but the standard `evaluate_base_solver.py` path only
supports the current `src/solving/solver.py` solver choices (`glucose` and
`march`). CaDiCaL therefore needs a small standalone wrapper before it can be
used as a paper baseline.

## Smoke Command

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_cadical_full400_smoke.py \
  --input 'data/test/3sat/400/*.cnf' \
  --output runs/analysis/cadical_smoke/smoke.csv \
  --limit 60 \
  --timeout 65 \
  --n 5
```

CaDiCaL options:

```text
-q -t 60
```

`-t` is CaDiCaL's wall-clock time limit. The wrapper also uses a 65s external
guard.

## Result

| file | Result | wall time (s) | return code |
| --- | --- | ---: | --- |
| `3sat_0.cnf` | UNKNOWN | 60.009 | 0 |
| `3sat_1.cnf` | SATISFIABLE | 4.925 | 10 |
| `3sat_10.cnf` | SATISFIABLE | 0.586 | 10 |
| `3sat_100.cnf` | SATISFIABLE | 1.368 | 10 |
| `3sat_101.cnf` | UNKNOWN | 60.009 | 0 |

Source:

```text
runs/analysis/cadical_smoke/smoke.csv
```

## Interpretation

The smoke test confirms that CaDiCaL is runnable and result parsing is simple:
`s SATISFIABLE` / `s UNSATISFIABLE` lines identify solved instances, return code
10 indicates SAT, return code 20 would indicate UNSAT, and timeout-like cases
return `UNKNOWN`.

This is enough evidence to justify a full400 CaDiCaL default baseline if we want
to answer the top-conference baseline question. It should be run as an unguided
CDCL reference, not as a neural method, and should not trigger any selector or
threshold changes.
