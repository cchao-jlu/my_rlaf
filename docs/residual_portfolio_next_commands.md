# Residual Portfolio Next Commands

## Completed Pilot: ResidualProxyCap10 Iter0

This all-49 oracle pilot is checkpoint-specific. Do not mix its result with
the historical `runs/GNN_March_3SAT/best.pt` gate below.

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --checkpoint runs/GNN_March_3SAT_ResidualProxyCap10/last.pt \
  --out-dir runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0 \
  --subset-root data/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0 \
  --doc docs/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu
```

Official result:

```text
decision=fail
total=49
oracle_solved=1
positive: 410/3sat_12.cnf, solved_samples=8/16, best_time=10.875, best_sample_id=5
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_proxy_cap10_iter0.md`
- `docs/residual_portfolio_gate_decision_residual_proxy_cap10_iter0.md`

Consequence:

```text
Stop selector work for runs/GNN_March_3SAT_ResidualProxyCap10/last.pt.
Do not enter dev-only selector freeze or held-out same-budget control for this checkpoint.
Return to residual-targeted / diversity / entropy training objectives, then rerun the same gate for a new checkpoint.
```

## Historical Pilot: Base March Checkpoint

The historical all-49 pilot for `runs/GNN_March_3SAT/best.pt` failed:

```text
decision=fail
total=49
oracle_solved=1
```

Therefore selector tuning for `runs/GNN_March_3SAT/best.pt` is stopped.
`ResidualProxyCap10/last.pt` has now also failed its checkpoint-specific gate.

Strict-60 note: after correcting the strong-solver denominator to exclude
solutions returned after the nominal 60s cap, the historical expanded pilot has
52 residual instances rather than 49. The `1/49` gate is still sufficient to
stop selector tuning for the current checkpoint, but any future gate should use
the strict residual CSV and a separate artifact namespace:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --input runs/analysis/benchmark_transition_band_expanded_strict60_smoke/both_unknown_subset.csv \
  --source-root data/benchmark_transition_band_expanded \
  --out-dir runs/analysis/benchmark_march_expanded_strict60_sample_portfolio_oracle \
  --subset-root data/benchmark_march_expanded_strict60_sample_portfolio_oracle \
  --doc docs/benchmark_march_expanded_strict60_sample_portfolio_oracle.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu
```

Then decide it with the strict denominator:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python decide_residual_portfolio_gate.py \
  --instance-oracle runs/analysis/benchmark_march_expanded_strict60_sample_portfolio_oracle/instance_oracle_summary.csv \
  --output docs/residual_portfolio_gate_decision_strict52.md \
  --gate-name strict52 \
  --expected-total 52 \
  --fail-max 2 \
  --pass-min 5
```

Formal gate decisions are fail-closed: `decide_residual_portfolio_gate.py`
requires the oracle CSV denominator to match `--expected-total`, rejects
duplicate instance keys, and parses `solved_any` strictly so string `False` is
not counted as solved. Use `--allow-diagnostic-total` only for explicitly
non-formal monitoring summaries.

## If Gate Fails

The expected failure condition is:

```text
oracle solved <= 2/49
```

Do not tune selectors for that checkpoint. Generate a larger residual pool:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_transition_band_expanded_gate.py \
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

Monitor the long-running gate:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python monitor_transition_band_gate.py \
  --raw-dir runs/analysis/benchmark_transition_band_residual_large/raw \
  --sizes 410 425 440 \
  --instances 300
```

Before the larger gate is used for training or evaluation, lock the full
candidate denominator with a candidate-level split. This can be done while the
solver gate is still running, because it depends only on the generation spec:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python build_candidate_split_manifest.py \
  --sizes 410 425 440 \
  --instances 300 \
  --generation-seed 2041 \
  --split-seed 1729 \
  --train-frac 0.5 \
  --dev-frac 0.25 \
  --cnf-root data/benchmark_transition_band_residual_large \
  --output-dir runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729 \
  --doc docs/benchmark_transition_band_residual_large_candidate_split_seed1729.md
```

After the larger gate finishes, project residual splits from that locked
candidate split while excluding the all-49 pilot:

The recommended one-shot finalization command is:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python finalize_residual_large_gate.py
```

It runs strict-60 re-summary, projects the residual split from the candidate
manifest, runs the split/protocol audit in incomplete mode, and verifies that
the residual train/dev CNFs are materialized for training. The script inherits
the same raw-completeness guard as `run_transition_band_expanded_gate.py`.

First rebuild the final strong-gate summary from raw solver artifacts using
the strict nominal 60s cap. This does not rerun solvers; it prevents March
solutions returned after 60s but before the external timeout from shrinking the
residual denominator:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_transition_band_expanded_gate.py \
  --sizes 410 425 440 \
  --instances 300 \
  --seed 2041 \
  --limit 60 \
  --timeout 65 \
  --workers 8 \
  --data-root data/benchmark_transition_band_residual_large/3sat \
  --out-dir runs/analysis/benchmark_transition_band_residual_large \
  --raw-dir runs/analysis/benchmark_transition_band_residual_large/raw \
  --doc-path docs/benchmark_transition_band_residual_large_gate.md \
  --skip-solvers
```

This command intentionally refuses to write `combined.csv` if any raw
size/solver CSV is incomplete. Do not pass `--allow-partial-summary` for a
paper denominator or residual split.

Check that the strong-solver gate has produced the residual subset:

```bash
test -f runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv && \
  wc -l runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv
```

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python build_residual_split_manifest.py \
  --input runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv \
  --cnf-root data/benchmark_transition_band_residual_large \
  --exclude-csv runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/both_unknown_subset.csv \
  --exclude-cnf-root data/benchmark_transition_band_expanded \
  --candidate-manifest runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv \
  --output-dir runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729 \
  --doc docs/benchmark_transition_band_residual_large_residual_split_seed1729.md \
  --seed 1729 \
  --train-frac 0.5 \
  --dev-frac 0.25 \
  --materialize symlink
```

The next model-side task is residual-targeted training from
`docs/top_conference_residual_targeted_training_plan.md`.

Before launching training, verify that the projected residual split has
materialized train/dev CNFs and that the source checkpoint exists:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python audit_residual_training_ready.py \
  --split-manifest runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv \
  --train-glob "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/cnf/residual_train/*/*.cnf" \
  --dev-glob "runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/cnf/residual_dev/*/*.cnf" \
  --checkpoint runs/GNN_March_3SAT/best.pt \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_training_ready_audit_seed1729.csv \
  --doc docs/benchmark_transition_band_residual_large_training_ready_audit_seed1729.md
```

Run the first residual-targeted GRPO finetune:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python train_rlaf.py \
  --config-name config_train_rlaf_march_residual_targeted
```

Current status: the full 60s resume was stopped after freezing a later
checkpoint. The latest checkpoint-specific all-49 oracle gate for this line is:

```text
runs/GNN_March_3SAT_ResidualTargetedIter22/last.pt
sha256: 4cf7537b86c86d8caec832d064ee4704388ec881874d30950930d832fa329058
```

Official gate result:

```text
gate: residual_targeted_iter22_all49
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf, solved_samples=6/16, best_time=1.0505, best_sample_id=11
  - 425/3sat_28.cnf, solved_samples=1/16, best_time=59.2371, best_sample_id=3
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_targeted_iter22.md`
- `docs/residual_portfolio_gate_decision_residual_targeted_iter22.md`

Consequence:

```text
Stop selector work for runs/GNN_March_3SAT_ResidualTargetedIter22/last.pt.
Do not enter dev-only selector freeze or held-out same-budget control for this checkpoint.
Return to model-side residual objective changes, then rerun the same all-49 gate for a new checkpoint.
```

The existing `runs/GNN_March_3SAT_ResidualTargeted/best.pt` still predates this
resume and should not be used for oracle gates. The frozen Iter0 and Iter8
checkpoints are retained as provenance, but the Iter22 gate is the authoritative
checkpoint gate for this training line.

## Next Model-Side Step

Do not keep running the same solved-first composite GRPO configuration. After
22 completed updates it still only reaches `2/49` oracle coverage. The first
coverage/diversity variant below also failed the same all-49 gate, so do not
rerun it as-is.

```text
config: configs/config_train_rlaf_march_residual_coverage_diverse.yaml
model_dir: runs/GNN_March_3SAT_ResidualCoverageDiverse
from_checkpoint: runs/GNN_March_3SAT_ResidualTargetedIter22/last.pt
target_stat: composite_diverse
rollout: 8 CNFs x 8 samples x 20s March cap
```

This kept the solved-first residual objective but added an unsolved-only
sample-similarity penalty inside each CNF group and a small entropy bonus. The
run completed, froze both dev-best and final checkpoints, and gated only the
dev-best checkpoint:

```text
runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt
sha256: c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f

runs/GNN_March_3SAT_ResidualCoverageDiverseFinalIter15/last.pt
sha256: 9fe407aca77ceb4169834aa57815f3b55053f37effe34fb650c0de75abdfd296
```

Official gate result:

```text
gate: residual_coverage_diverse_best_iter2_all49
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf, solved_samples=9/16, best_time=1.4119, best_sample_id=15
  - 425/3sat_28.cnf, solved_samples=1/16, best_time=59.8441, best_sample_id=15
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_coverage_diverse_best_iter2.md`
- `docs/residual_portfolio_gate_decision_residual_coverage_diverse_best_iter2.md`

Consequence: stop selector work for this checkpoint. Do not enter dev-only
selector freeze or held-out same-budget non-neural control. The next
implementation should be a stronger model-side objective, for example
hard-positive replay / residual-positive prioritized finetuning / a targeted
objective that explicitly increases coverage beyond the two recurring positives.

## Current Next Step: Residual Elite Mining

The next active branch is model-side hard-positive replay, not selector tuning.
Two helper scripts are now available:

```text
build_residual_elite_replay_manifest.py
train_residual_elite_replay.py
```

Verified checks:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python -m py_compile \
  build_residual_elite_replay_manifest.py \
  train_residual_elite_replay.py \
  tests/test_residual_elite_replay.py

env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python -m unittest \
  tests.test_residual_elite_replay \
  tests.test_residual_training_objective \
  tests.test_residual_portfolio_protocol
```

Result:

```text
13 tests OK
```

The all-49 `ResidualTargetedIter22` positives were used only as a smoke test:

```text
runs/analysis/benchmark_transition_band_residual_large/residual_targeted_iter22_elite_replay_smoke_manifest.csv
docs/residual_targeted_iter22_elite_replay_smoke_manifest.md
runs/GNN_March_3SAT_ResidualEliteReplaySmoke/
```

Do not gate or report `ResidualEliteReplaySmoke`; it only validates
deterministic sample reconstruction and checkpoint saving.

Formal mining must use residual train/dev, not all-49. The residual-train
mining namespace is:

```text
runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2
data/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2
docs/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2.md
```

Current partial state:

```text
source checkpoint: runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt
source checkpoint sha256: c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f
completed residual_train instances: 23 / 168
3sat/410/3sat_101.cnf: solved_samples=0/16
3sat/410/3sat_102.cnf: solved_samples=0/16
3sat/410/3sat_105.cnf: solved_samples=0/16
3sat/410/3sat_117.cnf: solved_samples=0/16
3sat/410/3sat_122.cnf: solved_samples=2/16, best_time=56.9111, best_sample_id=5
3sat/410/3sat_13.cnf: solved_samples=15/16, best_time=55.4571, best_sample_id=2
3sat/410/3sat_135.cnf: solved_samples=0/16
3sat/410/3sat_136.cnf: solved_samples=0/16
3sat/410/3sat_155.cnf: solved_samples=0/16
3sat/410/3sat_159.cnf: solved_samples=0/16
3sat/410/3sat_160.cnf: solved_samples=7/16, best_time=54.9684, best_sample_id=14
3sat/410/3sat_166.cnf: solved_samples=0/16
3sat/410/3sat_172.cnf: solved_samples=3/16, best_time=58.4589, best_sample_id=2
3sat/410/3sat_19.cnf: solved_samples=0/16
3sat/410/3sat_191.cnf: solved_samples=0/16
3sat/410/3sat_213.cnf: solved_samples=0/16
3sat/410/3sat_216.cnf: solved_samples=13/16, best_time=57.7088, best_sample_id=9
3sat/410/3sat_226.cnf: solved_samples=0/16
3sat/410/3sat_231.cnf: solved_samples=0/16
3sat/410/3sat_235.cnf: solved_samples=8/16, best_time=58.1850, best_sample_id=5
3sat/410/3sat_247.cnf: solved_samples=7/16, best_time=54.7944, best_sample_id=14
3sat/410/3sat_261.cnf: solved_samples=0/16
3sat/410/3sat_269.cnf: solved_samples=0/16
positive_instances: 7
solved_samples: 55
positive_floor_met: false
complete_mining: false
partial_elite_rows: 6
min_positive_instances_for_replay: 8
decision: continue_mining
```

A long residual-train mining run has been started outside the sandbox:

```text
pid: 2214783
log: runs/analysis/benchmark_transition_band_residual_large/logs/residual_train_elite_mining_coverage_diverse_best_iter2.log
```

Monitor it without starting another March-heavy job:

```bash
pgrep -af '[r]un_march_sample_portfolio_multiseed.py|[s]olvers/march_weighted/march_nh'
find runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/instances \
  -maxdepth 1 -name '*_summary.csv' | wc -l
tail -n 40 runs/analysis/benchmark_transition_band_residual_large/logs/residual_train_elite_mining_coverage_diverse_best_iter2.log
```

Use the progress summarizer for a decision-grade snapshot. It does not run
solvers:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  summarize_residual_elite_mining.py \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --instances-dir runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/instances \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_mining_progress_coverage_diverse_best_iter2.csv \
  --remaining-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_mining_remaining_coverage_diverse_best_iter2.csv \
  --doc docs/residual_train_elite_mining_progress_coverage_diverse_best_iter2.md \
  --min-positive-instances 8
```

Current progress artifact:

```text
runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_mining_progress_coverage_diverse_best_iter2.csv
docs/residual_train_elite_mining_progress_coverage_diverse_best_iter2.md
```

The progress decision is `ready_for_formal_elite_manifest` only when
`positive_floor_met=true`, `complete_mining=true`, and
`raw_artifacts_complete=true`. The summary counts only split members whose
per-instance raw grid has been audited, and reports
`unexpected_artifact_instances` if the mining directory contains artifacts from
another split/namespace. If the positive floor is hit before all 168 train
instances complete, keep mining; do not build the formal replay manifest from
the partial raw snapshot.

The formal `--require-raw-complete` guard is stricter than instance coverage:
the raw source must exactly match the split, each instance must have the same
sample-seed set, and every instance/seed must contain a complete
`sample_id=0..num_samples_generated-1` grid with no duplicates. A truncated or
partially summarized raw CSV is not a valid replay source.

Formal train/dev manifest commands should keep `--min-positive-instances 8`.
This is a protocol guard against accidentally training replay from sparse
partial manifests. Omit it only for smoke/debug artifacts that will not be
trained or gated.

If it stops early, resume with the same command. Existing per-instance
artifacts will be skipped:

```bash
cd /home/sunshixin/chenchao/my_rlaf && \
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2 \
  --doc docs/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu
```

After residual-train mining finishes, finalize the formal train manifest with
the guarded finalizer. The safest entry point is
`finalize_residual_train_when_ready.py`: it refuses to run while March mining
processes are still active when they are visible in the local process table,
then refreshes the progress snapshot with `summarize_residual_elite_mining.py`.
It refuses to enter ready/finalizer mode unless the refreshed progress CSV
records `ready_for_formal_elite_manifest`. This refreshed progress check is
the hard guard when sandbox PID isolation hides host-side March processes.
After readiness, it also requires the per-instance and global mining artifacts
to remain unchanged for a short settle window before invoking the finalizer,
so a host-side runner that is still writing final summaries cannot race the
formal summarize-only step.
The delegated finalizer repeats the non-negotiable progress/strict artifact
check: it refreshes the progress snapshot again, checks
`ready_for_formal_elite_manifest`, runs strict summarize-only without
`--allow-partial-summary`, builds the manifest with `--require-raw-complete`,
and runs the audit. The manifest builder and audit also lock the formal
sampling protocol from the finalizer command: raw artifacts must use exactly
the declared `--sample-seeds` set and `--num-samples` value. New raw artifacts
also record the source checkpoint hash; the builder/audit validate that hash
when present while remaining compatible with older in-progress train-mining
raw files that lack it. It parses progress booleans strictly, so string values
like `False` cannot be treated as truthy. If any per-instance raw artifact is
missing, truncated, generated with the wrong sample budget, or records a
different checkpoint hash, it fails and the mining run should be resumed or
rebuilt in a separate namespace.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_train_when_ready.py --dry-run
```

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_elite_manifest.py \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --instances-dir runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/instances \
  --min-positive-instances 8 \
  --progress-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_mining_progress_coverage_diverse_best_iter2.csv \
  --remaining-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_mining_remaining_coverage_diverse_best_iter2.csv \
  --progress-doc docs/residual_train_elite_mining_progress_coverage_diverse_best_iter2.md \
  --portfolio-input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2 \
  --portfolio-doc docs/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu \
  --manifest-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --manifest-doc docs/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.md \
  --audit-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --audit-doc docs/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.md \
  --expected-split residual_train \
  --max-per-instance 4
```

The equivalent manual commands are still valid for debugging, but do not skip
any of the four steps: progress gate, strict summarize-only, guarded manifest
build, and audit.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  audit_residual_elite_replay_manifest.py \
  --manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --expected-split residual_train \
  --min-positive-instances 8 \
  --max-per-instance 4 \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --doc docs/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.md
```

If train positives are still sparse, do not train from all-49 positives. Expand
train mining seeds or change the model-side objective again. If train positives
are adequate, run the same mining protocol on residual-dev for checkpoint
selection, then train `train_residual_elite_replay.py` and gate the dev-selected
checkpoint with the unchanged all-49 protocol.

Launch residual-dev mining only after residual-train mining has finished and
the train manifest audit has passed. Use the guarded launcher below; it refuses
to run if the train mining progress is not ready, if the train manifest audit
is missing/failing, if the audit CSV does not contain the required formal train
manifest checks, or if March/replay/training processes are still active when
visible. Keep held-out untouched:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python launch_residual_dev_elite_mining.py \
  --train-manifest-audit runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2 \
  --doc docs/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu \
  --detached
```

After residual-dev mining finishes, finalize the formal dev manifest with the
same guarded finalizer. It requires dev mining to be complete and positive
floor to be met before strict summarize-only/build/audit, and it applies the
same expected `sample_seeds` / `num_samples` protocol checks as the train
manifest:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_elite_manifest.py \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --instances-dir runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/instances \
  --min-positive-instances 4 \
  --progress-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_mining_progress_coverage_diverse_best_iter2.csv \
  --remaining-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_mining_remaining_coverage_diverse_best_iter2.csv \
  --progress-doc docs/residual_dev_elite_mining_progress_coverage_diverse_best_iter2.md \
  --portfolio-input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2 \
  --portfolio-doc docs/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu \
  --manifest-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --manifest-doc docs/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.md \
  --audit-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --audit-doc docs/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.md \
  --expected-split residual_dev \
  --max-per-instance 4
```

The dev finalizer already runs the audit below. Use this manual audit only for
debugging or re-checking an existing manifest:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  audit_residual_elite_replay_manifest.py \
  --manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --expected-split residual_dev \
  --min-positive-instances 4 \
  --max-per-instance 4 \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --doc docs/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.md
```

Formal replay training should also keep a second guard at the training entry
point, so a sparse manifest cannot be trained by bypassing the manifest
builder. The training entry point also rejects manifest split mismatches and
`source_checkpoint_sha256` mismatches, so residual-heldout artifacts or elites
mined by another checkpoint cannot be silently trained. It also rejects
row-limited manifest training unless `--allow-partial-manifest-training` is
explicitly set for smoke/debug runs; such checkpoints must not be gated. The
saved replay `config.yaml` records train/dev manifest SHA256, source checkpoint
SHA256, elite row counts, positive-instance counts, expected train/dev splits,
expected train/dev sampling budgets, row-limit settings, and the train/dev
positive floors used for the run:

The preferred formal entry point is the guarded two-stage pipeline below. The
`train_audit` stage refuses to start unless train/dev manifest audits already
pass and contain the required formal manifest checks, then trains replay and
audits the saved replay config. After that, run the all-49 oracle diagnostic
for `model-dir/best.pt` in its own namespace. Only then run the `gate` stage,
which requires the formal replay training-config audit checks and binds that
audit plus the oracle artifact into the all-49 gate decision.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_elite_replay_pipeline.py \
  --stage train_audit \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --train-manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --dev-manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --train-split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --train-manifest-audit runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --dev-manifest-audit runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --model-dir runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2 \
  --epochs 8 \
  --batch-size 8 \
  --lr 5e-6 \
  --kl-penalty 0.05 \
  --min-train-positive-instances 8 \
  --min-dev-positive-instances 4 \
  --expected-train-split residual_train \
  --expected-dev-split residual_dev \
  --expected-train-sample-seeds 1729 \
  --expected-dev-sample-seeds 1729 \
  --expected-train-num-samples 16 \
  --expected-dev-num-samples 16 \
  --training-config-audit-csv runs/analysis/benchmark_transition_band_residual_large/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.csv \
  --training-config-audit-doc docs/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.md
```

Then run the all-49 oracle diagnostic on the replay `best.pt`. This is the
expensive solver stage and should use a separate artifact namespace:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --checkpoint runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2 \
  --doc docs/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu \
  --resume
```

After the oracle diagnostic finishes, run the `gate` stage:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_elite_replay_pipeline.py \
  --stage gate \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --train-manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --dev-manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --train-split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --train-manifest-audit runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --dev-manifest-audit runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_audit_coverage_diverse_best_iter2.csv \
  --model-dir runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2 \
  --training-config-audit-csv runs/analysis/benchmark_transition_band_residual_large/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.csv \
  --training-config-audit-doc docs/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.md \
  --oracle-summary runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv \
  --gate-output docs/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.md \
  --gate-record-json runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.json \
  --gate-name residual_elite_replay_coverage_diverse_best_iter2_all49 \
  --expected-total 49 \
  --fail-max 2 \
  --pass-min 5
```

Official result:

```text
gate: residual_elite_replay_coverage_diverse_best_iter2_all49
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf, solved_samples=9/16, best_time=8.1456, best_sample_id=4
  - 425/3sat_28.cnf, solved_samples=1/16, best_time=39.5187, best_sample_id=14
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2.md`
- `docs/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.md`
- `runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.json`

Consequence:

```text
Stop selector work for runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt.
Do not enter dev-only selector freeze or held-out same-budget control for this checkpoint.
Do not rerun elite replay as-is; it only increased probability of existing sparse positives.
```

The sample-portfolio runner now takes a nonblocking lock in each `--out-dir`.
If a second runner tries to write the same namespace, it fails instead of
concurrently overwriting raw/summary/global artifacts. Use a separate
namespace for any diagnostic rerun.

## Completed Failed Branch: ResidualProgressDiverse

This checkpoint directly rewarded residual-search progress and hard-size
coverage, rather than only cloning solved elite samples:

```text
configs/config_train_rlaf_march_residual_progress_diverse.yaml
model_dir: runs/GNN_March_3SAT_ResidualProgressDiverse
from_checkpoint: runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt
target_stat: composite_progress_diverse
rollout: 12 CNFs x 12 samples x 30s March cap
size advantage weights: 410=1.0, 425=1.25, 440=1.6
```

Final training state:

```text
optimized train iterations: 24
dev validation iterations: 11
latest validation: iteration 22, val/decisions=190525.22, no new best
best checkpoint: runs/GNN_March_3SAT_ResidualProgressDiverse/best.pt
best checkpoint sha256: f9ac184722fe5785c3b084c2e173e8d799ae13a7d2b1a151887e66d4d662997a
best score: 4.315622056940805
best score iteration: 12
last checkpoint sha256: 826c2d87be226aeb238eb3deca61f12876858db012e597704354fb86ec5dd7b5
status: training complete
```

Official all-49 oracle gate result:

```text
gate: residual_progress_diverse_all49
decision: fail
total: 49
oracle_solved: 1
positive:
  - 410/3sat_12.cnf, solved_samples=8/16, best_time=6.5103, best_sample_id=2
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse/instance_oracle_summary.csv`
- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse/raw_samples_all.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_progress_diverse.md`
- `docs/residual_portfolio_gate_decision_residual_progress_diverse.md`
- `runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_progress_diverse.json`

Consequence:

```text
Stop selector work for runs/GNN_March_3SAT_ResidualProgressDiverse/best.pt.
Do not enter dev-only selector freeze or held-out same-budget control.
Do not rerun solved-first/progress-diverse GRPO as-is.
```

The failure mode is still checkpoint oracle scarcity. The latest branch fell
back to the single recurring `410/3sat_12.cnf` all-49 positive and did not
recover `425/3sat_28.cnf` or any `size=440` all-49 positives.

## Current Next Model-Side Branch: Coverage-First Residual Supervision

The next step should explicitly optimize residual instance coverage, not a
generic solved-first composite/progress surrogate.

The strongest available training signal is the existing residual train/dev
mining from `ResidualCoverageDiverseBestIter2`:

```text
train manifest: 109 elite rows over 30 positive residual_train instances
dev manifest: 17 elite rows over 7 positive residual_dev instances
train positives by size: 410=12, 425=11, 440=7
dev positives by size: 410=3, 440=4
```

Recommended protocol:

```text
1. Optionally expand residual_train/dev mining with more sample seeds if GPU/CPU
   budget allows, using the same split CSVs and a fresh namespace.
2. Build a coverage-balanced manifest: cap per-instance rows, keep fastest
   solved elites, and retain same-CNF failed samples as contrastive negatives.
3. Train a supervised residual policy objective:
   increase log-prob of solved elite samples,
   decrease or margin-rank failed samples from the same CNF,
   balance instances rather than rows,
   keep KL to the source checkpoint.
4. Select checkpoint on residual_dev coverage-balanced objective only.
5. Return to the unchanged all-49 oracle gate; selector and held-out work resume
   only if oracle_solved >= 5/49.
```

The existing elite replay command remains useful as a baseline/debug path, but
do not gate another checkpoint trained by the same lightweight positive-only
objective unless the manifest or loss has materially changed.

Implemented first-pass utilities:

```text
build_residual_contrastive_replay_manifest.py
train_residual_contrastive_replay.py
tests/test_residual_contrastive_replay.py
```

Build coverage-balanced contrastive train/dev manifests from the existing
formal residual mining artifacts:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  build_residual_contrastive_replay_manifest.py \
  --raw-samples runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_contrastive_replay_manifest_coverage_diverse_best_iter2.csv \
  --doc docs/residual_train_contrastive_replay_manifest_coverage_diverse_best_iter2.md \
  --max-positives-per-instance 2 \
  --max-negatives-per-instance 4 \
  --negative-selection low_progress \
  --min-positive-instances 8 \
  --require-raw-complete \
  --expected-sample-seeds 1729 \
  --expected-num-samples 16

env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  build_residual_contrastive_replay_manifest.py \
  --raw-samples runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_contrastive_replay_manifest_coverage_diverse_best_iter2.csv \
  --doc docs/residual_dev_contrastive_replay_manifest_coverage_diverse_best_iter2.md \
  --max-positives-per-instance 2 \
  --max-negatives-per-instance 4 \
  --negative-selection low_progress \
  --min-positive-instances 4 \
  --require-raw-complete \
  --expected-sample-seeds 1729 \
  --expected-num-samples 16
```

Actual built manifests:

```text
train contrastive manifest:
  rows: 156
  positive contrastive instances: 27
  by size: 410=12, 425=9, 440=6

dev contrastive manifest:
  rows: 30
  positive contrastive instances: 6
  by size: 410=2, 440=4
```

Train the first contrastive residual checkpoint:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  train_residual_contrastive_replay.py \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --train-manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_contrastive_replay_manifest_coverage_diverse_best_iter2.csv \
  --dev-manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_contrastive_replay_manifest_coverage_diverse_best_iter2.csv \
  --model-dir runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2 \
  --epochs 8 \
  --batch-size 8 \
  --lr 5e-6 \
  --kl-penalty 0.05 \
  --bce-weight 0.5 \
  --pairwise-weight 1.0 \
  --margin 0.02 \
  --min-train-positive-instances 8 \
  --min-dev-positive-instances 4 \
  --expected-train-split residual_train \
  --expected-dev-split residual_dev \
  --expected-train-sample-seeds 1729 \
  --expected-dev-sample-seeds 1729 \
  --expected-train-num-samples 16 \
  --expected-dev-num-samples 16
```

Smoke status:

```text
env PYTHONPATH=. python -m unittest \
  tests.test_residual_contrastive_replay \
  tests.test_residual_elite_replay \
  tests.test_residual_training_objective

28 tests OK
```

A row-limited CPU smoke of `train_residual_contrastive_replay.py` also
completed and wrote `runs/analysis/tmp_residual_contrastive_replay_smoke/`.
That smoke checkpoint is not formal and must not be gated.

Full first-pass contrastive replay training is complete:

```text
model_dir: runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2
epochs: 8
best epoch: 7
best score: -0.727973997592926
best checkpoint sha256: 56dba0670da653bea7a8106c5db2ca34463928bd8f13c5bb302dd47da313562c
last checkpoint sha256: c56fd8f865c65aca9d3a1f7d7e4837e4425eec526b3d0c57a68186623ce17cd9
config sha256: 53fede17e28f0f40a3e3fd871ef05b1d14a780038cd640e2adfa4c84266e1d53
metrics sha256: c8967d8a1ee64b08edf605c2069365ec10639710e2595c4f166806b324734c24
```

Metric caveat: dev loss decreased from `0.7349` to `0.7280`, but dev pairwise
loss stayed around `0.69`, and both positive and negative log-probs declined.
Treat this as an oracle diagnostic candidate, not as evidence that the loss is
fixed.

The all-49 gate below has now been run:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --checkpoint runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2 \
  --doc docs/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu

env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  decide_residual_portfolio_gate.py \
  --instance-oracle runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv \
  --output docs/residual_portfolio_gate_decision_residual_contrastive_replay_coverage_diverse_best_iter2.md \
  --gate-name residual_contrastive_replay_coverage_diverse_best_iter2_all49 \
  --checkpoint runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2/best.pt \
  --record-json runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_contrastive_replay_coverage_diverse_best_iter2.json \
  --expected-total 49 \
  --fail-max 2 \
  --pass-min 5
```

If this gate is still `<=2/49`, do not tune selector. Inspect and fix the
contrastive loss sign/normalization or expand residual train/dev mining seeds.

Official gate result:

```text
gate: residual_contrastive_replay_coverage_diverse_best_iter2_all49
decision: fail
total: 49
oracle_solved: 2
positives:
  - 410/3sat_12.cnf, solved_samples=7/16, best_time=10.5340, best_sample_id=11
  - 425/3sat_28.cnf, solved_samples=1/16, best_time=50.6457, best_sample_id=10
size-440 positives: 0/30
```

Artifacts:

- `runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv`
- `docs/benchmark_march_expanded_sample_portfolio_oracle_residual_contrastive_replay_coverage_diverse_best_iter2.md`
- `docs/residual_portfolio_gate_decision_residual_contrastive_replay_coverage_diverse_best_iter2.md`
- `runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_contrastive_replay_coverage_diverse_best_iter2.json`

Consequence:

```text
Stop selector work for runs/GNN_March_3SAT_ResidualContrastiveReplayCoverageDiverseBestIter2/best.pt.
Do not enter dev-only selector freeze or held-out same-budget control.
Do not rerun this contrastive objective as-is.
```

The contrastive objective has since been fixed to use same-CNF group-aware
pairwise comparisons and `delta_log_prob_per_var` relative to the source
checkpoint. That fixed variant trained successfully but is not worth an
all-49 solver gate under the current evidence:

```text
model_dir: runs/GNN_March_3SAT_ResidualContrastiveGroupAwareCoverageDiverseBestIter2
best.pt sha256: c3fec51c29de5097a6d157dfe6d4385ecae349d07bccfedf341e85d144c44a04
last.pt sha256: 2d6ba175929369fa3582cd47042bfd38f04442368817f0014150ef38884aceb3
best epoch: 7
best dev score: -0.701538602511088
```

Reason: train separation improves, but dev separation does not. Dev pairwise
loss worsens from about `0.70318` to `0.70420`, and the final dev positive
delta score remains lower than the negative delta score. Do not gate this
checkpoint unless explicitly running a diagnostic.

The current all-checkpoint oracle union confirms that this is a coverage
problem, not a selector problem:

```text
doc: docs/residual_all49_oracle_union_current_checkpoints.md
union oracle solved: 2/49
union positives:
  - 410/3sat_12.cnf
  - 425/3sat_28.cnf
size-440 positives: 0/30
```

Next model-side work item: expand residual train/dev mining seeds in fresh
namespaces, rebuild training manifests from the union of old and new raw
mining artifacts, and train only if the expanded positive floor improves
meaningfully. Do not tune selectors, touch held-out, or run same-budget
non-neural control until a new checkpoint passes the unchanged all-49 oracle
gate.

Recommended train mining expansion. This intentionally mines only new sample
seeds; the existing `1729` raw snapshot remains the first raw source for later
manifest construction:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  run_march_sample_portfolio_multiseed.py \
  --scope expanded \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --out-dir runs/analysis/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2 \
  --subset-root data/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2 \
  --doc docs/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2.md \
  --sample-seeds 1730,1731,1732 \
  --num-samples 16 \
  --artifact-mode instance \
  --full-cpu-lim 60 \
  --workers 8 \
  --device cpu
```

Current run status:

```text
pid: 3140840
log:
  runs/analysis/benchmark_transition_band_residual_large/logs/residual_train_multiseed_mining_coverage_diverse_best_iter2.log
progress doc:
  docs/residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.md
progress csv:
  runs/analysis/benchmark_transition_band_residual_large/residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.csv
```

Monitor the run with the multi-seed progress summarizer. The completion unit is
`instance x sample_seed`, not just instance. For residual_train, the expected
grid is `168 instances x 3 new seeds = 504 seed pairs`.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  summarize_residual_multiseed_mining.py \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --instances-dir runs/analysis/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2/instances \
  --expected-sample-seeds 1730,1731,1732 \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.csv \
  --remaining-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_multiseed_mining_remaining_coverage_diverse_best_iter2.csv \
  --positives-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_multiseed_mining_positives_coverage_diverse_best_iter2.csv \
  --doc docs/residual_train_multiseed_mining_progress_coverage_diverse_best_iter2.md \
  --min-positive-instances 16
```

Only treat train mining as complete when the progress row reports:

```text
completed_seed_pairs=504
complete_mining=true
raw_artifacts_complete=true
decision=ready_for_formal_multiseed_manifest or complete_but_sparse
```

If the runner exits before that, resume the same command in the same namespace;
existing per-instance artifacts are reused by default. Do not start dev mining
while the train mining runner or March workers are still visible.

Recommended dev mining expansion, after train mining is not running:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  launch_residual_dev_multiseed_mining.py \
  --detached
```

The launcher refuses to run unless the train multi-seed progress row reports
the exact expected seed set, `completed_seed_pairs=504`,
`raw_artifacts_complete=true`, `decision=ready_for_formal_multiseed_manifest`,
and `positive_instances >= 16`. It also refuses while March/replay/residual
training processes are active. To inspect the command without launching:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  launch_residual_dev_multiseed_mining.py \
  --dry-run
```

With the current partial train progress this dry-run must fail closed; that is
the expected state until train mining completes.

Use the same progress summarizer for dev after it starts, with expected grid
`93 instances x 3 new seeds = 279 seed pairs` and `--min-positive-instances 8`.
Use the dev namespace paths:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  summarize_residual_multiseed_mining.py \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --instances-dir runs/analysis/benchmark_march_residual_dev_multiseed_mining_coverage_diverse_best_iter2/instances \
  --expected-sample-seeds 1730,1731,1732 \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_multiseed_mining_progress_coverage_diverse_best_iter2.csv \
  --remaining-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_multiseed_mining_remaining_coverage_diverse_best_iter2.csv \
  --positives-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_multiseed_mining_positives_coverage_diverse_best_iter2.csv \
  --doc docs/residual_dev_multiseed_mining_progress_coverage_diverse_best_iter2.md \
  --min-positive-instances 8
```

After a new mining run completes, first write its strict aggregate. This must
run without `--allow-partial-summary`; a missing seed-pair artifact should fail
and trigger a resume.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  finalize_residual_multiseed_mining.py
```

The finalizer refreshes multi-seed progress, refuses partial grids, checks the
runner's work-dir lock, and only then runs strict `--summarize-only`. It does
not use `--allow-partial-summary`. Use `--require-positive-floor` when the next
action is dev-launch readiness; omit it when writing a complete-but-sparse
diagnostic summary before switching objectives.

Run the analogous strict summarize-only finalization for dev after the dev
runner finishes, using the dev split/out-dir/subset/doc paths. Then build
expanded contrastive manifests from the old `1729` raw source plus the new raw
source:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  build_residual_contrastive_replay_manifest.py \
  --raw-samples \
    runs/analysis/benchmark_march_residual_train_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
    runs/analysis/benchmark_march_residual_train_multiseed_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_train_contrastive_replay_manifest_coverage_diverse_best_iter2_seeds1729_1732.csv \
  --doc docs/residual_train_contrastive_replay_manifest_coverage_diverse_best_iter2_seeds1729_1732.md \
  --max-positives-per-instance 2 \
  --max-negatives-per-instance 4 \
  --negative-selection low_progress \
  --min-positive-instances 16 \
  --require-raw-complete \
  --expected-sample-seeds 1729,1730,1731,1732 \
  --expected-num-samples 16

env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  build_residual_contrastive_replay_manifest.py \
  --raw-samples \
    runs/analysis/benchmark_march_residual_dev_elite_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
    runs/analysis/benchmark_march_residual_dev_multiseed_mining_coverage_diverse_best_iter2/raw_samples_all.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_dev_contrastive_replay_manifest_coverage_diverse_best_iter2_seeds1729_1732.csv \
  --doc docs/residual_dev_contrastive_replay_manifest_coverage_diverse_best_iter2_seeds1729_1732.md \
  --max-positives-per-instance 2 \
  --max-negatives-per-instance 4 \
  --negative-selection low_progress \
  --min-positive-instances 8 \
  --require-raw-complete \
  --expected-sample-seeds 1729,1730,1731,1732 \
  --expected-num-samples 16
```

Those positive floors are sanity guards, not final claims. If the expanded
manifests cannot meet them, do not lower the bar just to train another
checkpoint; switch to a stronger residual-distribution training objective.

Existing positive-only replay baseline command:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  train_residual_elite_replay.py \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --train-manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --dev-manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --model-dir runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2 \
  --epochs 8 \
  --batch-size 8 \
  --lr 5e-6 \
  --kl-penalty 0.05 \
  --min-train-positive-instances 8 \
  --min-dev-positive-instances 4 \
  --expected-train-split residual_train \
  --expected-dev-split residual_dev \
  --expected-train-sample-seeds 1729 \
  --expected-dev-sample-seeds 1729 \
  --expected-train-num-samples 16 \
  --expected-dev-num-samples 16
```

Only run this after both guarded manifests exist. The dev manifest is for
checkpoint selection only; it is not a held-out evaluation set. The replay
training entry point records and enforces the expected train/dev sampling
budget, so a checkpoint trained from the wrong mining seed set or sample count
will be rejected before training or by the config audit below.

Before running the all-49 oracle gate on the replay checkpoint, audit that the
saved replay training config still matches the formal train/dev manifests and
source checkpoint. This audit also rejects row-limited or partial-manifest
training configs:

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  audit_residual_elite_replay_manifest.py \
  --manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --split-csv runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv \
  --checkpoint runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt \
  --expected-split residual_train \
  --min-positive-instances 8 \
  --max-per-instance 4 \
  --training-config runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/config.yaml \
  --train-manifest runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --dev-manifest runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv \
  --min-train-positive-instances 8 \
  --min-dev-positive-instances 4 \
  --expected-train-split residual_train \
  --expected-dev-split residual_dev \
  --expected-train-sample-seeds 1729 \
  --expected-dev-sample-seeds 1729 \
  --expected-train-num-samples 16 \
  --expected-dev-num-samples 16 \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.csv \
  --doc docs/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.md
```

When gating the replay checkpoint, pass that audit artifact into
`decide_residual_portfolio_gate.py`. The gate decision will fail before writing
if the training-config audit is missing required formal replay-provenance
checks or has any failed check, and the decision document will record the
audit path and SHA256. New oracle summaries produced by
`run_march_sample_portfolio_multiseed.py` also carry the evaluated checkpoint
hash; when present, the gate decision verifies that hash against `--checkpoint`.
Always write `--record-json` for any checkpoint that may proceed to held-out:
the final protocol audit now reopens the recorded oracle, checkpoint, and
training-config audit artifacts and checks their SHA256/provenance instead of
trusting the JSON fields alone.

```bash
env PYTHONPATH=. /home/sunshixin/anaconda3/envs/rlaf/bin/python \
  decide_residual_portfolio_gate.py \
  --instance-oracle runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv \
  --output docs/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.md \
  --gate-name residual_elite_replay_coverage_diverse_best_iter2_all49 \
  --checkpoint runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt \
  --training-config-audit runs/analysis/benchmark_transition_band_residual_large/residual_elite_replay_training_config_audit_coverage_diverse_best_iter2.csv \
  --record-json runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.json \
  --expected-total 49 \
  --fail-max 2 \
  --pass-min 5
```

If this diversity variant cannot complete optimizer steps, use the staged
residual-targeted curriculum only as a cheaper fallback:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python train_rlaf.py \
  --config-name config_train_rlaf_march_residual_targeted_stage1
```

This writes to `runs/GNN_March_3SAT_ResidualTargetedStage1`, keeps the same
residual train/dev split and composite objective, but uses 8 CNFs, 8 samples,
and a 20s March cap per rollout. It is a checkpoint-generation step, not a
paper result. Gate it only after the log shows `Optimized model for ...` and
`last.pt` has a new mtime.

## If Gate Passes

The pass condition is:

```text
oracle solved >= 5/49
```

Still do not claim a paper result from all-49. Generate a larger residual pool,
lock dev/held-out splits, tune selector thresholds only on dev, and run the
fixed selected neural portfolio against the same-budget non-neural rerun
portfolio on held-out residual instances.

Dev-only selector/schedule selection uses the residual dev split, and only
starts after the replay checkpoint passes the all-49 gate above. Example:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_march_expanded_early_trace_gate.py \
  --checkpoint runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/best.pt \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_dev.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --subset-root data/benchmark_transition_band_residual_large/dev_neural_selector_seed1729 \
  --out-dir runs/analysis/benchmark_transition_band_residual_large/neural_selector_dev_seed1729 \
  --doc docs/benchmark_transition_band_residual_large_neural_selector_dev_seed1729.md \
  --sample-seeds 1729 \
  --num-samples 16 \
  --top-k 2 \
  --policy probe_solved_then_high_deadends \
  --probe-cpu-lim 1 \
  --full-cpu-lim 60 \
  --resume
```

After dev freezes `top-k`, policy, probe budget, full-run budget, sample seed
schedule, and any adaptive thresholds, run the selected neural portfolio once
on held-out. This writes `selector_spec.json`; the final audit checks the
held-out summary against that frozen spec.

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_march_expanded_early_trace_gate.py \
  --selector-spec-in runs/analysis/benchmark_transition_band_residual_large/neural_selector_dev_seed1729/selector_spec.json \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_heldout.csv \
  --source-root data/benchmark_transition_band_residual_large \
  --subset-root data/benchmark_transition_band_residual_large/heldout_neural_selector_seed1729 \
  --out-dir runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729 \
  --doc docs/benchmark_transition_band_residual_large_neural_selector_heldout_seed1729.md \
  --resume
```

After dev selects the fixed selector and budget rule, pre-register the
non-neural solver/config cycle from the dev neural summary. Match the neural
allocated residual budget (`probe_cpu_total + full_cpu_allocated`), not the
lower actual capped time from instances that solve early. The dev artifact
freezes the solver cycle and attempt limit; held-out may expand that frozen
cycle per instance to match each held-out neural allocated budget. This uses
the frozen selector's allocated budget only, not held-out solve outcomes.

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python build_non_neural_schedule_from_neural_budget.py \
  --neural-summary runs/analysis/benchmark_transition_band_residual_large/neural_selector_dev_seed1729/expanded_early_trace_summary.csv \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_schedule_seed1729.csv \
  --doc docs/benchmark_transition_band_residual_large_non_neural_control_heldout_schedule_seed1729.md \
  --source-split dev \
  --selector-spec runs/analysis/benchmark_transition_band_residual_large/neural_selector_dev_seed1729/selector_spec.json \
  --aggregation mean \
  --attempt-limit 60 \
  --solver-cycle march cadical_seed1 cadical_plain_seed1 cadical_shuffle_seed1
```

Then run the control from the frozen schedule artifact and the held-out neural
budget summary. This produces per-instance same-budget non-neural schedules
from the frozen dev cycle:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python run_residual_non_neural_budget_control.py \
  --input runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_heldout.csv \
  --cnf-root data/benchmark_transition_band_residual_large \
  --out-dir runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_seed1729 \
  --doc docs/benchmark_transition_band_residual_large_non_neural_control_heldout_seed1729.md \
  --schedule-csv runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_schedule_seed1729.csv \
  --neural-budget-summary runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729/expanded_early_trace_summary.csv \
  --workers 8
```

The control script records the input CSV, CNF root, frozen schedule source,
held-out budget source, per-instance expanded schedules, per-attempt artifacts,
and whether each solver budget is internally or externally enforced. The final
audit recomputes per-instance schedules from the frozen solver cycle and checks
per-instance residual CPU budget equality.

Finally, build the denominator-preserving paper table from artifacts:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python summarize_residual_portfolio_paper_table.py \
  --strong-combined runs/analysis/benchmark_transition_band_residual_large/combined.csv \
  --candidate-manifest runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv \
  --candidate-metadata runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json \
  --split-manifest runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv \
  --split-metadata runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/split_metadata.json \
  --oracle-summary runs/analysis/benchmark_march_expanded_sample_portfolio_oracle_residual_elite_replay_coverage_diverse_best_iter2/instance_oracle_summary.csv \
  --neural-summary runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729/expanded_early_trace_summary.csv \
  --non-neural-summary runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_seed1729/instance_summary.csv \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_paper_table_seed1729.csv \
  --doc docs/benchmark_transition_band_residual_large_residual_portfolio_paper_table_seed1729.md
```

This summary must not be used to tune held-out settings. It is only a final
artifact join over the already fixed strong-solver gate, oracle diagnostic,
selected neural held-out run, and same-budget non-neural held-out control.
It parses solve booleans strictly and rejects duplicate oracle/non-neural
instance keys, so string `False` and duplicated rows cannot inflate the final
solve counts.

Run the protocol audit before using the table in a paper draft:

```bash
/home/sunshixin/anaconda3/envs/rlaf/bin/python audit_residual_portfolio_protocol.py \
  --strong-combined runs/analysis/benchmark_transition_band_residual_large/combined.csv \
  --candidate-manifest runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv \
  --candidate-metadata runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json \
  --expected-candidate-total 900 \
  --expected-generation-seed 2041 \
  --expected-split-seed 1729 \
  --require-candidate-files \
  --split-manifest runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv \
  --split-metadata runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/split_metadata.json \
  --split-input runs/analysis/benchmark_transition_band_residual_large/both_unknown_subset.csv \
  --exclude-csv runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/both_unknown_subset.csv \
  --exclude-cnf-root data/benchmark_transition_band_expanded \
  --neural-summary runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729/expanded_early_trace_summary.csv \
  --non-neural-summary runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_seed1729/instance_summary.csv \
  --selector-spec runs/analysis/benchmark_transition_band_residual_large/neural_selector_heldout_seed1729/selector_spec.json \
  --gate-record runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_gate_decision_residual_elite_replay_coverage_diverse_best_iter2.json \
  --require-gate-pass \
  --non-neural-schedule runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_schedule_seed1729.csv \
  --non-neural-run-schedule runs/analysis/benchmark_transition_band_residual_large/non_neural_control_heldout_seed1729/schedule.csv \
  --output-csv runs/analysis/benchmark_transition_band_residual_large/residual_portfolio_protocol_audit_seed1729.csv \
  --doc docs/benchmark_transition_band_residual_large_protocol_audit_seed1729.md
```

The audit must pass without `--allow-incomplete` for any top-conference claim.
It checks held-out neural group-key uniqueness, non-neural instance-key
uniqueness, fixed selector provenance, the all-49 gate-pass record for the same
checkpoint, the gate record's oracle/checkpoint/training-audit artifact hashes,
and per-instance same-budget equality.
