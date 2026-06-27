from __future__ import annotations

import argparse
import csv
import os
import random
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a hard-recovery split without touching 300/350 heldout.")
    parser.add_argument("--source-root", default="data/test/3sat")
    parser.add_argument("--output-root", default="data/selector_splits/3sat")
    parser.add_argument("--size", type=int, default=400)
    parser.add_argument("--train-count", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260523)
    parser.add_argument(
        "--base-eval",
        default="runs/GNN_Glucose_3SAT_V1/eval_oneshot_400_optimized_events_gated.csv",
    )
    parser.add_argument(
        "--adapter-eval",
        default="runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/eval_trace_adapter_rho_gate_400_optimized_events_gated.csv",
    )
    parser.add_argument("--link-mode", choices=["symlink", "copy"], default="symlink")
    return parser.parse_args()


def result_is_solved(value) -> bool:
    return str(value) not in {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}


def place_file(source: Path, target: Path, link_mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    if link_mode == "copy":
        target.write_bytes(source.read_bytes())
    else:
        rel_source = os.path.relpath(source.resolve(), start=target.parent.resolve())
        target.symlink_to(rel_source)


def load_eval_frame(base_eval: str, adapter_eval: str) -> pd.DataFrame:
    base = pd.read_csv(base_eval)[["cnf_id", "Result", "time"]].rename(
        columns={"Result": "base_result", "time": "base_time"}
    )
    adapter = pd.read_csv(adapter_eval)[["cnf_id", "Result", "time"]].rename(
        columns={"Result": "adapter_result", "time": "adapter_time"}
    )
    frame = base.merge(adapter, on="cnf_id", how="inner")
    frame["base_solved"] = frame["base_result"].map(result_is_solved)
    frame["adapter_solved"] = frame["adapter_result"].map(result_is_solved)
    frame["bucket"] = "other"
    frame.loc[~frame["base_solved"] & frame["adapter_solved"], "bucket"] = "known_recovered"
    frame.loc[frame["base_solved"] & ~frame["adapter_solved"], "bucket"] = "known_lost"
    frame.loc[~frame["base_solved"] & ~frame["adapter_solved"], "bucket"] = "both_timeout"
    near_timeout = frame["base_solved"] & frame["adapter_solved"] & (frame["base_time"] >= 45.0)
    frame.loc[near_timeout, "bucket"] = "near_timeout_solved"
    return frame


def choose_train_ids(frame: pd.DataFrame, train_count: int, seed: int) -> set[int]:
    rng = random.Random(seed)
    selected: list[int] = []
    for bucket in ["known_recovered", "known_lost", "both_timeout", "near_timeout_solved"]:
        ids = frame.loc[frame["bucket"] == bucket, "cnf_id"].astype(int).tolist()
        rng.shuffle(ids)
        selected.extend(ids)
        if len(selected) >= train_count:
            return set(selected[:train_count])
    remaining = frame.loc[~frame["cnf_id"].isin(selected), "cnf_id"].astype(int).tolist()
    rng.shuffle(remaining)
    selected.extend(remaining)
    return set(selected[:train_count])


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_root) / str(args.size)
    output_root = Path(args.output_root)
    train_root = output_root / "hard_recovery_train" / str(args.size)
    heldout_root = output_root / "hard_recovery_heldout" / str(args.size)
    for root in [train_root, heldout_root]:
        root.mkdir(parents=True, exist_ok=True)
        for child in root.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()

    frame = load_eval_frame(args.base_eval, args.adapter_eval)
    train_ids = choose_train_ids(frame, train_count=args.train_count, seed=args.seed)
    rows = []
    for _, row in frame.sort_values("cnf_id").iterrows():
        cnf_id = int(row["cnf_id"])
        source = source_dir / f"3sat_{cnf_id}.cnf"
        if not source.exists():
            raise FileNotFoundError(source)
        split = "hard_recovery_train" if cnf_id in train_ids else "hard_recovery_heldout"
        target_root = train_root if cnf_id in train_ids else heldout_root
        target = target_root / source.name
        place_file(source, target, args.link_mode)
        rows.append(
            {
                "size": int(args.size),
                "cnf_id": cnf_id,
                "split": split,
                "bucket": row["bucket"],
                "source_file": str(source),
                "split_file": str(target),
                "base_result": row["base_result"],
                "base_time": float(row["base_time"]),
                "adapter_result": row["adapter_result"],
                "adapter_time": float(row["adapter_time"]),
            }
        )

    manifest = output_root / "hard_recovery_manifest.csv"
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = pd.DataFrame(rows).groupby(["split", "bucket"]).size().reset_index(name="count")
    print(summary.to_string(index=False))
    print(f"wrote manifest: {manifest}")


if __name__ == "__main__":
    main()
