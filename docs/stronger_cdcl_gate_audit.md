# Stronger-CDCL Gate Audit

Scope: evidence gate only. This audit does not change the neural model,
selector thresholds, Local Boundary Correction guard, portfolio schedule,
or solver configurations.

## Solver Availability

| solver | path | present | executable | role |
| --- | --- | --- | --- | --- |
| Glucose | solvers/glucose/simp/glucose_static | yes | yes | available baseline |
| Weighted Glucose | solvers/glucose_weighted/simp/glucose_static | yes | yes | available neural workflow solver |
| Weighted Glucose release | solvers/glucose_weighted/simp/glucose_release | yes | yes | available neural workflow solver |
| CaDiCaL | solvers/cadical/cadical | yes | yes | available stronger CDCL baseline |
| March | solvers/march/march_nh | yes | yes | available lookahead solver baseline |
| Weighted March | solvers/march_weighted/march_nh | yes | yes | available weighted lookahead solver |
| Kissat | solvers/kissat/kissat | no | no | missing external stronger CDCL gate |
| MapleSAT | solvers/maplesat/maplesat | no | no | missing external stronger CDCL gate |
| CryptoMiniSat | solvers/cryptominisat/cryptominisat5 | no | no | missing external stronger CDCL gate |

Current checkout conclusion: CaDiCaL and March are available; Kissat,
MapleSAT, and CryptoMiniSat are not present as executable artifacts.

## March Strict-Hard Subset

A decisive top-conference performance claim would require complementarity
on instances that a strong baseline cannot solve. Under repeated March
strict-60, the hard subset contains 16 instances. Current neural and
portfolio methods solve none of them.

| item | value | interpretation |
| --- | --- | --- |
| available_executable_strong_solvers | 2 | CaDiCaL and March are the available stronger-solver baselines in this checkout. |
| missing_external_solver_families | 3 | Kissat, MapleSAT, and CryptoMiniSat binaries are absent from this checkout. |
| march_strict60_hard_instances | 16 | Instances unsolved by March under strict 60s in all three repeats. |
| neural_solved_on_march_hard | 0 | Local Boundary Correction solves none of the repeated-March strict-hard subset. |
| online_solved_on_march_hard | 0 | Online-Consistent Selector solves none of the repeated-March strict-hard subset. |
| portfolio_solved_repeats_on_march_hard | 0 | The Local5 -> CaDiCaL55 portfolio has no solved repeat on the repeated-March strict-hard subset. |
| cadical_solved_repeats_on_march_hard | 0 | CaDiCaL has no solved repeat on the repeated-March strict-hard subset. |

March strict-hard instance keys:

`3sat_102.cnf`, `3sat_126.cnf`, `3sat_160.cnf`, `3sat_184.cnf`, `3sat_187.cnf`, `3sat_198.cnf`, `3sat_21.cnf`, `3sat_3.cnf`, `3sat_31.cnf`, `3sat_34.cnf`, `3sat_37.cnf`, `3sat_49.cnf`, `3sat_5.cnf`, `3sat_50.cnf`, `3sat_67.cnf`, `3sat_72.cnf`

Detailed overlap is written to:

```text
runs/analysis/stronger_cdcl_gate/march_strict_hard_overlap.csv
```

## Decision

- The current result cannot support a strong-SAT-baseline performance or
  complementarity claim: the repeated-March strict-hard subset has zero
  neural, CaDiCaL, or Local5 -> CaDiCaL55 portfolio solves.
- The paper can still be made rigorous as a failure-boundary / risk-control
  study: Online-Consistent selection improves a neural-guided Glucose
  workflow, but stronger solver families expose the boundary of that
  improvement.
- To reopen a top-conference performance route, the next hard gate is not
  another neural selector. It is an external stronger-solver artifact
  audit: provide Kissat/MapleSAT/CryptoMiniSat binaries, run the same
  full400 60s protocol with three repeats, and check whether any neural or
  portfolio method solves instances missed by that solver in all repeats.
- If those external solvers also cover all neural-solved instances, the
  only defensible top-conference path is a negative/failure-boundary
  framing or a different benchmark protocol with an explicit rationale.

Generated artifacts:

```text
runs/analysis/stronger_cdcl_gate/solver_availability.csv
runs/analysis/stronger_cdcl_gate/summary.csv
runs/analysis/stronger_cdcl_gate/march_strict_hard_overlap.csv
```
