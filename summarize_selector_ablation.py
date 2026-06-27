import argparse
import collections
import os

import pandas as pd


DEFAULT_SELECTOR_DIR = (
    "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorRho300350"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize slow-fast selector online and offline ablations."
    )
    parser.add_argument("--selector-dir", default=DEFAULT_SELECTOR_DIR)
    parser.add_argument("--baseline-300", default="runs/GNN_Glucose_3SAT_V1/eval_oneshot_300.csv")
    parser.add_argument("--baseline-350", default="runs/GNN_Glucose_3SAT_V1/eval_oneshot_350.csv")
    parser.add_argument(
        "--adapter-300",
        default=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/"
            "eval_trace_adapter_300_round1_conf500.csv"
        ),
    )
    parser.add_argument(
        "--adapter-350",
        default=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/"
            "eval_trace_adapter_350_round1_conf500.csv"
        ),
    )
    parser.add_argument(
        "--rho-gate-300",
        default=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
            "eval_trace_adapter_300_round1_conf500.csv"
        ),
    )
    parser.add_argument(
        "--rho-gate-350",
        default=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
            "eval_trace_adapter_350_round1_conf500.csv"
        ),
    )
    return parser.parse_args()


def read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def eval_summary(path: str) -> dict[str, object]:
    frame = read_csv(path)
    result_counts = collections.Counter(frame["Result"].astype(str)) if "Result" in frame else {}
    solved = int(sum(count for result, count in result_counts.items() if result != "INDETERMINATE"))
    return {
        "n": len(frame),
        "solved": solved,
        "time_mean": frame["time"].mean(),
        "time_median": frame["time"].median(),
        "cpu_mean": frame["CPU time"].mean() if "CPU time" in frame else float("nan"),
        "gpu_mean": frame["GPU time"].mean() if "GPU time" in frame else float("nan"),
        "conflicts_mean": frame["conflicts"].mean(),
        "decisions_mean": frame["decisions"].mean(),
    }


def print_online_table(rows: list[tuple[str, str, dict[str, object]]]) -> None:
    print("## Online Solver Ablation")
    print()
    print("| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for method, size, summary in rows:
        print(
            f"| {method} | {size} | {summary['n']} | {summary['solved']} | "
            f"{summary['time_mean']:.4f} | {summary['time_median']:.4f} | "
            f"{summary['conflicts_mean']:.2f} | {summary['decisions_mean']:.2f} |"
        )


def print_offline_table(selector_training_path: str) -> None:
    if not os.path.exists(selector_training_path):
        return
    frame = pd.read_csv(selector_training_path)
    if "selector_use_adapter" not in frame:
        return
    frame["inverse_selector_time"] = frame.apply(
        lambda row: row["adapter_time"] if int(row["selector_use_adapter"]) == 0 else row["base_time"],
        axis=1,
    )
    frame["size"] = frame["selector_dataset"].str.extract(r"/(\d+)/\*\.cnf$")[0].fillna(
        frame["selector_dataset"]
    )

    print()
    print("## Offline Selector Policy Ablation")
    print()
    print("| size | selected fraction | base | always adapter | learned selector | inverse selector |")
    print("|---:|---:|---:|---:|---:|---:|")
    groups = list(frame.groupby("size", sort=True))
    groups.append(("all", frame))
    for size, group in groups:
        print(
            f"| {size} | {group['selector_use_adapter'].mean():.4f} | "
            f"{group['base_time'].mean():.4f} | {group['adapter_time'].mean():.4f} | "
            f"{group['selector_time'].mean():.4f} | {group['inverse_selector_time'].mean():.4f} |"
        )


def main() -> None:
    args = parse_args()
    selector_300 = os.path.join(args.selector_dir, "eval_trace_adapter_300_round1_conf500.csv")
    selector_350 = os.path.join(args.selector_dir, "eval_trace_adapter_350_round1_conf500.csv")
    rows = [
        ("one-shot baseline", "300", eval_summary(args.baseline_300)),
        ("always adapter", "300", eval_summary(args.adapter_300)),
        ("fixed rho gate", "300", eval_summary(args.rho_gate_300)),
        ("learned selector", "300", eval_summary(selector_300)),
        ("one-shot baseline", "350", eval_summary(args.baseline_350)),
        ("always adapter", "350", eval_summary(args.adapter_350)),
        ("fixed rho gate", "350", eval_summary(args.rho_gate_350)),
        ("learned selector", "350", eval_summary(selector_350)),
    ]
    print_online_table(rows)
    print_offline_table(os.path.join(args.selector_dir, "selector_training.csv"))


if __name__ == "__main__":
    main()
