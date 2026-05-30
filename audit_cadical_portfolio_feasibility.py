from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
IN_PATH = ROOT / "runs/analysis/cadical_neural_overlap/combined.csv"
OUT_DIR = ROOT / "runs/analysis/cadical_portfolio_feasibility"
DOC_PATH = ROOT / "docs/cadical_portfolio_feasibility_audit.md"
TIME_CAP = 60.0

METHODS = {
    "one_shot": {
        "paper_name": "One-shot",
        "solved_col": "one_shot_solved",
        "time_col": "one_shot_time_mean",
    },
    "online": {
        "paper_name": "Online-Consistent Selector",
        "solved_col": "online_solved",
        "time_col": "online_time_mean",
    },
    "old_compact": {
        "paper_name": "Old Compact",
        "solved_col": "old_compact_solved",
        "time_col": "old_compact_time_mean",
    },
    "local": {
        "paper_name": "+ Local Boundary Correction",
        "solved_col": "local_correction_solved",
        "time_col": "local_correction_time_mean",
    },
    "cadical": {
        "paper_name": "CaDiCaL",
        "solved_col": "cadical_solved",
        "time_col": "cadical_time",
    },
}


def capped_time(frame: pd.DataFrame, method: str) -> pd.Series:
    meta = METHODS[method]
    solved = frame[meta["solved_col"]].astype(bool)
    times = pd.to_numeric(frame[meta["time_col"]], errors="coerce").fillna(TIME_CAP)
    return times.where(solved, TIME_CAP).clip(upper=TIME_CAP)


def solved_within(frame: pd.DataFrame, method: str, cap: float) -> pd.Series:
    meta = METHODS[method]
    solved = frame[meta["solved_col"]].astype(bool)
    times = pd.to_numeric(frame[meta["time_col"]], errors="coerce").fillna(TIME_CAP)
    return solved & (times <= cap)


def single_method_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, meta in METHODS.items():
        times = pd.to_numeric(frame[meta["time_col"]], errors="coerce").fillna(TIME_CAP)
        solved = frame[meta["solved_col"]].astype(bool)
        capped = capped_time(frame, method)
        rows.append(
            {
                "method": method,
                "paper_name": meta["paper_name"],
                "solved": int(solved.sum()),
                "total": len(frame),
                "actual_mean_time": float(times.mean()),
                "actual_median_time": float(times.median()),
                "capped_mean_time": float(capped.mean()),
                "capped_median_time": float(capped.median()),
            }
        )
    return pd.DataFrame(rows)


def parallel_pair_summary(frame: pd.DataFrame, method: str) -> tuple[dict[str, object], pd.DataFrame]:
    method_time = capped_time(frame, method)
    cadical_time = capped_time(frame, "cadical")
    method_solved = frame[METHODS[method]["solved_col"]].astype(bool)
    cadical_solved = frame[METHODS["cadical"]["solved_col"]].astype(bool)
    union_solved = method_solved | cadical_solved
    parallel_time = pd.concat([method_time, cadical_time], axis=1).min(axis=1)

    per_instance = frame[
        [
            "file_key",
            METHODS[method]["solved_col"],
            METHODS[method]["time_col"],
            "cadical_solved",
            "cadical_time",
            "pattern",
        ]
    ].copy()
    per_instance["method"] = method
    per_instance["paper_name"] = METHODS[method]["paper_name"]
    per_instance["parallel_solved"] = union_solved
    per_instance["parallel_time"] = parallel_time
    per_instance["winner"] = "none"
    per_instance.loc[method_solved & ~cadical_solved, "winner"] = method
    per_instance.loc[~method_solved & cadical_solved, "winner"] = "cadical"
    per_instance.loc[method_solved & cadical_solved & (method_time <= cadical_time), "winner"] = method
    per_instance.loc[method_solved & cadical_solved & (cadical_time < method_time), "winner"] = "cadical"

    row = {
        "method": method,
        "paper_name": METHODS[method]["paper_name"],
        "method_solved": int(method_solved.sum()),
        "cadical_solved": int(cadical_solved.sum()),
        "parallel_union_solved": int(union_solved.sum()),
        "method_only": int((method_solved & ~cadical_solved).sum()),
        "cadical_only": int((cadical_solved & ~method_solved).sum()),
        "both_solved": int((method_solved & cadical_solved).sum()),
        "both_unsolved": int((~method_solved & ~cadical_solved).sum()),
        "parallel_mean_time": float(parallel_time.mean()),
        "parallel_median_time": float(parallel_time.median()),
        "gain_vs_cadical_solved": int(union_solved.sum() - cadical_solved.sum()),
        "gain_vs_method_solved": int(union_solved.sum() - method_solved.sum()),
    }
    return row, per_instance


def sequential_schedule(frame: pd.DataFrame, first: str, second: str, first_cap: float) -> dict[str, object]:
    second_cap = TIME_CAP - first_cap
    first_hit = solved_within(frame, first, first_cap)
    second_hit = solved_within(frame, second, second_cap)
    first_time = capped_time(frame, first)
    second_time = capped_time(frame, second)

    solved = first_hit | (~first_hit & second_hit)
    total_time = pd.Series(TIME_CAP, index=frame.index, dtype=float)
    total_time.loc[first_hit] = first_time.loc[first_hit]
    total_time.loc[~first_hit & second_hit] = first_cap + second_time.loc[~first_hit & second_hit]

    return {
        "first": first,
        "second": second,
        "first_name": METHODS[first]["paper_name"],
        "second_name": METHODS[second]["paper_name"],
        "first_cap": first_cap,
        "second_cap": second_cap,
        "solved": int(solved.sum()),
        "mean_time": float(total_time.mean()),
        "median_time": float(total_time.median()),
    }


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(f"{value:.3f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(IN_PATH)
    frame["pattern"] = frame["pattern"].astype(str).str.zfill(4)

    single = single_method_summary(frame)
    single.to_csv(OUT_DIR / "single_method_summary.csv", index=False)

    parallel_rows = []
    parallel_frames = []
    for method in ["one_shot", "online", "old_compact", "local"]:
        row, per_instance = parallel_pair_summary(frame, method)
        parallel_rows.append(row)
        parallel_frames.append(per_instance)
    parallel = pd.DataFrame(parallel_rows)
    parallel_instances = pd.concat(parallel_frames, ignore_index=True)
    parallel.to_csv(OUT_DIR / "parallel_portfolio_summary.csv", index=False)
    parallel_instances.to_csv(OUT_DIR / "parallel_portfolio_per_instance.csv", index=False)

    schedule_rows = []
    for first, second in [
        ("cadical", "local"),
        ("local", "cadical"),
        ("cadical", "online"),
        ("online", "cadical"),
    ]:
        for first_cap in range(5, 60, 5):
            schedule_rows.append(sequential_schedule(frame, first, second, float(first_cap)))
    schedules = pd.DataFrame(schedule_rows)
    schedules.to_csv(OUT_DIR / "sequential_split_schedule_summary.csv", index=False)
    best_schedules = schedules.sort_values(["solved", "mean_time"], ascending=[False, True]).head(12)
    best_schedules.to_csv(OUT_DIR / "best_sequential_split_schedules.csv", index=False)

    local_only = frame[
        frame["local_correction_solved"].astype(bool) & ~frame["cadical_solved"].astype(bool)
    ][
        [
            "file_key",
            "one_shot_solved",
            "online_solved",
            "old_compact_solved",
            "local_correction_solved",
            "local_correction_time_mean",
            "cadical_solved",
            "cadical_time",
            "pattern",
        ]
    ].sort_values("file_key")
    local_only.to_csv(OUT_DIR / "local_only_instances.csv", index=False)

    best_parallel = parallel.sort_values(["parallel_union_solved", "parallel_mean_time"], ascending=[False, True])
    local_parallel = parallel.loc[parallel["method"] == "local"].iloc[0]
    best_seq = schedules.sort_values(["solved", "mean_time"], ascending=[False, True]).iloc[0]

    doc_lines = [
        "# CaDiCaL / Neural Portfolio Feasibility Audit",
        "",
        "Scope: decision audit only. This does not run new solvers and does not",
        "modify the neural model, selector, thresholds, or Local Boundary Correction.",
        "It asks whether the observed CaDiCaL/neural complementarity can support a",
        "portfolio-style top-conference claim.",
        "",
        "Inputs:",
        "",
        "```text",
        "runs/analysis/cadical_neural_overlap/combined.csv",
        "```",
        "",
        "Important limitation: neural times are 3-seed means from the full400 seed",
        "robustness table, while CaDiCaL is a single 60s run. Sequential schedules",
        "are simulated from full-budget observed times by treating a method as solved",
        "within a sub-budget only when its observed solve time is within that",
        "sub-budget. This is suitable for deciding whether a portfolio claim is worth",
        "a real run, not for replacing a real portfolio experiment.",
        "",
        "## Single-Method Reference",
        "",
        *markdown_table(
            single[["paper_name", "solved", "actual_mean_time", "capped_mean_time"]],
            ["paper_name", "solved", "actual_mean_time", "capped_mean_time"],
        ),
        "",
        "## Parallel Two-Core Oracle Portfolio With CaDiCaL",
        "",
        "This table starts CaDiCaL and the neural workflow together and takes the",
        "first solver to finish. It is a two-core oracle portfolio, not a same-core",
        "runtime result.",
        "",
        *markdown_table(
            parallel[
                [
                    "paper_name",
                    "parallel_union_solved",
                    "method_only",
                    "cadical_only",
                    "parallel_mean_time",
                    "gain_vs_cadical_solved",
                ]
            ],
            [
                "paper_name",
                "parallel_union_solved",
                "method_only",
                "cadical_only",
                "parallel_mean_time",
                "gain_vs_cadical_solved",
            ],
        ),
        "",
        "## Best Simulated Same-Core Split Schedules",
        "",
        "These schedules keep a 60s total budget and split it between CaDiCaL and",
        "a neural workflow. They are conservative simulations from observed full-run",
        "times, not interrupted solver measurements.",
        "",
        *markdown_table(
            best_schedules[
                ["first_name", "second_name", "first_cap", "second_cap", "solved", "mean_time"]
            ],
            ["first_name", "second_name", "first_cap", "second_cap", "solved", "mean_time"],
        ),
        "",
        "## Local-Only Instances Against CaDiCaL",
        "",
        *markdown_table(
            local_only[
                [
                    "file_key",
                    "one_shot_solved",
                    "online_solved",
                    "old_compact_solved",
                    "local_correction_solved",
                    "local_correction_time_mean",
                    "cadical_time",
                    "pattern",
                ]
            ],
            [
                "file_key",
                "one_shot_solved",
                "online_solved",
                "old_compact_solved",
                "local_correction_solved",
                "local_correction_time_mean",
                "cadical_time",
                "pattern",
            ],
        ),
        "",
        "## Decision",
        "",
        f"- The strongest two-core oracle pair is {best_parallel.iloc[0]['paper_name']} + "
        f"CaDiCaL with {int(best_parallel.iloc[0]['parallel_union_solved'])}/200 solved.",
        f"- CaDiCaL + Local Boundary Correction reaches {int(local_parallel['parallel_union_solved'])}/200 "
        f"solved, gaining {int(local_parallel['gain_vs_cadical_solved'])} instances over CaDiCaL alone, "
        f"but {int(local_parallel['cadical_only'])} CaDiCaL-only instances remain.",
        f"- The best simulated same-core 60s split solves {int(best_seq['solved'])}/200 "
        f"({best_seq['first_name']} for {best_seq['first_cap']:.0f}s, then "
        f"{best_seq['second_name']} for {best_seq['second_cap']:.0f}s), which is "
        f"{int(best_seq['solved']) - int(frame['cadical_solved'].sum())} above CaDiCaL alone.",
        "- Therefore the current evidence supports a concrete portfolio follow-up:",
        "  the simulated same-core split has a small but nonzero solved-count gain,",
        "  and the two-core oracle portfolio has a larger complementarity upper bound.",
        "- For a top-conference performance paper, this still requires a real",
        "  interrupted schedule run. The current audit is strong enough to justify",
        "  that experiment, but not to replace it.",
        "",
        "Generated artifacts:",
        "",
        "```text",
        "runs/analysis/cadical_portfolio_feasibility/single_method_summary.csv",
        "runs/analysis/cadical_portfolio_feasibility/parallel_portfolio_summary.csv",
        "runs/analysis/cadical_portfolio_feasibility/parallel_portfolio_per_instance.csv",
        "runs/analysis/cadical_portfolio_feasibility/sequential_split_schedule_summary.csv",
        "runs/analysis/cadical_portfolio_feasibility/best_sequential_split_schedules.csv",
        "runs/analysis/cadical_portfolio_feasibility/local_only_instances.csv",
        "```",
    ]
    DOC_PATH.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")

    print(single.to_string(index=False))
    print(parallel.to_string(index=False))
    print(best_schedules.to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
