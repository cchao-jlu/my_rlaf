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
CADICAL_REPEAT = Path("runs/analysis/cadical_repeat_stability/repeat_summary.csv")
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
    cadical = pd.read_csv(CADICAL_REPEAT)

    repeats = repeats.sort_values("repeat")
    cadical = cadical.sort_values("repeat")
    left_labels = [f"r{int(r)}" for r in repeats["repeat"]]
    portfolio_values = repeats["portfolio_solved"].astype(int).tolist()
    cadical_values = cadical["cadical_solved"].astype(int).tolist()

    split_order = [
        ("stable_neural_first_complement", "Original\nneural-first", "#4c78a8"),
        ("stable_second_stage_runtime_boundary", "Stable\nruntime\nboundary", "#f58518"),
        ("unstable_second_stage_runtime_boundary", "Unstable\nruntime\nboundary", "#f2c14e"),
    ]
    split_map = dict(zip(split["claim_class"], split["instances"]))
    right_labels = [label for _, label, _ in split_order] + ["Repeated\nstrict\nneural-first"]
    right_values = [int(split_map.get(key, 0)) for key, _, _ in split_order] + [1]
    right_colors = [color for _, _, color in split_order] + ["#2f7f7f"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.25, 1.0]})

    left = axes[0]
    x = range(len(left_labels))
    width = 0.34
    cad_bars = left.bar([i - width / 2 for i in x], cadical_values, color="#8a8f98", width=width, label="CaDiCaL 60s")
    port_bars = left.bar([i + width / 2 for i in x], portfolio_values, color="#2f7f7f", width=width, label="Local5 -> CaDiCaL55")
    for idx, (portfolio, cad) in enumerate(zip(portfolio_values, cadical_values)):
        left.text(idx, max(portfolio, cad) + 3.0, f"{portfolio - cad:+d}", ha="center", va="bottom", fontsize=8)
    add_value_labels(left, cad_bars)
    add_value_labels(left, port_bars)
    left.set_title("Matched full400 repeats")
    left.set_ylabel("Solved instances / 200")
    left.set_ylim(0, 90)
    left.set_xticks(list(x))
    left.set_xticklabels(left_labels)
    left.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    left.legend(frameon=False, fontsize=8, loc="upper left")

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

    fig.suptitle("Portfolio advantage is boundary-sensitive on 3SAT-400", y=1.02, fontsize=11)
    fig.tight_layout()

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_SVG, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
