from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from omegaconf import OmegaConf


DEFAULT_SOURCE = (
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400Conservative/best.pt"
)
DEFAULT_OUTPUT = (
    "runs/GNN_Glucose_3SAT_TwoStageRiskControllerOnlineConsistentBoundary400LocalReopenOverride"
)
DEFAULT_FEATURES = [
    "local_reopen_candidate",
    "warmup_c1000_minus_warmup_c750_decisions",
    "warmup_c2000_rho_event_corr",
]
DEFAULT_OPS = [">=", ">=", ">="]
DEFAULT_VALUES = [1.0, 294.0, 0.0365]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a two-stage selector checkpoint and add a local reopen override."
    )
    parser.add_argument("--checkpoint", default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--features", default=",".join(DEFAULT_FEATURES))
    parser.add_argument("--ops", default=",".join(DEFAULT_OPS))
    parser.add_argument("--values", default=",".join(str(value) for value in DEFAULT_VALUES))
    return parser.parse_args()


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]


def ensure_selector_features(adapter, feature_names: list[str]) -> None:
    existing = list(adapter.selector_feature_names) if adapter.selector_feature_names is not None else []
    for name in feature_names:
        if name not in existing:
            existing.append(name)
    if "local_reopen_candidate" in existing:
        existing = ["local_reopen_candidate", *[name for name in existing if name != "local_reopen_candidate"]]
    adapter.selector_feature_names = existing


def export_checkpoint(
    checkpoint: str,
    output_dir: str,
    feature_names: list[str],
    ops: list[str],
    values: list[float],
) -> Path:
    if not (len(feature_names) == len(ops) == len(values)):
        raise ValueError("features, ops, and values must have the same length")
    source_ckpt = Path(checkpoint)
    source_cfg = source_ckpt.parent / "config.yaml"
    if not source_ckpt.exists():
        raise FileNotFoundError(source_ckpt)
    if not source_cfg.exists():
        raise FileNotFoundError(source_cfg)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_ckpt, output / "best.pt")

    cfg = OmegaConf.load(source_cfg)
    adapter = cfg.model.event_adapter
    ensure_selector_features(adapter, feature_names)
    adapter.local_reopen_enabled = True
    adapter.local_reopen_feature_names = feature_names
    adapter.local_reopen_ops = ops
    adapter.local_reopen_values = values
    if "local_reopen_candidate" not in adapter.local_reopen_feature_names:
        adapter.local_reopen_feature_names = ["local_reopen_candidate", *adapter.local_reopen_feature_names]
        adapter.local_reopen_ops = [">=", *adapter.local_reopen_ops]
        adapter.local_reopen_values = [1.0, *adapter.local_reopen_values]
    ensure_selector_features(adapter, ["local_reopen_candidate"])
    OmegaConf.save(cfg, output / "config.yaml")
    return output / "best.pt"


def main() -> None:
    args = parse_args()
    feature_names = parse_csv(args.features)
    ops = parse_csv(args.ops)
    values = [float(value) for value in parse_csv(args.values)]
    output = export_checkpoint(
        checkpoint=args.checkpoint,
        output_dir=args.output_dir,
        feature_names=feature_names,
        ops=ops,
        values=values,
    )
    print(output)


if __name__ == "__main__":
    main()
