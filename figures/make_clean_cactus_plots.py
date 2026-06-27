from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class MethodSpec:
    key: str
    label: str
    color: str
    marker: str
    path_template: str


METHODS = [
    MethodSpec(
        key="oneshot",
        label="one-shot",
        color="#4c78a8",
        marker="o",
        path_template="runs/GNN_Glucose_3SAT_V1/eval_oneshot_{size}_optimized_events_gated.csv",
    ),
    MethodSpec(
        key="fixed_rho",
        label="fixed-rho",
        color="#f58518",
        marker="s",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/"
            "eval_trace_adapter_rho_gate_{size}_optimized_events_gated.csv"
        ),
    ),
    MethodSpec(
        key="polarity_gate_min095",
        label="polarity-gate-min095",
        color="#54a24b",
        marker="^",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_PolarityGateMin095/"
            "eval_polarity_gate_min095_{size}_optimized_events_gated.csv"
        ),
    ),
    MethodSpec(
        key="sbe_polarity_conservative",
        label="conservative SBE polarity",
        color="#e45756",
        marker="D",
        path_template=(
            "runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarityConservative/"
            "eval_sbe_polarity_conservative_{size}_optimized_events_gated.csv"
        ),
    ),
]


def solved_times(csv_path: Path) -> list[float]:
    frame = pd.read_csv(csv_path)
    solved = frame[frame["Result"] != "INDETERMINATE"].copy()
    return sorted(float(value) for value in solved["time"].tolist())


def plot_size(ax, size: int) -> None:
    for method in METHODS:
        csv_path = Path(method.path_template.format(size=size))
        if not csv_path.exists():
            continue
        times = solved_times(csv_path)
        if not times:
            continue
        ax.plot(
            range(1, len(times) + 1),
            times,
            label=method.label,
            color=method.color,
            linewidth=1.8,
            marker=method.marker,
            markevery=max(1, len(times) // 8),
            markersize=3.8,
        )
    ax.set_title(f"3SAT-{size}")
    ax.set_xlabel("Solved instances")
    ax.set_ylabel("Total time (s)")
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.set_xlim(left=1)


def save(fig, name: str) -> None:
    out_dir = Path("figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(out_dir / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    sizes = [300, 350, 400]

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.2), sharey=True)
    for ax, size in zip(axes, sizes):
        plot_size(ax, size)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, fontsize=9)
    fig.subplots_adjust(top=0.80)
    save(fig, "fig_clean_cactus_3sat_300_350_400")

    for size in sizes:
        fig, ax = plt.subplots(figsize=(4.4, 3.2))
        plot_size(ax, size)
        ax.legend(frameon=False, fontsize=8)
        save(fig, f"fig_clean_cactus_3sat_{size}")


if __name__ == "__main__":
    main()
