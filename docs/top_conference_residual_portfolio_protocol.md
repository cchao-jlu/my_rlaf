# Top-Conference Residual Portfolio Protocol

## Claim

In the residual setting after a fixed strong-solver union fails, a fixed-budget
neural restart portfolio solves more random 3SAT transition-band residual
instances than a same-budget non-neural rerun portfolio.

This replaces the old Glucose/Online-Consistent performance mainline. The
neural method is not positioned as a replacement for March or CaDiCaL. It is a
budgeted residual portfolio used only after both strong solvers fail.

## Stages

### Stage 0: Candidate Generation

Generate random 3SAT transition-band candidates before any neural selector
tuning. Report the full denominator:

- candidate instances: `N`
- sizes and instances per size
- generation seed
- CNF source directory

Immediately after defining the candidate denominator, write an immutable
candidate-level train/dev/held-out manifest with a fixed split seed. The
preferred order is:

```text
candidate generation spec -> candidate split manifest -> March/CaDiCaL
filtering -> residual train/dev/held-out projected from candidate split
```

This is stronger than splitting only after observing the residual set, because
the held-out bucket is fixed before knowing which candidates survive the strong
solver union. The candidate manifest must record its generation seed, split
seed, sizes, instances per size, CNF root, manifest hash, and split counts.

### Stage 1: Strong-Solver Union Filter

Run the fixed strong baseline:

- March, 60s cap
- CaDiCaL, 60s cap
- union solved if either solver returns `SATISFIABLE` or `UNSATISFIABLE`
  within the nominal 60s cap

Report:

- March solved
- CaDiCaL solved
- solved after nominal limit but before external timeout
- union solved
- both-unknown residual count `R`

Only both-unknown residual instances enter the neural residual experiment.
If an external timeout is larger than the nominal solver cap, any solution
returned after the nominal cap must be reported as late and must not shrink
the residual denominator.

### Stage 2: Residual Split

The residual pool must be split before selector thresholds, adaptive budget
rules, or solver schedules are tuned. If a candidate-level split manifest
exists, residual split assignment must be projected from that manifest:
`candidate_train -> residual_train`, `candidate_dev -> residual_dev`, and
`candidate_heldout -> residual_heldout`.

- pilot gate: existing all-49 residual set, used only to decide whether the
  current checkpoint has enough oracle sampled coverage to continue
- dev residual: threshold/top-k/schedule selection
- held-out residual: final one-shot protocol evaluation

The pilot gate is not a final paper result and must not be used as the
held-out evidence after tuning. It must also not be used for selector
threshold, adaptive budget, or schedule tuning.

When excluding pilot instances from a later residual pool, exclusion should use
CNF content hashes whenever the files are available. File names such as
`3sat_12.cnf` are not globally unique across generation seeds.

### Stage 3: Oracle Diagnostic

Oracle sampling is a diagnostic upper bound, not a deployable method and not
the main claim.

Fixed pilot settings:

- sample seed: `1729`
- samples per residual instance: `16`
- solver: weighted March
- full-sample CPU cap: `60s`
- no selector and no threshold tuning
- per-instance artifacts and resume are required

Go/no-go interpretation:

- oracle `<= 2/49`: stop selector work and change the training objective
- oracle `>= 5/49`: the checkpoint has enough sampled coverage to continue
- oracle positives concentrated in one or two narrow modes: expand residual
  pool before making any performance claim

### Stage 4: Fixed Selected Neural Portfolio

The paper result must use a non-oracle selected portfolio. Any adaptive budget
rule must be pre-registered on the dev residual set and frozen before held-out
evaluation.

Allowed rule family:

```text
if probe_solved_samples > 0:
    run probe-solved samples first, up to the fixed solved-probe cap
elif max_probe_deadends >= threshold_A:
    run top-8
elif max_probe_deadends >= threshold_B:
    run top-4
else:
    run top-2
```

`threshold_A`, `threshold_B`, ranking keys, and caps are chosen on dev only.
Held-out evaluation is one-shot. The held-out run must write a frozen
`selector_spec.json` that records the checkpoint, sample seeds, solver seed,
sample count, policy, default `top_k`, adaptive thresholds, adaptive top-k
caps, solved-probe cap, probe cap, full-run cap, and budget accounting. The
protocol audit must be able to recompute each instance's `effective_top_k`
from held-out probe features and this frozen spec.

Budget accounting must include:

- GNN inference / sample generation wall time
- probe CPU and wall time
- selected full-run CPU and wall time
- capped timeout budget for failed attempts
- allocated residual CPU budget:
  `num_samples * probe_cpu_lim + effective_top_k * full_cpu_lim`

Report both residual incremental budget and full pipeline budget after the
March+CaDiCaL union baseline. The same-budget non-neural control must match
the neural allocated residual budget, not the neural actual consumed time after
early solves. Actual capped CPU and wall-clock remain reported separately.

### Stage 5: Same-Budget Non-Neural Control

The non-neural control is mandatory. It must be a fixed rerun portfolio with
the same residual CPU budget as the selected neural portfolio.
Its schedule is derived from the dev neural allocated budget and frozen before
held-out evaluation. It must not be derived from held-out neural consumed time
or held-out neural solve outcomes.

Required controls:

- March default rerun attempts as part of a fixed mixed schedule. The current
  unweighted March binary has no exposed random seed interface, so repeated
  March attempts must not be described as independent seed reruns unless a
  real March perturbation, CNF permutation, or configured March variant is
  added and audited.
- CaDiCaL rerun portfolio with fixed seed/configuration order, for example
  `cadical_seed1`, `cadical_plain_seed1`, and `cadical_shuffle_seed1`.
- mixed March+CaDiCaL extra-budget portfolio with a fixed dev-derived
  schedule.

The non-neural schedules are pre-registered before held-out evaluation. They
are not oracle portfolios. The dev artifact freezes the budget rule and
solver/config cycle: dev neural summary path, its SHA256 hash,
`source_split=dev`, attempt limit, solver/config cycle, and the representative
dev schedule. On held-out, the same frozen cycle may be expanded per instance
to match that instance's neural allocated residual CPU budget; this uses only
the frozen selector's allocated budget, not held-out solve outcomes. The final
protocol audit rejects schedules derived from held-out summaries, schedules
that contain only a single default CaDiCaL configuration, and per-instance
schedules that cannot be recomputed from the frozen cycle and attempt limit.

## Paper-Worthy Criteria

The pilot all-49 gate is only a checkpoint feasibility test. A paper-worthy
result requires a larger held-out residual set.

Minimum paper-worthy evidence:

- selected neural portfolio solves more held-out residual instances than the
  same-budget non-neural rerun portfolio
- the comparison uses the same residual incremental CPU budget
- the result is reported over the full candidate denominator, not only over
  hand-picked solved cases

Strong paper evidence:

- selected neural portfolio solves a nontrivial set of residual instances that
  the same-budget non-neural portfolio still does not solve
- the gain persists on a larger held-out transition-band residual pool
- repeated sample seeds or repeated residual sets show the effect is stable

## Main Table Template

| quantity | value |
| --- | --- |
| candidate instances `N` | |
| March solved | |
| CaDiCaL solved | |
| March+CaDiCaL union solved | |
| both-unknown residual `R` | |
| oracle neural coverage | |
| fixed selected neural residual solves | |
| fixed same-budget non-neural residual solves | |
| neural-only over non-neural | |
| non-neural-only over neural | |
| residual CPU budget | |
| residual wall-clock budget | |

## Stop Conditions

Stop selector work if oracle coverage is sparse. If the all-49 pilot produces
only one or two oracle-positive instances, the current checkpoint is not a
viable top-conference performance model. The next route is model-side:

- hard-instance finetuning
- strong-union-unsolved targeted objective
- sampled policy entropy/diversity objective
- residual-distribution training

The concrete fallback plan is documented in
`docs/top_conference_residual_targeted_training_plan.md`. Selector work can
resume only after a new checkpoint passes the same all-49 oracle gate or a
pre-registered replacement pilot gate on a larger residual pool.
