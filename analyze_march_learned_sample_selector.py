from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/benchmark_march_learned_sample_selector"
FEATURE_CSV = ROOT / "runs/analysis/benchmark_march_sample_selector_features/focused_sample_features.csv"
EARLY_CSV = ROOT / "runs/analysis/benchmark_march_early_trace_selector/early_trace_selector_candidates.csv"
PRED_CSV = OUT_DIR / "learned_selector_predictions.csv"
SUMMARY_CSV = OUT_DIR / "learned_selector_summary.csv"
DOC_PATH = ROOT / "docs/benchmark_march_learned_sample_selector.md"


BASE_FEATURES = [
    "log_prob",
    "phase_mean",
    "phase_mode_match",
    "weight_mean",
    "weight_std",
    "weight_min",
    "weight_max",
    "weight_p10",
    "weight_p50",
    "weight_p90",
    "log_weight_mean",
    "log_weight_std",
    "log_weight_abs_mean",
    "model_rho_abs_mean",
    "model_mu_mean",
    "model_mu_std",
    "model_sigma_mean",
]
EARLY_FEATURES = [
    "probe_decisions",
    "probe_lookAheadCount",
    "probe_unitResolveCount",
    "probe_necessary_assignments",
    "probe_dead_ends_in_main",
]
KEYS = ["size", "file_key", "sample_seed", "sample_id"]


def load_frame(use_early: bool) -> pd.DataFrame:
    frame = pd.read_csv(FEATURE_CSV)
    if use_early and EARLY_CSV.exists():
        early = pd.read_csv(EARLY_CSV)
        early = early[KEYS + EARLY_FEATURES].drop_duplicates(KEYS)
        frame = frame.merge(early, on=KEYS, how="left", validate="one_to_one")
    frame["solved_strict60"] = frame["solved_strict60"].astype(bool)
    return frame


def make_model(model_name: str, seed: int):
    if model_name == "logistic":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.5, max_iter=1000, random_state=seed),
        )
    if model_name == "rf":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=3,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=seed,
        )
    raise ValueError(f"Unknown model {model_name!r}")


def split_groups(frame: pd.DataFrame, mode: str) -> list[tuple[str, pd.Series]]:
    if mode == "leave_seed_group":
        return [
            (f"{size}/{file_key}/seed{sample_seed}", (frame["size"].eq(size) & frame["file_key"].eq(file_key) & frame["sample_seed"].eq(sample_seed)))
            for size, file_key, sample_seed in frame[["size", "file_key", "sample_seed"]].drop_duplicates().itertuples(index=False)
        ]
    if mode == "leave_instance":
        return [
            (f"{size}/{file_key}", (frame["size"].eq(size) & frame["file_key"].eq(file_key)))
            for size, file_key in frame[["size", "file_key"]].drop_duplicates().itertuples(index=False)
        ]
    raise ValueError(f"Unknown split mode {mode!r}")


def rank_metrics(pred: pd.DataFrame, score_col: str, top_ks: list[int]) -> pd.DataFrame:
    rows = []
    for split, group in pred.groupby("split", sort=True):
        for (size, file_key, sample_seed), sg in group.groupby(["size", "file_key", "sample_seed"], sort=True):
            positive = bool(sg["solved_strict60"].any())
            ranked = sg.sort_values(score_col, ascending=False).reset_index(drop=True)
            first_hit = -1
            for idx, row in ranked.iterrows():
                if bool(row["solved_strict60"]):
                    first_hit = int(idx + 1)
                    break
            base = {
                "split": split,
                "size": int(size),
                "file_key": file_key,
                "sample_seed": int(sample_seed),
                "positive": positive,
                "strict60_solved_samples": int(sg["solved_strict60"].sum()),
                "first_hit_rank": first_hit,
            }
            for top_k in top_ks:
                base[f"top{top_k}_hit"] = bool(ranked.head(top_k)["solved_strict60"].any())
            rows.append(base)
    return pd.DataFrame(rows)


def evaluate(frame: pd.DataFrame, features: list[str], model_name: str, split_mode: str, seed: int) -> pd.DataFrame:
    preds = []
    for split_name, test_mask in split_groups(frame, split_mode):
        train = frame[~test_mask].copy()
        test = frame[test_mask].copy()
        if train["solved_strict60"].nunique() < 2:
            test["score"] = train["solved_strict60"].mean()
        else:
            model = make_model(model_name, seed)
            model.fit(train[features].fillna(0.0), train["solved_strict60"].astype(int))
            if hasattr(model, "predict_proba"):
                test["score"] = model.predict_proba(test[features].fillna(0.0))[:, 1]
            else:
                test["score"] = model.decision_function(test[features].fillna(0.0))
        test["split"] = split_name
        preds.append(test[KEYS + ["split", "solved_strict60", "score"]])
    return pd.concat(preds, ignore_index=True)


def baseline_predictions(frame: pd.DataFrame, metric: str, ascending: bool, split_mode: str) -> pd.DataFrame:
    preds = frame[KEYS + ["solved_strict60", metric]].copy()
    preds["score"] = -preds[metric] if ascending else preds[metric]
    split_names = []
    for _, row in preds.iterrows():
        if split_mode == "leave_instance":
            split_names.append(f"{int(row['size'])}/{row['file_key']}")
        else:
            split_names.append(f"{int(row['size'])}/{row['file_key']}/seed{int(row['sample_seed'])}")
    preds["split"] = split_names
    return preds[KEYS + ["split", "solved_strict60", "score"]]


def summarize(name: str, pred: pd.DataFrame, top_ks: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    ranking = rank_metrics(pred, "score", top_ks)
    positives = ranking[ranking["positive"]]
    row = {
        "selector": name,
        "groups": int(len(ranking)),
        "positive_groups": int(len(positives)),
        "mean_first_hit_rank_positive": float(positives.loc[positives["first_hit_rank"] > 0, "first_hit_rank"].mean())
        if len(positives)
        else float("nan"),
    }
    for top_k in top_ks:
        row[f"top{top_k}_hits"] = float(ranking[f"top{top_k}_hit"].sum())
        row[f"positive_top{top_k}_hits"] = float(positives[f"top{top_k}_hit"].sum())
        row[f"positive_top{top_k}_recall"] = float(positives[f"top{top_k}_hit"].mean()) if len(positives) else float("nan")
    return ranking, pd.DataFrame([row])


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


def write_doc(summary: pd.DataFrame, split_mode: str, use_early: bool) -> None:
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    ranked = summary.sort_values(["positive_top2_recall", "positive_top4_recall", "mean_first_hit_rank_positive"], ascending=[False, False, True])
    lines = [
        "# March Learned Sample Selector Diagnostic",
        "",
        "Scope: offline cross-validated diagnostic for learned sample selection.",
        "It uses existing sampled-guidance outcomes only; it does not run new SAT",
        "solving and does not claim a deployable result.",
        "",
        f"Split mode: {split_mode}; early-trace features: {use_early}.",
        "",
        "## Summary",
        "",
        *markdown_table(
            ranked,
            [
                "selector",
                "groups",
                "positive_groups",
                "positive_top1_hits",
                "positive_top2_hits",
                "positive_top4_hits",
                "positive_top2_recall",
                "mean_first_hit_rank_positive",
            ],
        ),
        "",
        "## Decision",
        "",
    ]
    best = ranked.iloc[0]
    learned = ranked[ranked["selector"].str.startswith("learned_")]
    best_learned = learned.iloc[0] if not learned.empty else None
    learned_beats_best_baseline = (
        best_learned is not None
        and bool(str(best["selector"]).startswith("learned_"))
        and float(best_learned["positive_top2_recall"]) > 0.8
    )
    if learned_beats_best_baseline:
        lines.extend(
            [
                "- The learned/offline selector signal is strong enough to justify a",
                "  real fixed-budget learned selector runner on a larger generated",
                "  transition-band set.",
                "- This remains a gate, not a paper claim, until evaluated on held-out",
                "  instances beyond the focused four-instance set.",
            ]
        )
    elif str(best["selector"]).startswith("baseline_") and float(best["positive_top2_recall"]) >= 1.0:
        lines.extend(
            [
                "- A simple early-trace baseline is stronger than the learned selector",
                "  on this focused diagnostic.",
                "- The next experiment should expand the strong-union-unsolved sampled",
                "  set and test whether this early-trace signal generalizes before",
                "  investing in a learned selector.",
            ]
        )
    else:
        lines.extend(
            [
                "- The focused data is too small or too weak for a learned selector",
                "  to support a top-conference claim.",
                "- The next model step should generate a larger strong-union-unsolved",
                "  training/evaluation set or change the March policy objective.",
            ]
        )
    lines.extend(
        [
            "",
            "Artifacts:",
            "",
            "```text",
            str(PRED_CSV.relative_to(ROOT)),
            str(SUMMARY_CSV.relative_to(ROOT)),
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline learned selector diagnostic for sampled March guidance.")
    parser.add_argument("--split-mode", default="leave_seed_group", choices=["leave_seed_group", "leave_instance"])
    parser.add_argument("--use-early", action="store_true")
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()

    frame = load_frame(use_early=args.use_early)
    features = BASE_FEATURES + (EARLY_FEATURES if args.use_early else [])
    top_ks = [1, 2, 4, 8]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pred_frames = []
    summary_frames = []
    selectors = [
        ("learned_logistic", evaluate(frame, features, "logistic", args.split_mode, args.seed)),
        ("learned_rf", evaluate(frame, features, "rf", args.split_mode, args.seed)),
        ("baseline_low_log_prob", baseline_predictions(frame, "log_prob", True, args.split_mode)),
        ("baseline_high_weight_std", baseline_predictions(frame, "weight_std", False, args.split_mode)),
    ]
    if args.use_early:
        selectors.extend(
            [
                ("baseline_high_deadends", baseline_predictions(frame, "probe_dead_ends_in_main", False, args.split_mode)),
                ("baseline_high_unitresolve", baseline_predictions(frame, "probe_unitResolveCount", False, args.split_mode)),
            ]
        )

    for name, pred in selectors:
        pred = pred.copy()
        pred["selector"] = name
        pred_frames.append(pred)
        _, summary = summarize(name, pred, top_ks)
        summary_frames.append(summary)

    predictions = pd.concat(pred_frames, ignore_index=True)
    summary = pd.concat(summary_frames, ignore_index=True)
    predictions.to_csv(PRED_CSV, index=False)
    summary.to_csv(SUMMARY_CSV, index=False)
    write_doc(summary, args.split_mode, args.use_early)

    print(summary.sort_values(["positive_top2_recall", "positive_top4_recall", "mean_first_hit_rank_positive"], ascending=[False, False, True]).to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
