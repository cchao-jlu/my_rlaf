# EchoSAT

EchoSAT is a SAT neural-guided solving research codebase built from RLAF. The
current public snapshot keeps source code, solver integrations, configs, tests,
and the core SAT symmetry documentation. Local datasets, model checkpoints,
run outputs, W&B logs, temporary files, and one-off experiment reports are not
included in this repository snapshot.

## Contents

- `src/`: Python package for CNF data loading, GNN models, policy evaluation,
  solver wrappers, and trace-distillation utilities.
- `configs/`: Hydra configs for baseline training/evaluation and trace
  distillation.
- `solvers/`: Glucose, weighted Glucose, March, and weighted March source used
  by the project. Built binaries are intentionally excluded.
- `tests/`: unit and regression tests for core project behavior.
- `docs/`: selected mainline SAT symmetry protocol and audit reports.

## Setup

```bash
conda create -n rlaf python=3.12
conda activate rlaf
pip install -e .
pip install torch-scatter torch-sparse -f https://data.pyg.org/whl/torch-2.5.0+cu124.html
```

Use the PyG wheel URL matching your CUDA or CPU environment.

Build local SAT solvers:

```bash
bash build_solvers.sh
```

## Basic Commands

Train a baseline guided model:

```bash
python train_rlaf.py model_name=GNN_Glucose_3SAT \
  solver.solver=glucose \
  dataset.train_path='data/training/3sat/*/*.cnf' \
  dataset.val_path='data/validation/3sat/*/*.cnf'
```

Evaluate a guided solver:

```bash
python evaluate_guided_solver.py \
  model_name=GNN_Glucose_3SAT \
  dataset.eval_path='data/test/3sat/450/*.cnf'
```

Evaluate an unguided solver:

```bash
python evaluate_base_solver.py \
  solver.solver=glucose \
  dataset.eval_path='data/test/3sat/450/*.cnf'
```

Generate and train trace distillation data:

```bash
python generate_trace_distillation_data.py --config-name config_generate_trace_distillation
python train_trace_distill.py --config-name config_train_trace_distill
```

## SAT Symmetry Mainline

The main documentation entry point is:

- `docs/sat_symmetry_original_method_report.md`

Related protocol and audit documents included in this snapshot:

- `docs/runtime_protocol_v1.md`
- `docs/glucose_weighted_preprocessing_code_audit.md`
- `docs/symmetry_weighted_glucose_path_audit.md`
- `docs/symmetry_solver_protocol_preflight.md`
- `docs/symmetry_runtime_protocol_v1.md`
- `docs/symmetry_runtime_protocol_v1_1.md`
- `docs/symmetry_runtime_benchmark_v2.md`
- `docs/symmetry_runtime_positive_subset_v2.md`

The runtime reports are viability and attribution evidence. They are not solver
speedup claims.

## Data And Artifacts

This repository does not include generated CNF datasets, trace tensors,
checkpoints, run CSVs, W&B logs, or local smoke-test outputs. Recreate those
artifacts locally with the scripts and configs above, or provide your own data
under `data/`.
