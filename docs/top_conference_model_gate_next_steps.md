# Top-Conference Model Gate Next Steps

Scope: model and experiment gates needed before this project can support a
top-conference-level claim. This is not a paper-writing checklist.

## Current Evidence

- Frozen Glucose/Online/Local workflows are dominated by March/CaDiCaL and
  should not be treated as the main performance story.
- March sampled guidance has real complementarity on focused transition-band
  cases, but the strongest evidence is still sample/selector gated rather than
  a broad deployable result.
- Static policy features recover most focused positives at small top-k, but
  are close to random on the tiny focused set.
- A 1s internal March probe now exposes usable progress counters.
- Hand-written early-trace `high_deadends` recovers 4/6 focused seed groups,
  matching the static top-2 gate, but still misses `440/3sat_8.cnf` for seeds
  1729 and 1730.
- Offline learned selectors do not beat the simple early-trace baseline on the
  focused diagnostic.

## Current Best Non-Oracle Gate

Focused instances:

```text
410:3sat_2.cnf
440:3sat_8.cnf
```

Best fixed-budget selector observed so far:

```text
probe_solved_then_high_deadends
num_samples=16
probe_cpu_lim=1.0
top_k=2
solver_seed=1729
```

Result:

```text
4/6 seed groups solved
2/2 instances solved by at least one sample seed
mean total capped CPU: 79.219s
```

This is not enough for a top-conference performance claim because the
low-probability complement case remains seed-sensitive.

## Next Required Experiment

Expand the strong-union-unsolved sampled dataset.

Minimum gate:

- Generate at least 30-50 transition-band instances not solved by the
  March/CaDiCaL union under the same nominal 60s protocol.
- For each instance, generate 3 sample seeds and 16 March-policy samples per
  seed.
- Run 1s internal March probes for every sample.
- Evaluate fixed top-k selectors without per-instance tuning:
  - low `log_prob`
  - high `weight_std`
  - high `probe_dead_ends_in_main`
  - high `probe_unitResolveCount`
  - learned RF/logistic trained only on held-out folds

Hard success criteria:

- Nonzero neural-only solves against the March/CaDiCaL union on held-out
  instances.
- Fixed selector recovers most oracle sampled solves at top-2 or top-4.
- Selected-sample wall-clock budget remains competitive with simply rerunning
  strong solvers.
- Learned selector must beat the best simple baseline on held-out instances
  before it can be claimed as a method contribution.

Failure criteria:

- If neural-only solves are rare or vanish on the expanded set, stop the
  selector route and retrain the March policy objective toward
  strong-union-unsolved instances.
- If oracle solves exist but no fixed selector recovers them at reasonable
  top-k, switch from static/probe rules to a learned stopping policy or
  training objective; do not keep hand-tuning rules on focused cases.

## Implementation Hygiene

- Use per-group raw artifacts for long runs.
- Keep `--resume` enabled for staged runs.
- Do not reuse focused-case labels for final held-out claims.
- Do not present oracle sampled solves as a deployable method.
