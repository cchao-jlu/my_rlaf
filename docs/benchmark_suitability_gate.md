# Benchmark Suitability Gate

Scope: decide whether the current held-out benchmark package can support
a top-conference performance claim. This is a benchmark audit only: it
does not modify neural models, selectors, thresholds, solver code, or
Local Boundary Correction.

## Dataset Inventory

| family | size | instances |
| --- | --- | --- |
| 3sat | 250 | 200 |
| 3sat | 300 | 200 |
| 3sat | 350 | 200 |
| 3sat | 400 | 200 |

## Available Strong Solver Artifacts

| solver | path | executable | role |
| --- | --- | --- | --- |
| Glucose | solvers/glucose/simp/glucose_static | True | unguided CDCL baseline |
| Weighted Glucose | solvers/glucose_weighted/simp/glucose_static | True | neural workflow solver |
| CaDiCaL | solvers/cadical/cadical | True | strong CDCL baseline |
| March | solvers/march/march_nh | True | lookahead baseline |
| Kissat | solvers/kissat/kissat | False | missing external strong-solver gate |
| MapleSAT | solvers/maplesat/maplesat | False | missing external strong-solver gate |
| CryptoMiniSat | solvers/cryptominisat/cryptominisat5 | False | missing external strong-solver gate |

## March Suitability Probe

March is the strongest available baseline in the current checkout on the
random 3SAT held-out family. For 250/300/350, this gate uses a 20-instance
smoke probe. For 400, it uses the existing repeated full200 strict-60
audit.

| size | protocol | total | solved | unknown | solved_rate | mean_time | median_time | max_time | external_timeouts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | smoke20 | 20 | 20 | 0 | 1.000 | 0.160 | 0.120 | 0.434 | 0 |
| 300 | smoke20 | 20 | 20 | 0 | 1.000 | 0.729 | 0.550 | 2.482 | 0 |
| 350 | smoke20 | 20 | 20 | 0 | 1.000 | 4.251 | 2.352 | 12.719 | 0 |
| 400 | full200_repeat3_strict60 | 200 | 184 | 16 | 0.920 | 26.713 | 28.844 | 60.000 | 8 |

## Decision

- The current benchmark family is random 3SAT only, with 200 held-out
  instances each at sizes 250, 300, 350, and 400.
- March solves all 20 smoke instances at 250, 300, and 350. The 250/300
  smoke probes are sub-second on average, and 350 is still fully solved
  in the smoke set.
- On full400, March strict-60 solves 184/200 in all three repeats and
  strictly contains all current neural-guided solved sets.
- Therefore the current benchmark package is not suitable for a
  top-conference performance claim unless March/lookahead solvers are
  explicitly excluded by a well-justified protocol. It is suitable for a
  neural-guidance failure-boundary and risk-control study.
- The next hard gate for a performance route is not another selector. It is
  either a new benchmark protocol where strong solvers are not trivially
  dominant, or external Kissat/MapleSAT/CryptoMiniSat artifacts evaluated
  under the same repeated 60s protocol.

Generated artifacts:

```text
runs/analysis/benchmark_suitability_gate/dataset_inventory.csv
runs/analysis/benchmark_suitability_gate/solver_inventory.csv
runs/analysis/benchmark_suitability_gate/march_suitability_summary.csv
```
