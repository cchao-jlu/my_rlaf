from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent


COLORS = {
    "graph": "#F4F6F8",
    "gnn": "#E8F1FB",
    "solver": "#FDEEEE",
    "state": "#FFF3D7",
    "output": "#EAF6EA",
    "loss": "#F2EAFB",
    "line": "#2F3A45",
}


def setup(width: float, height: float):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def box(ax, xy, wh, text, color, fontsize=10, lw=1.4):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=lw,
        edgecolor=COLORS["line"],
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#1F2933",
        linespacing=1.25,
    )
    return patch


def arrow(ax, start, end, text=None, rad=0.0, fontsize=8):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(
            arrowstyle="-|>",
            lw=1.4,
            color=COLORS["line"],
            shrinkA=4,
            shrinkB=4,
            connectionstyle=f"arc3,rad={rad}",
        ),
    )
    if text:
        mx = (start[0] + end[0]) / 2
        my = (start[1] + end[1]) / 2
        ax.text(mx, my + 0.028, text, ha="center", va="center", fontsize=fontsize, color="#475569")


def title(ax, text):
    ax.text(0.5, 0.96, text, ha="center", va="top", fontsize=13, fontweight="bold", color="#111827")


def save(fig, name):
    for ext in ("pdf", "svg"):
        fig.savefig(OUT_DIR / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def architecture():
    fig, ax = setup(13.5, 3.8)
    title(ax, "Graph-level feedback-conditioned SAT guidance model")

    box(ax, (0.03, 0.58), (0.13, 0.15), "Literal features\nx_lit", COLORS["graph"])
    box(ax, (0.03, 0.31), (0.13, 0.15), "Clause features\nx_cls", COLORS["graph"])
    box(ax, (0.21, 0.58), (0.13, 0.15), "Literal\nencoder", COLORS["gnn"])
    box(ax, (0.21, 0.31), (0.13, 0.15), "Clause\nencoder", COLORS["gnn"])
    box(ax, (0.40, 0.39), (0.18, 0.24), "SAT GNN layers\nlit -> clause -> lit\nL message-passing steps", COLORS["gnn"], fontsize=9)
    box(ax, (0.64, 0.43), (0.14, 0.16), "Variable pairing\n[h_v-, h_v+]", COLORS["gnn"], fontsize=9)
    box(ax, (0.70, 0.69), (0.14, 0.14), "Graph-level\nstate z in R^6", COLORS["state"], fontsize=9)
    box(ax, (0.83, 0.43), (0.12, 0.16), "Readout MLP\nconcat z", COLORS["gnn"], fontsize=9)
    box(ax, (0.97, 0.43), (0.01, 0.16), "", COLORS["output"])
    ax.text(0.965, 0.51, "Guidance\nphase, weight", ha="right", va="center", fontsize=10, color="#1F2933")

    arrow(ax, (0.16, 0.655), (0.21, 0.655))
    arrow(ax, (0.16, 0.385), (0.21, 0.385))
    arrow(ax, (0.34, 0.655), (0.40, 0.56))
    arrow(ax, (0.34, 0.385), (0.40, 0.46))
    arrow(ax, (0.58, 0.51), (0.64, 0.51))
    arrow(ax, (0.78, 0.51), (0.83, 0.51))
    arrow(ax, (0.77, 0.69), (0.87, 0.59), text="condition")
    arrow(ax, (0.95, 0.51), (0.965, 0.51))

    ax.text(0.075, 0.19, "Static CNF graph", ha="center", fontsize=9, color="#475569")
    ax.text(0.78, 0.19, "Feedback affects readout, not message passing", ha="center", fontsize=9, color="#475569")
    save(fig, "fig_global_state_architecture")


def inference_refinement():
    fig, ax = setup(14.5, 4.2)
    title(ax, "Single-step feedback refinement at evaluation time")

    y1 = 0.62
    y2 = 0.29
    box(ax, (0.03, y1), (0.10, 0.14), "CNF graph\nG", COLORS["graph"])
    box(ax, (0.17, y1), (0.11, 0.14), "GNN\nz = 0", COLORS["gnn"])
    box(ax, (0.32, y1), (0.12, 0.14), "Initial\nguidance a0", COLORS["output"])
    box(ax, (0.48, y1), (0.13, 0.14), "SAT solver\nwarmup", COLORS["solver"])
    box(ax, (0.65, y1), (0.12, 0.14), "Solver stats\ns0", COLORS["state"])
    box(ax, (0.80, y1), (0.14, 0.14), "Feedback encoder\nz = phi(s0)", COLORS["state"])

    box(ax, (0.66, y2), (0.14, 0.14), "GNN\nconditioned on z", COLORS["gnn"])
    box(ax, (0.49, y2), (0.13, 0.14), "Refined\nguidance a1", COLORS["output"])
    box(ax, (0.32, y2), (0.13, 0.14), "SAT solver\nfinal run", COLORS["solver"])
    box(ax, (0.15, y2), (0.12, 0.14), "Result and\nstatistics", COLORS["output"])

    arrow(ax, (0.13, y1 + 0.07), (0.17, y1 + 0.07))
    arrow(ax, (0.28, y1 + 0.07), (0.32, y1 + 0.07))
    arrow(ax, (0.44, y1 + 0.07), (0.48, y1 + 0.07))
    arrow(ax, (0.61, y1 + 0.07), (0.65, y1 + 0.07))
    arrow(ax, (0.77, y1 + 0.07), (0.80, y1 + 0.07))
    arrow(ax, (0.87, y1), (0.74, y2 + 0.14), text="attach z")
    arrow(ax, (0.66, y2 + 0.07), (0.62, y2 + 0.07))
    arrow(ax, (0.49, y2 + 0.07), (0.45, y2 + 0.07))
    arrow(ax, (0.32, y2 + 0.07), (0.27, y2 + 0.07))
    arrow(ax, (0.08, y1), (0.67, y2 + 0.03), text="reuse G", rad=-0.15)

    ax.text(0.49, 0.87, "Pass 1: produce feedback", ha="center", fontsize=10, color="#475569")
    ax.text(0.48, 0.15, "Pass 2: produce final guidance", ha="center", fontsize=10, color="#475569")
    save(fig, "fig_feedback_refinement_inference")


def training_improver():
    fig, ax = setup(15.5, 4.8)
    title(ax, "Feedback improver training with mixed warmup and composite GRPO objective")

    box(ax, (0.03, 0.60), (0.10, 0.14), "CNF graph\nG", COLORS["graph"])
    box(ax, (0.18, 0.75), (0.13, 0.13), "Random warmup\nguidance", COLORS["graph"], fontsize=9)
    box(ax, (0.18, 0.49), (0.13, 0.13), "Model warmup\nguidance", COLORS["gnn"], fontsize=9)
    box(ax, (0.36, 0.60), (0.13, 0.14), "Mixed warmup\np_model = 0.5", COLORS["state"], fontsize=9)
    box(ax, (0.54, 0.60), (0.13, 0.14), "SAT solver\nshort rollout", COLORS["solver"])
    box(ax, (0.72, 0.60), (0.13, 0.14), "Global state\nz = phi(s)", COLORS["state"])

    box(ax, (0.66, 0.28), (0.15, 0.14), "Feedback improver\none GNN forward", COLORS["gnn"], fontsize=9)
    box(ax, (0.46, 0.28), (0.15, 0.14), "Sample K refined\nguidance candidates", COLORS["output"], fontsize=9)
    box(ax, (0.27, 0.28), (0.13, 0.14), "SAT solver\nfinal runs", COLORS["solver"])
    box(ax, (0.05, 0.27), (0.17, 0.16), "Composite cost\nlog(1+t) + 0.4 log(1+c)\n+ 0.05 log(1+d)", COLORS["loss"], fontsize=8.5)
    box(ax, (0.46, 0.06), (0.15, 0.12), "GRPO update", COLORS["loss"])

    arrow(ax, (0.13, 0.67), (0.36, 0.67))
    arrow(ax, (0.31, 0.815), (0.36, 0.70))
    arrow(ax, (0.31, 0.555), (0.36, 0.64))
    arrow(ax, (0.49, 0.67), (0.54, 0.67))
    arrow(ax, (0.67, 0.67), (0.72, 0.67))
    arrow(ax, (0.78, 0.60), (0.74, 0.42), text="condition")
    arrow(ax, (0.08, 0.60), (0.66, 0.35), text="reuse G", rad=-0.10)
    arrow(ax, (0.66, 0.35), (0.61, 0.35))
    arrow(ax, (0.46, 0.35), (0.40, 0.35))
    arrow(ax, (0.27, 0.35), (0.22, 0.35))
    arrow(ax, (0.14, 0.27), (0.46, 0.12), rad=-0.15)
    arrow(ax, (0.61, 0.12), (0.72, 0.28), text="update")

    ax.text(0.51, 0.91, "Input state generation", ha="center", fontsize=10, color="#475569")
    ax.text(0.43, 0.02, "One-step improver objective", ha="center", fontsize=10, color="#475569")
    save(fig, "fig_feedback_improver_training")


def main():
    architecture()
    inference_refinement()
    training_improver()


if __name__ == "__main__":
    main()
