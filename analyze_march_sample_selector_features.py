from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch_geometric.loader import DataLoader

from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy.evaluate import sample_var_params


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "data/benchmark_transition_band"
SUBSET_ROOT = ROOT / "data/benchmark_march_sample_selector_features"
OUT_DIR = ROOT / "runs/analysis/benchmark_march_sample_selector_features"
RAW_OUTCOMES = ROOT / "runs/analysis/benchmark_march_sample_portfolio_multiseed/focused_sample_portfolio_raw.csv"
FEATURES_CSV = OUT_DIR / "focused_sample_features.csv"
RANKING_CSV = OUT_DIR / "focused_selector_ranking.csv"
SUMMARY_CSV = OUT_DIR / "focused_selector_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_sample_selector_features.md"
SOLVED = {"SATISFIABLE", "UNSATISFIABLE"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def prepare_subset(outcomes: pd.DataFrame) -> None:
    for row in outcomes[["size", "file_key"]].drop_duplicates().itertuples(index=False):
        size = int(row.size)
        file_key = str(row.file_key)
        source = SOURCE_ROOT / "3sat" / str(size) / file_key
        target_dir = SUBSET_ROOT / "3sat" / str(size)
        target = target_dir / file_key
        target_dir.mkdir(parents=True, exist_ok=True)
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(source.resolve())
        except OSError:
            shutil.copy2(source, target)


def sample_features_for_instance(
    model: torch.nn.Module,
    transform,
    model_cfg,
    size: int,
    file_key: str,
    sample_seed: int,
    num_samples: int,
    device: str,
) -> pd.DataFrame:
    set_seed(sample_seed)
    path = SUBSET_ROOT / "3sat" / str(size) / file_key
    dataset = DimacsCNFDataset(str(path.relative_to(ROOT)), transform=transform, lazy=True)
    loader = DataLoader(dataset=dataset, batch_size=1, num_workers=0, shuffle=False)
    data = sample_var_params(
        model=model,
        loader=loader,
        device=device,
        use_mode=False,
        num_samples=num_samples,
        scale_sigma=float(model_cfg.scale_sigma),
        add_timing=False,
    )[0]

    var_params = data["var"].var_params
    phase = var_params[:, :, 0]
    weight = var_params[:, :, 1]
    log_weight = torch.log(weight.clamp_min(1.0e-12))
    y_var = data["var"].y_var_ref
    y_rho = y_var[:, 0]
    y_mu = y_var[:, 1]
    y_sigma = y_var[:, 2] if y_var.shape[1] > 2 else torch.full_like(y_mu, float(model_cfg.scale_sigma))
    p_phase = torch.sigmoid(y_rho)
    phase_mode = (p_phase >= 0.5).float()
    sample_count = phase.shape[1]
    rows = []
    for sample_id in range(sample_count):
        sample_phase = phase[:, sample_id]
        sample_weight = weight[:, sample_id]
        sample_log_weight = log_weight[:, sample_id]
        phase_mode_match = (sample_phase == phase_mode).float()
        rows.append(
            {
                "size": int(size),
                "file_key": file_key,
                "sample_seed": int(sample_seed),
                "sample_id": int(sample_id),
                "log_prob": float(data.log_prob[sample_id]),
                "phase_mean": float(sample_phase.mean()),
                "phase_mode_match": float(phase_mode_match.mean()),
                "weight_mean": float(sample_weight.mean()),
                "weight_std": float(sample_weight.std(unbiased=False)),
                "weight_min": float(sample_weight.min()),
                "weight_max": float(sample_weight.max()),
                "weight_p10": float(torch.quantile(sample_weight, 0.10)),
                "weight_p50": float(torch.quantile(sample_weight, 0.50)),
                "weight_p90": float(torch.quantile(sample_weight, 0.90)),
                "log_weight_mean": float(sample_log_weight.mean()),
                "log_weight_std": float(sample_log_weight.std(unbiased=False)),
                "log_weight_abs_mean": float(sample_log_weight.abs().mean()),
                "model_rho_abs_mean": float(y_rho.abs().mean()),
                "model_mu_mean": float(y_mu.mean()),
                "model_mu_std": float(y_mu.std(unbiased=False)),
                "model_sigma_mean": float(y_sigma.mean()),
            }
        )
    return pd.DataFrame(rows)


def build_features(outcomes: pd.DataFrame, checkpoint: str, device: str) -> pd.DataFrame:
    model, transform, model_cfg = load_checkpoint(checkpoint, var_output=True)
    num_samples = int(outcomes.groupby(["size", "file_key", "sample_seed"]).size().max())
    frames = []
    for row in outcomes[["size", "file_key", "sample_seed"]].drop_duplicates().sort_values(["size", "file_key", "sample_seed"]).itertuples(index=False):
        frames.append(
            sample_features_for_instance(
                model=model,
                transform=transform,
                model_cfg=model_cfg,
                size=int(row.size),
                file_key=str(row.file_key),
                sample_seed=int(row.sample_seed),
                num_samples=num_samples,
                device=device,
            )
        )
    features = pd.concat(frames, ignore_index=True)
    return features


def evaluate_rankings(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = [
        ("log_prob", False),
        ("log_prob", True),
        ("phase_mode_match", False),
        ("phase_mode_match", True),
        ("log_weight_abs_mean", False),
        ("log_weight_abs_mean", True),
        ("weight_std", False),
        ("weight_std", True),
    ]
    ranking_rows = []
    summary_rows = []
    for (size, file_key, sample_seed), group in frame.groupby(["size", "file_key", "sample_seed"], sort=True):
        for metric, ascending in metrics:
            ranked = group.sort_values(metric, ascending=ascending).reset_index(drop=True)
            first_hit = -1
            for idx, row in ranked.iterrows():
                if bool(row["solved_strict60"]):
                    first_hit = int(idx + 1)
                    break
            top1 = bool(ranked.iloc[0]["solved_strict60"])
            top2 = bool(ranked.head(2)["solved_strict60"].any())
            top4 = bool(ranked.head(4)["solved_strict60"].any())
            ranking_rows.append(
                {
                    "size": int(size),
                    "file_key": file_key,
                    "sample_seed": int(sample_seed),
                    "metric": metric,
                    "ascending": bool(ascending),
                    "strict60_solved_samples": int(group["solved_strict60"].sum()),
                    "top1_hit": top1,
                    "top2_hit": top2,
                    "top4_hit": top4,
                    "first_hit_rank": first_hit,
                }
            )
    ranking = pd.DataFrame(ranking_rows)
    for (metric, ascending), group in ranking.groupby(["metric", "ascending"], sort=True):
        positives = group[group["strict60_solved_samples"] > 0]
        summary_rows.append(
            {
                "metric": metric,
                "ascending": bool(ascending),
                "groups": int(len(group)),
                "positive_groups": int(len(positives)),
                "top1_hits": int(group["top1_hit"].sum()),
                "top2_hits": int(group["top2_hit"].sum()),
                "top4_hits": int(group["top4_hit"].sum()),
                "positive_top1_hits": int(positives["top1_hit"].sum()),
                "positive_top2_hits": int(positives["top2_hit"].sum()),
                "positive_top4_hits": int(positives["top4_hit"].sum()),
                "mean_first_hit_rank_positive": float(positives.loc[positives["first_hit_rank"] > 0, "first_hit_rank"].mean())
                if not positives.empty
                else float("nan"),
            }
        )
    return ranking, pd.DataFrame(summary_rows)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(summary: pd.DataFrame) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    ranked = summary.sort_values(["positive_top1_hits", "positive_top2_hits", "positive_top4_hits"], ascending=False)
    lines = [
        "# March Sample Selector Feature Audit",
        "",
        "Scope: cheap selector-feature audit for sampled March guidance. It joins",
        "policy-sampling features with focused sampled-portfolio outcomes. This",
        "does not train a selector and does not run additional SAT solving.",
        "",
        "## Ranking Summary",
        "",
        *markdown_table(
            ranked,
            [
                "metric",
                "ascending",
                "groups",
                "positive_groups",
                "positive_top1_hits",
                "positive_top2_hits",
                "positive_top4_hits",
                "mean_first_hit_rank_positive",
            ],
        ),
        "",
        "## Interpretation",
        "",
    ]
    best = ranked.iloc[0]
    if int(best["positive_top1_hits"]) > 0 or int(best["positive_top2_hits"]) > 0:
        lines.extend(
            [
                "- At least one cheap policy-derived metric ranks strict-60 successful",
                "  samples near the top on the focused complement cases.",
                "- This supports trying a learned sample selector / stopping rule before",
                "  changing the March checkpoint objective.",
            ]
        )
    else:
        lines.extend(
            [
                "- These simple policy-derived metrics do not rank strict-60 successful",
                "  samples near the top.",
                "- The next route should use early solver traces or change the training",
                "  objective rather than relying on static sample statistics.",
            ]
        )
    lines.extend(
        [
            "",
            "Artifacts:",
            "",
            "```text",
            str(FEATURES_CSV.relative_to(ROOT)),
            str(RANKING_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze cheap features for sampled March guidance selection.")
    parser.add_argument("--checkpoint", default="runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    outcomes = pd.read_csv(RAW_OUTCOMES)
    outcomes["solved_returned"] = outcomes["Result"].astype(str).isin(SOLVED)
    outcomes["solved_strict60"] = outcomes["solved_returned"] & (outcomes["CPU time"].astype(float) <= 60.0)
    prepare_subset(outcomes)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    features = build_features(outcomes, checkpoint=args.checkpoint, device=args.device)
    joined = features.merge(
        outcomes[
            [
                "size",
                "file_key",
                "sample_seed",
                "sample_id",
                "Result",
                "CPU time",
                "decisions",
                "solved_returned",
                "solved_strict60",
            ]
        ],
        on=["size", "file_key", "sample_seed", "sample_id"],
        how="left",
        validate="one_to_one",
    )
    joined.to_csv(FEATURES_CSV, index=False)
    ranking, summary = evaluate_rankings(joined)
    ranking.to_csv(RANKING_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(summary)
    print(summary.sort_values(["positive_top1_hits", "positive_top2_hits", "positive_top4_hits"], ascending=False).to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
