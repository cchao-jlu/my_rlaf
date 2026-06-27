from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_LOG = ROOT / "runs/analysis/benchmark_transition_band_residual_large/logs/residual_targeted_training_resume.log"
DEFAULT_MODEL_DIR = ROOT / "runs/GNN_March_3SAT_ResidualTargeted"
DEFAULT_PROCESS_PATTERN = "train_rlaf.py --config-name config_train_rlaf_march_residual_targeted"


def display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def pgrep(pattern: str) -> list[str]:
    proc = subprocess.run(["pgrep", "-af", pattern], capture_output=True, text=True)
    if proc.returncode not in {0, 1}:
        raise RuntimeError(proc.stderr.strip() or f"pgrep failed with {proc.returncode}")
    own_pid = os.getpid()
    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        first = line.split(maxsplit=1)[0]
        if first.isdigit() and int(first) == own_pid:
            continue
        if "monitor_residual_targeted_training.py" in line:
            continue
        rows.append(line)
    return rows


def parse_log(path: Path) -> dict[str, str | int]:
    if not path.exists():
        return {"log_exists": "no"}
    text = path.read_text(errors="replace")
    iterations = re.findall(r"GRPO Iteration (\d+)", text)
    optimized = re.findall(r"Optimized model for (\d+) steps", text)
    solver_batches = re.findall(r"Solved (\d+) formulas in ([0-9.]+) seconds", text)
    best_saves = re.findall(r"Saving new best checkpoint", text)
    last_saves = re.findall(r"Saving checkpoint at iteration|last.pt", text)
    validation_scores = re.findall(r"Loaded best validation score ([0-9.eE+-]+)", text)
    signals = re.findall(r"Received signal (\d+)", text)
    return {
        "log_exists": "yes",
        "last_iteration_seen": int(iterations[-1]) if iterations else -1,
        "optimized_iterations_logged": len(optimized),
        "solver_batches_logged": len(solver_batches),
        "last_solver_batch_formulas": int(solver_batches[-1][0]) if solver_batches else 0,
        "last_solver_batch_seconds": solver_batches[-1][1] if solver_batches else "",
        "best_checkpoint_saves_logged": len(best_saves),
        "last_checkpoint_saves_logged": len(last_saves),
        "last_best_score_loaded": validation_scores[-1] if validation_scores else "",
        "signals_logged": len(signals),
    }


def file_state(path: Path) -> dict[str, str | int]:
    if not path.exists():
        return {"path": display(path), "exists": "no"}
    stat = path.stat()
    return {
        "path": display(path),
        "exists": "yes",
        "size": stat.st_size,
        "mtime": f"{stat.st_mtime:.0f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor residual-targeted RLAF training.")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--process-pattern", default=DEFAULT_PROCESS_PATTERN)
    parser.add_argument("--skip-process-check", action="store_true")
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    process_rows = [] if args.skip_process_check else pgrep(str(args.process_pattern))
    rows = {
        "process_check_note": (
            "This only reports processes visible from the current PID namespace. "
            "Detached training started outside the sandbox may require a direct host pgrep check."
        ),
        "processes_visible_here": process_rows,
        "log": parse_log(args.log.resolve()),
        "best_score": {},
        "files": [
            file_state(model_dir / "best.pt"),
            file_state(model_dir / "last.pt"),
            file_state(model_dir / "best_score.json"),
        ],
    }
    score_path = model_dir / "best_score.json"
    if score_path.exists():
        with score_path.open() as handle:
            rows["best_score"] = json.load(handle)
    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
