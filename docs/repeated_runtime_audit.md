# Repeated Runtime Audit

This audit only checks runtime stability for two fixed paper claims:

1. Whether the six `50 -> 56` recovered timeouts remain stable.
2. Whether the four guarded Local Boundary Correction open-set cases remain stable.

It does not change the model, thresholds, configs, or solver seed.

Source CSV:

- `runs/analysis/repeated_runtime_audit.csv`

| instance | comparison | stable? | interpretation |
| --- | --- | --- | --- |
| `3sat_163.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_188.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_189.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_85.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_89.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_97.cnf` | One-shot vs Online-Consistent Selector | yes | recovered timeout stable |
| `3sat_188.cnf` | Online-Consistent Selector vs + Local Boundary Correction | mixed | mild / boundary-sensitive |
| `3sat_196.cnf` | Online-Consistent Selector vs + Local Boundary Correction | yes | stable hard speedup |
| `3sat_46.cnf` | Online-Consistent Selector vs + Local Boundary Correction | yes | stable hard speedup |
| `3sat_66.cnf` | Online-Consistent Selector vs + Local Boundary Correction | yes | neutral timeout |

Notes:

- `3sat_188.cnf` appears in both groups and is treated as boundary-sensitive.
- `3sat_66.cnf` is neutral timeout evidence, not an improvement claim.
- This is same-seed repeated runtime stability, not seed sensitivity.
