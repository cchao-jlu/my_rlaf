from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


BASELINE_CSV = Path("runs/GNN_Glucose_3SAT_V1/eval_oneshot_full400_compactcheck.csv")
OLD_COMPACT_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/"
    "eval_compact_risk_full400.csv"
)
ONLINE_CONSISTENT_CSV = Path("runs/analysis/online_consistent_boundary400_full400_actual_batched.csv")
LOCAL_BOUNDARY_CSV = Path(
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride/"
    "eval_local_reopen_guarded_full400.csv"
)

OUT_PDF = Path("figures/fig_full400_cactus_paper.pdf")
OUT_SVG = Path("figures/fig_full400_cactus_paper.svg")
UNSOLVED = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", "nan", "None"}


def is_solved(value: object) -> bool:
    return str(value) not in UNSOLVED


def load_eval(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    frame["solved"] = frame["Result"].map(is_solved)
    return frame


def solved_times(frame: pd.DataFrame) -> list[float]:
    return sorted(float(value) for value in frame.loc[frame["solved"], "time"])


def main() -> None:
    methods = [
        ("One-shot", BASELINE_CSV, "#4c78a8"),
        ("Old Compact", OLD_COMPACT_CSV, "#f58518"),
        ("Online-Consistent Selector", ONLINE_CONSISTENT_CSV, "#54a24b"),
        ("Local Boundary Correction", LOCAL_BOUNDARY_CSV, "#b279a2"),
    ]

    fig, ax = plt.subplots(figsize=(5.7, 3.65))
    for label, path, color in methods:
        times = solved_times(load_eval(path))
        ax.plot(range(1, len(times) + 1), times, label=label, color=color, linewidth=1.9)

    ax.set_title("3SAT-400 full test")
    ax.set_xlabel("Solved instances")
    ax.set_ylabel("Wall-clock time (s)")
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.set_xlim(left=1)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
