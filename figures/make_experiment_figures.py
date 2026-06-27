import matplotlib.pyplot as plt
import numpy as np


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


OUT_DIRS = ["figures", "jluthesis-template/images"]


def save(fig, name):
    fig.tight_layout()
    for out_dir in OUT_DIRS:
        fig.savefig(f"{out_dir}/{name}.pdf", bbox_inches="tight")
        fig.savefig(f"{out_dir}/{name}.svg", bbox_inches="tight")
    plt.close(fig)


def add_labels(ax, bars, fmt="{:.2f}", dy=0.02):
    ymin, ymax = ax.get_ylim()
    offset = (ymax - ymin) * dy
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            fmt.format(value),
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=0,
        )


def plot_total_time_overview():
    datasets = ["3sat/300", "3sat/350", "3sat/400"]
    methods = ["Original solver", "Original RLAF", "Modified", "Composite", "Balanced"]
    values = np.array(
        [
            [12.82, 6.02, 5.59, 4.84, 4.84],
            [107.48, 54.52, 52.15, 47.58, 47.01],
            [1752.45, 863.23, 786.08, 775.28, 763.92],
        ]
    )
    colors = ["#9aa0a6", "#5b8ff9", "#5ad8a6", "#f6bd16", "#f08c00"]

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = np.arange(len(datasets))
    width = 0.15
    for i, method in enumerate(methods):
        ax.bar(x + (i - 2) * width, values[:, i], width, label=method, color=colors[i])

    ax.set_yscale("log")
    ax.set_ylabel("Total time (s, log scale)")
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.grid(axis="y", which="major", linestyle="--", alpha=0.35)
    ax.legend(ncol=2, frameon=False, fontsize=8)
    save(fig, "fig_exp_total_time_overview")


def plot_reward_ablation():
    datasets = ["3sat/300", "3sat/350", "3sat/400"]
    decisions_only_cpu = np.array([4.83, 59.85, 755.69])
    composite_cpu = np.array([4.69, 47.40, 775.08])
    decisions_only_dec = np.array([264035.28, 1665992.51, 12247790.40])
    composite_dec = np.array([268776.57, 1677292.76, 12721036.04])

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2))
    x = np.arange(len(datasets))
    width = 0.34

    axes[0].bar(x - width / 2, decisions_only_cpu, width, label="decisions-only", color="#5b8ff9")
    axes[0].bar(x + width / 2, composite_cpu, width, label="composite", color="#f6bd16")
    axes[0].set_title("CPU time")
    axes[0].set_ylabel("Seconds")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(datasets, rotation=15)
    axes[0].grid(axis="y", linestyle="--", alpha=0.35)

    axes[1].bar(x - width / 2, decisions_only_dec / 1e6, width, label="decisions-only", color="#5b8ff9")
    axes[1].bar(x + width / 2, composite_dec / 1e6, width, label="composite", color="#f6bd16")
    axes[1].set_title("Decisions")
    axes[1].set_ylabel("Millions")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(datasets, rotation=15)
    axes[1].grid(axis="y", linestyle="--", alpha=0.35)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left")

    save(fig, "fig_exp_reward_ablation")


def plot_feedback_ablation():
    labels = ["w/o feedback", "w/ feedback"]
    cpu = np.array([391.66, 47.99])
    decisions = np.array([7476220.45, 1735536.10]) / 1e6
    colors = ["#ff7875", "#52c41a"]

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0))
    bars0 = axes[0].bar(labels, cpu, color=colors, width=0.55)
    axes[0].set_ylabel("CPU time (s)")
    axes[0].set_title("CPU time")
    axes[0].grid(axis="y", linestyle="--", alpha=0.35)
    add_labels(axes[0], bars0)

    bars1 = axes[1].bar(labels, decisions, color=colors, width=0.55)
    axes[1].set_ylabel("Decisions (M)")
    axes[1].set_title("Search scale")
    axes[1].grid(axis="y", linestyle="--", alpha=0.35)
    add_labels(axes[1], bars1)
    save(fig, "fig_exp_feedback_ablation")


def plot_scale_generalization():
    sizes = np.array([300, 350, 400])
    original_rlaf = np.array([6.02, 54.52, 863.23])
    balanced = np.array([4.84, 47.01, 763.92])
    improvement = (balanced - original_rlaf) / original_rlaf * 100.0

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    ax.plot(sizes, improvement, marker="o", linewidth=2.2, color="#2f54eb")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Number of variables")
    ax.set_ylabel("Total time change vs Original RLAF (%)")
    ax.set_xticks(sizes)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    for x, y in zip(sizes, improvement):
        ax.text(x, y - 1.2, f"{y:.1f}%", ha="center", va="top", fontsize=9)
    save(fig, "fig_exp_scale_generalization")


if __name__ == "__main__":
    plot_total_time_overview()
    plot_reward_ablation()
    plot_feedback_ablation()
    plot_scale_generalization()
