# End-to-End Portfolio Runner Gap

Goal: turn the promising `Local 5s -> CaDiCaL 55s` result into a
paper-ready portfolio experiment.

## Current Evidence

The current strongest portfolio evidence is:

```text
docs/portfolio_local5_cadical55_eval.md
runs/analysis/portfolio_local5_cadical55/full_summary.csv
```

It reports:

| Schedule | Solved | Delta vs CaDiCaL 60s | CaDiCaL-only losses |
| --- | ---: | ---: | ---: |
| CaDiCaL 60s | 75/200 | 0 | - |
| imported Local-5s + rerun CaDiCaL-55s | 79/200 | +4 | 0 |

This is stronger than a pure simulated portfolio because the second stage
reruns CaDiCaL under a real 55s limit. However, it is not yet a complete
end-to-end portfolio run because the Local first-stage outcome is imported
from existing full400 3-seed mean times.

## Why the Existing Guided Evaluator Is Not Enough

The guided evaluator is organized as a batch pipeline:

1. load a batch of CNFs;
2. run neural inference to produce one-shot guidance;
3. run one or more warmup solver probes;
4. attach event state / selector features;
5. run the final weighted solver call;
6. aggregate total time after all stages finish.

The official Local Boundary Correction config also uses multi-point warmup:

```text
feedback_refinement.intervention_conflicts: [500, 750, 1000, 2000]
feedback_refinement.warmup_cpu_lim: 15
```

Therefore, simply overriding `solver.params.cpu-lim=5` does not implement
"run the complete Local workflow for 5 seconds." It changes only the final
solver call and leaves warmup / neural stages outside a true per-instance
wall-clock budget. It can also turn the first stage into a different method.

## Minimal Engineering Requirement

A paper-ready end-to-end runner needs a per-instance wall-clock controller:

1. Start a timer for one CNF.
2. Run the Local Boundary Correction workflow until either:
   - the workflow proves SAT/UNSAT within 5s total wall-clock, or
   - the 5s budget expires.
3. If the first stage solved, record the Local result and stop.
4. If it did not solve, run CaDiCaL on the same CNF with the remaining 55s.
5. Record a single per-instance portfolio row with:
   - first-stage status and wall time;
   - second-stage status and wall time;
   - final portfolio result and total wall time;
   - whether the run is portfolio-only, CaDiCaL-only, or both.

The clean implementation is not to tune the selector. It is to refactor the
guided evaluation path so it can run one CNF at a time under an external
wall-clock budget.

## Small Code Probe

A local probe added external timeout handling to the underlying solver
wrapper, and direct Glucose smoke calls correctly returned `TIMEOUT` with
`external_timeout=True` and `CPU time` equal to the external timeout.

This is only a low-level building block. It does not solve the full
end-to-end issue because the Local workflow budget spans neural inference,
warmup probes, selector construction, and final solving.

## Decision

The portfolio direction is now worth a real engineering pass because the
current partial run reaches `79/200`, `+4` over CaDiCaL 60s, with zero
CaDiCaL-only losses. For a top-conference performance claim, the next hard
gate is:

> implement and run a true per-instance interrupted `Local 5s -> CaDiCaL 55s`
> portfolio over full400.

If the true end-to-end run remains near `79/200`, the paper can credibly
move toward neural/CDCL complementarity. If it drops to CaDiCaL-level, the
portfolio angle should stay as analysis and the paper should return to
risk-controlled neural guidance under strong-CDCL reference.
