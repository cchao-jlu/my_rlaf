# Glucose Seed Effect Audit

This is a read-only implementation audit for whether solver seed sensitivity is meaningful under the paper evaluation protocol.

## Findings

- `src/solving/solver.py` passes `seed` to Glucose as `-rnd-seed=<seed>`.
- `src/solving/solver.py` defaults to `seed=1`, so existing repeated runtime runs are same-seed runtime repeats.
- Passing Hydra `solver.params.rnd-seed=<seed>` would create a duplicate CLI option, because `solve_cnf(..., seed=1)` already emits `-rnd-seed=1`.
- The seed smoke therefore uses `+solver.params.seed=<seed>`, which binds to the Python `solve_cnf(seed=...)` argument and emits exactly one `-rnd-seed=<seed>`.

## Glucose Paths Affected By Seed

In `solvers/glucose_weighted/core/Solver.cc`, `random_seed` is consumed by:

- random variable selection when `drand(random_seed) < random_var_freq`;
- random polarity when `rnd_pol` is enabled;
- randomized initial activity when `rnd-init` is enabled;
- randomized restart phase when `randomize_on_restarts` or `fix-phas-rest` is enabled.

The paper protocol sets `rnd-freq=0.0`, does not enable random polarity, and does not enable randomized initial activity or phase restart flags at the command line. However, Glucose may enable restart phase randomization internally in adaptive branches, so a small smoke check is still useful.

## Current Interpretation

The existing full400 repeated runtime table is same-seed runtime stability, not solver-seed sensitivity.

The selected-instance seed smoke should be interpreted as low seed-sensitivity evidence for the key boundary and recovered-timeout cases. It does not replace a full400 multi-seed robustness table.
