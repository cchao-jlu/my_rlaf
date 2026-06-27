# Residual-Targeted Training Plan

## Purpose

This is the fallback mainline if the all-49 oracle pilot shows sparse sampled
coverage for the current March-trained checkpoint.

The goal is not to tune a selector around rare wins. The goal is to train a
policy whose sampled restarts have nontrivial coverage on instances left
unsolved by the fixed March/CaDiCaL union.

## Trigger

Switch to this plan when the pre-registered all-49 pilot gate reports:

```text
oracle sampled coverage <= 2/49
```

Do not tune `top-k`, `dead_ends`, probe thresholds, learned selectors, or
adaptive schedules for that checkpoint after this failure. Selector work can
resume only after a new checkpoint passes the same oracle gate.

## Training Objective

Train toward the residual distribution, not the original broad 3SAT training
distribution.

Primary target:

```text
maximize sampled solve coverage on March/CaDiCaL both-unknown transition-band
instances under a fixed sample budget
```

Secondary targets:

- preserve performance on easier transition-band instances so the policy does
  not become a narrow memorized perturbation
- increase diversity across sampled restarts for a fixed checkpoint
- reduce repeated generation of near-identical failing March weight vectors

## Data

Use three disjoint pools.

| split | source | purpose |
| --- | --- | --- |
| residual-train | March/CaDiCaL both-unknown candidates not in all-49 | policy update |
| residual-dev | held out from training | checkpoint selection and objective ablation |
| residual-heldout | held out before any ablation | final portfolio protocol only |

The all-49 pilot remains a checkpoint gate and diagnostic set. It must not
become the final held-out set after training decisions have used it.

## Candidate Generation

Generate a larger transition-band candidate pool before training.

Recommended first expansion:

```text
sizes: 410, 425, 440
instances per size: at least 300
March cap: 60s
CaDiCaL cap: 60s
residual filter: both unknown
```

If the residual count is still too small, expand around the transition band:

```text
sizes: 405, 410, 415, 425, 435, 440, 445
```

Report the full denominator:

- candidate instances
- March solved
- CaDiCaL solved
- union solved
- both-unknown residual count

Run the larger strong-solver gate into a new namespace so the existing all-49
pilot artifacts remain immutable:

```bash
python run_transition_band_expanded_gate.py \
  --sizes 410 425 440 \
  --instances 300 \
  --seed 2041 \
  --limit 60 \
  --timeout 65 \
  --workers 8 \
  --data-root data/benchmark_transition_band_residual_large/3sat \
  --out-dir runs/analysis/benchmark_transition_band_residual_large \
  --doc-path docs/benchmark_transition_band_residual_large_gate.md
```

## Loss Variants

Start with the smallest model-side changes that directly address sparse
coverage.

### Variant A: Residual GRPO

Use the existing RLAF/GRPO training path, but train on residual-train CNFs and
score samples by capped March solve progress.

Reward priority:

```text
solved within cap
then lower capped CPU
then lower dead_ends_in_main / decisions for unsolved samples
```

This tests whether the current policy family can move probability mass toward
residual solves without new architecture.

Initial config:

```text
configs/config_train_rlaf_march_residual_targeted.yaml
```

This starts from `runs/GNN_March_3SAT/best.pt`, uses the materialized
`residual_train` and `residual_dev` manifests, optimizes a composite capped
March cost, and keeps a KL penalty to the starting checkpoint.

The initial composite is explicitly solved-first:

```text
unsolved_penalty * I[not solved]
+ cpu_weight * log1p(CPU time)
+ deadends_weight * log1p(dead_ends_in_main)
+ decisions_weight * log1p(decisions)
```

GRPO converts lower composite cost within each CNF group into positive
advantage, so solved samples are preferred before runtime/progress tie-breaks.

The full 60s residual GRPO configuration is expensive: one iteration can launch
`cnf_per_iter * num_samples` capped March runs. If it repeatedly fails to
finish an optimizer step, use a staged curriculum rather than restarting the
same configuration. The staged run keeps the same residual split and composite
objective but writes to a separate checkpoint directory and lowers the rollout
cost:

```text
config: configs/config_train_rlaf_march_residual_targeted_stage1.yaml
model_dir: runs/GNN_March_3SAT_ResidualTargetedStage1
cnf_per_iter: 8
num_samples: 8
March cap: 20s
skip_initial_val: true
```

This is not a paper result. It is a model-side step to obtain a checkpoint that
has actually completed GRPO updates on the residual distribution. It can be
promoted to the normal oracle gate only after the log contains
`Optimized model for ...` and `last.pt` has a newer mtime than the source
checkpoint.

Use a checkpoint-specific oracle namespace for this curriculum, for example
`benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_stage1`.
If validation has not produced `best.pt`, gate `last.pt` and record that exact
path in the gate decision. Do not mix Stage1 oracle artifacts with
`ResidualTargeted` or `ResidualProxyCap10` artifacts.

### Variant B: Hard-Instance Finetuning

Initialize from the current best March-trained checkpoint and finetune only on
residual-train plus a small stabilizer mix of transition-band non-residual
instances.

Suggested mix:

```text
70% residual-train
30% transition-band stabilizer
```

Keep a KL penalty to the base checkpoint so finetuning does not collapse to a
single brittle weighting mode.

### Variant C: Diversity-Regularized Sampling

Add a sample-diversity term within each CNF group. The target is not higher
entropy everywhere; it is more distinct March restart behavior across the
`num_samples` budget.

Track diversity with:

- pairwise cosine distance of sampled variable-weight vectors
- standard deviation of generated weights per instance
- uniqueness of early March probe traces
- oracle solved coverage per instance

Implemented first-pass config:

```text
configs/config_train_rlaf_march_residual_coverage_diverse.yaml
```

It starts from `ResidualTargetedIter22/last.pt`, writes to
`runs/GNN_March_3SAT_ResidualCoverageDiverse`, uses `target_stat:
composite_diverse`, adds an unsolved-only sample-similarity cost inside each
CNF group, and includes a small entropy bonus in GRPO.

Result: the dev-best checkpoint
`runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt` failed the
all-49 oracle gate with `oracle_solved=2/49`. This variant is not sufficient
for selector or same-budget non-neural control work. The next variant must
directly target new residual positives rather than only penalizing within-CNF
sample similarity.

### Variant D: Elite Replay / Hard-Positive Finetuning

If oracle coverage stays sparse after solved-first GRPO and simple diversity,
the next stronger model-side signal is to mine solved sampled-March restarts on
`residual_train`, then explicitly increase their policy probability.

This is not selector tuning and not an oracle paper claim. It is a training
data construction step:

```text
residual_train sampled oracle mining
-> solved sample manifest
-> behavior-cloning / elite replay with KL to source checkpoint
-> residual_dev elite objective checkpoint selection
-> unchanged all-49 oracle gate
```

Implemented utilities:

```text
build_residual_elite_replay_manifest.py
train_residual_elite_replay.py
tests/test_residual_elite_replay.py
```

The manifest records the exact checkpoint, checkpoint SHA256, raw CSV SHA256,
`sample_seed`, `num_samples_generated`, and `sample_id`, so `var_params` can be
reconstructed deterministically without storing large tensors in CSVs.

Current source checkpoint for this branch:

```text
runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt
sha256: c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f
```

Current residual-train mining namespace:

```text
runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2
data/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2
docs/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2.md
```

Partial smoke result:

```text
completed residual_train instances: 23 / 168
positive instances: 7
solved samples: 55
positive:
  - 410/3sat_122.cnf, solved_samples=2/16, best_time=56.9111, best_sample_id=5
  - 410/3sat_13.cnf, solved_samples=15/16, best_time=55.4571, best_sample_id=2
  - 410/3sat_160.cnf, solved_samples=7/16, best_time=54.9684, best_sample_id=14
  - 410/3sat_172.cnf, solved_samples=3/16, best_time=58.4589, best_sample_id=2
  - 410/3sat_216.cnf, solved_samples=13/16, best_time=57.7088, best_sample_id=9
  - 410/3sat_235.cnf, solved_samples=8/16, best_time=58.1850, best_sample_id=5
  - 410/3sat_247.cnf, solved_samples=7/16, best_time=54.7944, best_sample_id=14
```

The long residual-train mining run is active outside the sandbox:

```text
pid: 2214783
log: runs/analysis/benchmark_transition_band_residual_large/logs/residual_train_elite_mining_coverage_diverse_best_iter2.log
```

Do not start another March-heavy gate/training run while this is active. Once
train positives are available, run the same mining protocol on `residual_dev`
for checkpoint selection. Do not use residual-heldout for mining or checkpoint
selection.

Current decision:

```text
min_positive_instances_for_replay=8
decision=continue_mining
```

Use `summarize_residual_elite_mining.py` to update the progress snapshot
without running solvers.

Formal train/dev elite manifests should be generated with
`--min-positive-instances 8`; the builder refuses sparse formal manifests under
that guard. This keeps partial smoke/progress artifacts from being accidentally
used as replay training data.

Formal manifests should also use `--require-raw-complete`, so a partial mining
snapshot cannot become the replay training set just because it reached the
positive floor early. Treat the positive floor as a readiness signal; build the
formal train/dev manifests from complete split-mining snapshots.

Raw completeness means more than one row per split instance: the raw source
must exactly cover the split, all instances must share the same mining
`sample_seed` set, and every instance/seed must contain the complete
`sample_id=0..num_samples_generated-1` grid without duplicates. This prevents a
truncated `raw_samples_all.csv` from becoming a formal replay source.

`summarize_residual_elite_mining.py` reports `positive_floor_met`,
`complete_mining`, and `raw_artifacts_complete`. Its `decision` should be
`ready_for_formal_elite_manifest` only when all three are true; otherwise
continue mining or report `complete_but_sparse`. It counts only split members
with audited complete raw grids and reports unexpected artifacts if the mining
directory contains rows from another split/namespace.

Formal replay training should additionally set
`--min-train-positive-instances 8` and a dev-side floor such as
`--min-dev-positive-instances 4`, so the training entry point also rejects
sparse manifests. It also enforces expected train/dev split names and
`source_checkpoint_sha256`, preventing residual-heldout leakage or training
from elites mined by a different checkpoint. Row-limited manifest training is
rejected unless explicitly marked as smoke/debug via
`--allow-partial-manifest-training`; checkpoints from row-limited training must
not be gated. The dev manifest remains a checkpoint-selection artifact, not
final held-out evidence.

The replay training config records source checkpoint SHA256, train/dev manifest
SHA256, elite row counts, positive-instance counts, expected train/dev splits,
row-limit settings, and the positive floors used by the training entry point.
Keep this provenance with the checkpoint before running the all-49 gate.
`audit_residual_elite_replay_manifest.py` can also audit the replay training
config against the formal train/dev manifests, source checkpoint hash, row
counts, positive counts, split guards, row-limit guards, and guard thresholds.

Formal result: the replay branch completed train/dev manifest finalization,
training, config audit, all-49 oracle diagnostic, and gate decision. The
dev-selected checkpoint failed the pre-registered gate:

```text
checkpoint: runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf
  - 425/3sat_28.cnf
```

Consequence: stop selector work and do not rerun elite replay as-is. The
failure mode is not a selector problem; the checkpoint still has sparse oracle
coverage and no `size=440` all-49 coverage.

### Variant E: Residual Progress-Diverse GRPO

The next model-side branch directly rewards useful residual-search progress
for unsolved samples and upweights harder residual sizes.

Implemented config:

```text
configs/config_train_rlaf_march_residual_progress_diverse.yaml
model_dir: runs/GNN_March_3SAT_ResidualProgressDiverse
from_checkpoint: runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt
target_stat: composite_progress_diverse
rollout: 12 CNFs x 12 samples x 30s March cap
size advantage weights: 410=1.0, 425=1.25, 440=1.6
```

The target is solved-first, but for unsolved samples it subtracts a progress
reward from the cost:

```text
progress_reward =
  0.22 * log1p(dead_ends_in_main)
  + 0.08 * log1p(decisions)
```

Then it adds the within-CNF sample-similarity cost and a small entropy bonus.
This is designed to avoid only cloning the sparse elite positives and instead
favor samples that push March deeper on residual instances, especially
`size=440`.

This branch has now been gated with the unchanged all-49 protocol and failed:

```text
checkpoint: runs/GNN_March_3SAT_ResidualProgressDiverse/best.pt
sha256: f9ac184722fe5785c3b084c2e173e8d799ae13a7d2b1a151887e66d4d662997a
decision: fail
total: 49
oracle_solved: 1
positive:
  - 410/3sat_12.cnf, solved_samples=8/16, best_time=6.5103, best_sample_id=2
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse.md`
- `docs/residual_portfolio_gate_decision_residual_progress_diverse.md`

Consequence: stop this objective too. Do not tune selectors, do not touch
held-out, and do not rerun solved-first/progress-diverse GRPO as-is.

Before replay training, run `audit_residual_elite_replay_manifest.py` on both
formal train and dev manifests. The audit checks split membership, positive
floor, checkpoint/raw hashes, CNF paths, `sample_id` range, and solved raw
sample provenance.

The residual-dev mining/build path must mirror residual-train in a separate
namespace, using strict summarize-only and `--require-raw-complete` before
building `residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv`.
Residual-heldout remains untouched until the final fixed portfolio protocol.
Use `finalize_residual_elite_manifest.py` for both train and dev finalization
so the progress readiness gate, strict summarize-only, manifest build, and
audit are executed as one guarded sequence.

Do not train elite replay from the all-49 positives. The all-49
`ResidualTargetedIter22` positives were used only to smoke-test deterministic
reconstruction and checkpoint saving.

### Variant F: Coverage-Balanced Residual Supervision

The next feasible branch should use the existing mined residual train/dev
positives, but change the loss so it optimizes coverage rather than only
fastest-elite likelihood.

Current mined positive signal from `ResidualCoverageDiverseBestIter2`:

```text
residual_train elite manifest:
  rows: 109
  positive instances: 30
  by size: 410=12, 425=11, 440=7

residual_dev elite manifest:
  rows: 17
  positive instances: 7
  by size: 410=3, 440=4
```

This is enough for a small supervised residual-policy experiment, but not
enough to claim a method. The objective should:

- sample/balance by residual instance, not by elite row
- increase log-probability of solved elite samples
- contrast against failed samples from the same CNF and same mining protocol
- use a margin or pairwise ranking loss so solved samples beat same-instance
  failures
- keep KL to the source checkpoint
- select checkpoints only on residual_dev coverage-balanced objective

If CPU budget allows, first expand residual_train/dev mining with additional
sample seeds in fresh namespaces. Otherwise start with the existing manifests
as a model-side proof-of-life. In both cases, the next checkpoint must return
to the unchanged all-49 oracle gate. Selector/protocol freeze resumes only if
the all-49 gate reaches `oracle_solved >= 5/49`.

First-pass implementation:

```text
build_residual_contrastive_replay_manifest.py
train_residual_contrastive_replay.py
tests/test_residual_contrastive_replay.py
```

The first contrastive checkpoint completed training and failed the unchanged
all-49 gate:

```text
checkpoint: runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2/best.pt
checkpoint sha256: 56dba0670da653bea7a8106c5db2ca34463928bd8f13c5bb302dd47da313562c
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf
  - 425/3sat_28.cnf
size-440 positives: 0/30
```

This restores the two recurring positives but does not improve coverage. The
training metrics show the pairwise term staying near `0.69` while both positive
and negative log-probs decline, so the next model-side change should fix the
contrastive loss sign/normalization or expand mining seeds before rebuilding
manifests. Do not enter selector or held-out protocol work for this checkpoint.

## Gates

Each new checkpoint must pass the same gate before selector work resumes.

| gate | condition | action |
| --- | --- | --- |
| fail | oracle `<=2/49` | keep training-objective work |
| marginal | oracle `3-4/49` | expand residual pilot or improve training |
| pass | oracle `>=5/49` | proceed to dev-only selector tuning |

A checkpoint is paper-track only if it later beats the same-budget non-neural
rerun portfolio on held-out residual instances.

## Required Artifacts

For every training variant, keep:

- config file
- checkpoint path
- residual split manifest
- training seed
- solver seed
- oracle gate command
- oracle gate output directory
- all-49 gate result
- dev selector result, only if the gate passes

## First Concrete Step

If the current all-49 pilot fails, create a larger residual candidate pool and
write immutable split manifests before running any new training.

The next implementation task is:

```text
build residual-train/dev/heldout manifests from a larger March/CaDiCaL
both-unknown transition-band pool
```

Use the manifest builder after the larger gate finishes:

```bash
python build_residual_split_manifest.py \
  --input runs/analysis/<larger_residual_gate>/both_unknown_subset.csv \
  --cnf-root data/<larger_residual_gate> \
  --exclude-csv runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/both_unknown_subset.csv \
  --output-dir runs/analysis/<larger_residual_gate>/residual_split_seed1729 \
  --doc docs/<larger_residual_gate>_residual_split_seed1729.md \
  --seed 1729 \
  --train-frac 0.5 \
  --dev-frac 0.25 \
  --materialize symlink
```

The `--exclude-csv` argument prevents the all-49 pilot gate from becoming
training data. The manifest records the input CSV hash, split seed, split
counts, and CNF paths so later selector and held-out evaluations can be audited.
