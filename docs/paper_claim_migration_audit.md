# Paper Claim Migration Audit

Scope: align the manuscript direction with the strongest current evidence.
This is a claim audit, not a model-change plan.

## Current Evidence Pivot

The older manuscript direction was neural-workflow internal:

- One-shot -> Online-Consistent Selector.
- Local Boundary Correction as guarded ablation.
- Main full400 table: neural methods under Glucose, with CaDiCaL only as an
  appendix baseline reference.

The strongest current top-conference evidence is now portfolio-level:

- End-to-end `Local Boundary Correction 5s -> CaDiCaL 55s` solves
  `79-80/200` over three full400 repeats.
- CaDiCaL 60s baseline solves `75/200`.
- The portfolio improves by `+4` to `+5` solved instances with zero
  CaDiCaL-only losses across the three repeats.
- Strict neural-first complement is smaller but real: 3 stable instances are
  solved by Local within 5s while CaDiCaL 60s times out.
- The remaining portfolio-only evidence is second-stage CaDiCaL
  cutoff/runtime-boundary behavior and must not be described as a neural
  solve.

Authoritative sources:

```text
docs/portfolio_e2e_local5_cadical55_stability.md
docs/portfolio_claim_split.md
runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv
runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split.csv
```

## Must Fix Before Top-Conference Submission

1. Change the paper's top-line claim from neural-only improvement to
   neural/CDCL portfolio complementarity.

   Current mismatch:

   - `paper/main.tex` title, abstract, introduction, main results, discussion,
     and conclusion still frame Online-Consistent Selector as the central
     result.
   - This is internally correct for the neural workflow, but it is weaker than
     the current portfolio evidence and does not answer the strong-CDCL
     baseline question sharply enough.

   Required replacement:

   - Main result should be the end-to-end `Local 5s -> CaDiCaL 55s` portfolio:
     `79-80/200` vs CaDiCaL `75/200`, zero CaDiCaL-only losses.
   - Online-Consistent Selector and Local Boundary Correction should become the
     neural-first stage and mechanism analysis.

2. Split portfolio-only evidence into neural-first complement and runtime
   boundary evidence.

   Required wording:

   - Stable neural-first complement: `3sat_132.cnf`, `3sat_140.cnf`,
     `3sat_25.cnf`.
   - Stable second-stage runtime-boundary evidence: `3sat_111.cnf`.
   - Boundary-sensitive second-stage runtime-boundary evidence: `3sat_48.cnf`.

   Forbidden wording:

   - Do not say the neural method alone contributes all `+4` to `+5` solved
     instances.
   - Do not call second-stage CaDiCaL solves neural solves.

3. Replace or demote the current main table.

   Current `paper/main.tex` Table 1 is a neural-only full400 robustness table:

   - One-shot `48/200`.
   - Online-Consistent Selector `53/200`.
   - Old Compact `54/200`.
   - + Local Boundary Correction `54/200`.

   Required new main table:

   - CaDiCaL 60s baseline: `75/200`.
   - Local5 -> CaDiCaL55 portfolio repeats: `79, 80, 80`.
   - Delta vs CaDiCaL: `+4, +5, +5`.
   - CaDiCaL-only losses: `0, 0, 0`.
   - Local first-stage solves: `40, 40, 40`.

   The neural-only table can remain as a mechanism/ablation table.

4. Update abstract and conclusion.

   Current abstract says the main empirical result is Online-Consistent
   Selector improving One-shot from `48/200` to `53/200`.

   Required abstract claim:

   - The neural workflow alone gives a stable improvement over one-shot but
     does not beat Old Compact or CaDiCaL.
   - As a neural-first/CDCL-second portfolio, Local5 -> CaDiCaL55 solves
     `79-80/200` vs `75/200` for CaDiCaL 60s.
   - The strict neural-first contribution is 3 stable CaDiCaL-unsolved
     early solves; additional portfolio-only cases include CaDiCaL
     runtime-boundary behavior.

5. Reframe related work and novelty.

   Current Related Work says the selector is narrower than a solver portfolio.
   That was true for the old framing, but the new strongest result is a real
   portfolio schedule.

   Required distinction:

   - SATzilla-style work selects among solvers per instance.
   - This work uses neural guidance as a cheap first-stage complement, then
     falls back to a strong CDCL solver.
   - The novelty is the event-conditioned, risk-controlled neural first stage
     and evidence that it creates nonzero complementarity with CaDiCaL.

## Should Fix If Time Allows

1. Add a paper-ready portfolio table and figure.

   The table is ready from CSV. A figure would help:

   - Bar/table: CaDiCaL 60s vs portfolio repeats.
   - Stacked contribution: Local first-stage solves, CaDiCaL second-stage
     solves, portfolio-only claim split.

2. Run one more robustness check only if resources allow.

   Useful but not mandatory:

   - Repeat CaDiCaL 60s baseline three times to test whether baseline `75/200`
     itself varies like the 55s second-stage boundary cases.
   - This is especially relevant because `3sat_111.cnf` and `3sat_48.cnf`
     show runtime-boundary behavior.

3. Decide whether to keep the neural-only cactus plot as Figure 1.

   If the paper becomes portfolio-first, Figure 1 should probably be a
   portfolio result or contribution split figure. The neural cactus can move to
   mechanism analysis.

## Can Defer To Appendix

- Old neural-only historical single-run `50 -> 56 -> 56`.
- no750 diagnostic.
- polarity / SBE.
- pairwise veto.
- compact stable.
- detailed boundary open-set audit.

## Recommended New Paper Structure

1. Introduction: neural guidance can complement strong CDCL when used as a
   cheap first-stage filter, but unsafe neural intervention needs risk control.
2. Method: Online-Consistent Selector and Local Boundary Correction define the
   neural first stage.
3. Portfolio schedule: run Local Boundary Correction for 5s, then CaDiCaL for
   55s on unsolved instances.
4. Main experiments: CaDiCaL 60s vs end-to-end portfolio repeats.
5. Mechanism analysis: neural-only full400 table, overlap audit, claim split,
   local boundary correction ablation.
6. Limitations: full400 only, runtime-boundary behavior, strict neural-first
   complement is 3 stable instances, not the entire +4/+5 portfolio delta.

## Next Concrete Edit

Before editing `paper/main.tex`, first update `docs/paper_tables_and_figures.md`
with a new Table 1 for the portfolio result and demote the old Table 1 to a
mechanism table. Then update the LaTeX from that single table source.
