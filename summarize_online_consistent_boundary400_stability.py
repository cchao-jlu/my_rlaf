from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path("runs/analysis")
INPUT_CSV = OUT_DIR / "local_reopen_guarded_full400_per_instance.csv"
OUT_CSV = OUT_DIR / "online_consistent_boundary400_stability.csv"

METHODS = [
    ("one_shot", "one_shot"),
    ("old_compact", "old"),
    ("online_consistent_boundary400", "online"),
    ("local_reopen_guarded", "local"),
]

BASELINE_KEY = "one_shot"
BOOTSTRAP_ITERS = 2000
SPLIT_ITERS = 2000
SPLIT_SIZE = 100


def load_frame() -> pd.DataFrame:
    frame = pd.read_csv(INPUT_CSV).copy()
    frame["file_key"] = frame["file_key"].astype(str)
    return frame


def select_columns(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    columns = [
        "file_key",
        f"{prefix}_result",
        f"{prefix}_solved",
        f"{prefix}_time",
        f"{prefix}_cpu_time",
        f"{prefix}_gpu_time",
    ]
    return frame[columns].copy()


def paired_frame(frame: pd.DataFrame, base_prefix: str, method_prefix: str) -> pd.DataFrame:
    base = select_columns(frame, base_prefix).rename(
        columns={
            f"{base_prefix}_result": "base_result",
            f"{base_prefix}_solved": "base_solved",
            f"{base_prefix}_time": "base_time",
            f"{base_prefix}_cpu_time": "base_cpu_time",
            f"{base_prefix}_gpu_time": "base_gpu_time",
        }
    )
    method = select_columns(frame, method_prefix).rename(
        columns={
            f"{method_prefix}_result": "method_result",
            f"{method_prefix}_solved": "method_solved",
            f"{method_prefix}_time": "method_time",
            f"{method_prefix}_cpu_time": "method_cpu_time",
            f"{method_prefix}_gpu_time": "method_gpu_time",
        }
    )
    return base.merge(method, on="file_key", how="inner")


def bootstrap_summary(paired: pd.DataFrame, rng: np.random.Generator) -> dict[str, float]:
    n = len(paired)
    base_time = paired["base_time"].to_numpy(dtype=np.float64)
    method_time = paired["method_time"].to_numpy(dtype=np.float64)
    base_solved = paired["base_solved"].to_numpy(dtype=np.float64)
    method_solved = paired["method_solved"].to_numpy(dtype=np.float64)
    indices = rng.integers(0, n, size=(BOOTSTRAP_ITERS, n))
    delta_time = method_time[indices].mean(axis=1) - base_time[indices].mean(axis=1)
    delta_solved = method_solved[indices].sum(axis=1) - base_solved[indices].sum(axis=1)
    return {
        "bootstrap_delta_time_mean": float(delta_time.mean()),
        "bootstrap_delta_time_ci_low": float(np.quantile(delta_time, 0.025)),
        "bootstrap_delta_time_ci_high": float(np.quantile(delta_time, 0.975)),
        "bootstrap_time_improve_prob": float((delta_time < 0.0).mean()),
        "bootstrap_delta_solved_mean": float(delta_solved.mean()),
        "bootstrap_delta_solved_ci_low": float(np.quantile(delta_solved, 0.025)),
        "bootstrap_delta_solved_ci_high": float(np.quantile(delta_solved, 0.975)),
        "bootstrap_solved_improve_prob": float((delta_solved > 0.0).mean()),
    }


def split_summary(paired: pd.DataFrame, rng: np.random.Generator) -> dict[str, float]:
    n = len(paired)
    size = min(SPLIT_SIZE, n)
    base_time = paired["base_time"].to_numpy(dtype=np.float64)
    method_time = paired["method_time"].to_numpy(dtype=np.float64)
    base_solved = paired["base_solved"].to_numpy(dtype=np.float64)
    method_solved = paired["method_solved"].to_numpy(dtype=np.float64)

    delta_times = []
    delta_solved = []
    for _ in range(SPLIT_ITERS):
        indices = rng.choice(n, size=size, replace=False)
        delta_times.append(float(method_time[indices].mean() - base_time[indices].mean()))
        delta_solved.append(float(method_solved[indices].sum() - base_solved[indices].sum()))

    delta_times = np.asarray(delta_times, dtype=np.float64)
    delta_solved = np.asarray(delta_solved, dtype=np.float64)
    return {
        "split_size": int(size),
        "split_delta_time_mean": float(delta_times.mean()),
        "split_delta_time_ci_low": float(np.quantile(delta_times, 0.025)),
        "split_delta_time_ci_high": float(np.quantile(delta_times, 0.975)),
        "split_time_improve_rate": float((delta_times < 0.0).mean()),
        "split_delta_solved_mean": float(delta_solved.mean()),
        "split_delta_solved_ci_low": float(np.quantile(delta_solved, 0.025)),
        "split_delta_solved_ci_high": float(np.quantile(delta_solved, 0.975)),
        "split_solved_improve_rate": float((delta_solved > 0.0).mean()),
    }


def method_row(frame: pd.DataFrame, key: str, prefix: str, rng: np.random.Generator) -> dict[str, object]:
    method = select_columns(frame, prefix).rename(
        columns={
            f"{prefix}_result": "result",
            f"{prefix}_solved": "solved",
            f"{prefix}_time": "time",
            f"{prefix}_cpu_time": "cpu_time",
            f"{prefix}_gpu_time": "gpu_time",
        }
    )
    row = {
        "method_key": key,
        "method": key,
        "n": int(len(method)),
        "solved": int(method["solved"].sum()),
        "mean_time": float(method["time"].mean()),
        "median_time": float(method["time"].median()),
        "mean_cpu_time": float(method["cpu_time"].mean()),
        "mean_gpu_time": float(method["gpu_time"].mean()),
    }
    if key == BASELINE_KEY:
        row.update(
            {
                "delta_mean_time_vs_one_shot": 0.0,
                "delta_solved_vs_one_shot": 0,
                "bootstrap_delta_time_mean": 0.0,
                "bootstrap_delta_time_ci_low": 0.0,
                "bootstrap_delta_time_ci_high": 0.0,
                "bootstrap_time_improve_prob": 0.0,
                "bootstrap_delta_solved_mean": 0.0,
                "bootstrap_delta_solved_ci_low": 0.0,
                "bootstrap_delta_solved_ci_high": 0.0,
                "bootstrap_solved_improve_prob": 0.0,
                "split_size": SPLIT_SIZE,
                "split_delta_time_mean": 0.0,
                "split_delta_time_ci_low": 0.0,
                "split_delta_time_ci_high": 0.0,
                "split_time_improve_rate": 0.0,
                "split_delta_solved_mean": 0.0,
                "split_delta_solved_ci_low": 0.0,
                "split_delta_solved_ci_high": 0.0,
                "split_solved_improve_rate": 0.0,
            }
        )
        return row

    paired = paired_frame(frame, BASELINE_KEY, prefix)
    row["delta_mean_time_vs_one_shot"] = float(paired["method_time"].mean() - paired["base_time"].mean())
    row["delta_solved_vs_one_shot"] = int(paired["method_solved"].sum() - paired["base_solved"].sum())
    row.update(bootstrap_summary(paired, rng=rng))
    row.update(split_summary(paired, rng=rng))
    return row


def main() -> None:
    frame = load_frame()
    rng = np.random.default_rng(1729)
    rows = [method_row(frame, key, prefix, rng) for key, prefix in METHODS]
    result = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
