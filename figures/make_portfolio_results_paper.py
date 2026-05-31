from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


REPEAT_SUMMARY = Path("runs/analysis/portfolio_e2e_local5_cadical55/repeat_stability_summary.csv")
CLAIM_SPLIT = Path("runs/analysis/portfolio_e2e_local5_cadical55/portfolio_claim_split_summary.csv")
OUT_PDF = Path("figures/fig_portfolio_full400_paper.pdf")
OUT_SVG = Path("figures/fig_portfolio_full400_paper.svg")


def add_value_labels(ax, bars, suffix: str = "") -> None:
    ymin, ymax = ax.get_ylim()
    offset = (ymax - ymin) * 0.025
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            f"{value:.0f}{suffix}",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def main() -> None:
    repeats = pd.read_csv(REPEAT_SUMMARY)
    split = pd.read_csv(CLAIM_SPLIT)

    baseline = int(repeats["cadical_60s_baseline_solved"].iloc[0])
    left_labels = ["CaDiCaL\n60s", "Portfolio\nr0", "Portfolio\nr1", "Portfolio\nr2"]
    left_values = [baseline, *repeats.sort_values("repeat")["portfolio_solved"].astype(int).tolist()]
    left_colors = ["#8a8f98", "#2f7f7f", "#2f7f7f", "#2f7f7f"]

    split_order = [
        ("stable_neural_first_complement", "Stable\nneural-first", "#4c78a8"),
        ("stable_second_stage_runtime_boundary", "Stable\nruntime\nboundary", "#f58518"),
        ("unstable_second_stage_runtime_boundary", "Unstable\nruntime\nboundary", "#f2c14e"),
    ]
    split_map = dict(zip(split["claim_class"], split["instances"]))
    right_labels = [label for _, label, _ in split_order]
    right_values = [int(split_map.get(key, 0)) for key, _, _ in split_order]
    right_colors = [color for _, _, color in split_order]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.25, 1.0]})

    left = axes[0]
    bars = left.bar(range(len(left_values)), left_values, color=left_colors, width=0.64)
    left.axhline(baseline, color="#555555", linewidth=1.0, linestyle="--", alpha=0.7)
    left.text(3.38, baseline + 0.5, "CaDiCaL 60s", ha="right", va="bottom", fontsize=8, color="#555555")
    for idx, value in enumerate(left_values[1:], start=1):
        left.text(idx, value + 3.4, f"+{value - baseline}", ha="center", va="bottom", fontsize=8, color="#1f5f5f")
    add_value_labels(left, bars)
    left.set_title("Full400 solved count")
    left.set_ylabel("Solved instances / 200")
    left.set_ylim(0, 90)
    left.set_xticks(range(len(left_labels)))
    left.set_xticklabels(left_labels)
    left.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)

    right = axes[1]
    bars = right.bar(range(len(right_values)), right_values, color=right_colors, width=0.62)
    bars[1].set_hatch("//")
    bars[2].set_hatch("..")
    add_value_labels(right, bars)
    right.set_title("Portfolio-only evidence")
    right.set_ylabel("Instances")
    right.set_ylim(0, 5)
    right.set_yticks(range(0, 6))
    right.set_xticks(range(len(right_labels)))
    right.set_xticklabels(right_labels)
    right.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)

    fig.suptitle("Local5 -> CaDiCaL55 portfolio on 3SAT-400", y=1.02, fontsize=11)
    fig.tight_layout()

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
