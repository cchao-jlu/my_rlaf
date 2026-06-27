from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "runs/analysis/candidate_split_manifest"
DEFAULT_DOC = ROOT / "docs/candidate_split_manifest.md"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_row_id(row: pd.Series) -> str:
    return f"{row['family']}:{int(row['size'])}:{row['file_key']}"


def build_candidate_frame(sizes: list[int], instances: int, cnf_root: Path) -> pd.DataFrame:
    rows = []
    for size in sizes:
        for idx in range(instances):
            file_key = f"3sat_{idx}.cnf"
            rows.append(
                {
                    "family": "3sat",
                    "size": int(size),
                    "file_key": file_key,
                    "cnf_path": str(cnf_root / "3sat" / str(size) / file_key),
                    "row_id": f"3sat:{int(size)}:{file_key}",
                }
            )
    return pd.DataFrame(rows)


def assign_splits(frame: pd.DataFrame, train_frac: float, dev_frac: float, seed: int) -> pd.DataFrame:
    if not 0.0 <= train_frac <= 1.0 or not 0.0 <= dev_frac <= 1.0:
        raise ValueError("Fractions must be in [0, 1].")
    if train_frac + dev_frac >= 1.0:
        raise ValueError("train_frac + dev_frac must leave held-out candidates.")

    rows = []
    rng = random.Random(seed)
    for size, group in frame.groupby("size", sort=True):
        indices = list(group.index)
        rng.shuffle(indices)
        n = len(indices)
        train_n = int(round(n * train_frac))
        dev_n = int(round(n * dev_frac))
        if n >= 3:
            train_n = max(1, min(train_n, n - 2))
            dev_n = max(1, min(dev_n, n - train_n - 1))
        split_for = {}
        for idx in indices[:train_n]:
            split_for[idx] = "candidate_train"
        for idx in indices[train_n : train_n + dev_n]:
            split_for[idx] = "candidate_dev"
        for idx in indices[train_n + dev_n :]:
            split_for[idx] = "candidate_heldout"
        for idx in group.index:
            row = group.loc[idx].to_dict()
            row["split"] = split_for[idx]
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["split", "size", "file_key"]).reset_index(drop=True)


def verify_existing_files(manifest: pd.DataFrame) -> int:
    missing = 0
    for path in manifest["cnf_path"].astype(str):
        if not Path(path).exists():
            missing += 1
    return missing


def markdown_table(frame: pd.DataFrame) -> list[str]:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return lines


def write_doc(
    manifest: pd.DataFrame,
    output_dir: Path,
    doc_path: Path,
    cnf_root: Path,
    sizes: list[int],
    instances: int,
    generation_seed: int,
    split_seed: int,
    train_frac: float,
    dev_frac: float,
    missing_files: int,
    manifest_sha256: str,
) -> None:
    totals = manifest.groupby("split", sort=True).size().reset_index(name="instances")
    by_size = manifest.groupby(["split", "size"], sort=True).size().reset_index(name="instances")
    lines = [
        "# Candidate Split Manifest",
        "",
        "Scope: immutable train/dev/held-out split over the full transition-band",
        "candidate denominator, before March/CaDiCaL residual filtering and before",
        "any neural selector or non-neural rerun schedule tuning.",
        "",
        "## Source",
        "",
        f"- CNF root: `{display_path(cnf_root)}`",
        f"- sizes: `{', '.join(str(size) for size in sizes)}`",
        f"- instances per size: `{instances}`",
        f"- generation seed: `{generation_seed}`",
        f"- split seed: `{split_seed}`",
        f"- train fraction: `{train_frac}`",
        f"- dev fraction: `{dev_frac}`",
        f"- missing CNF files at manifest time: `{missing_files}`",
        f"- manifest sha256: `{manifest_sha256}`",
        "",
        "## Split Totals",
        "",
        *markdown_table(totals),
        "",
        "## Split By Size",
        "",
        *markdown_table(by_size),
        "",
        "## Artifacts",
        "",
        "```text",
        display_path(output_dir / "manifest.csv"),
        display_path(output_dir / "candidate_train.csv"),
        display_path(output_dir / "candidate_dev.csv"),
        display_path(output_dir / "candidate_heldout.csv"),
        display_path(output_dir / "candidate_split_metadata.json"),
        "```",
    ]
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an immutable full-candidate split manifest.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[410, 425, 440])
    parser.add_argument("--instances", type=int, default=300)
    parser.add_argument("--generation-seed", type=int, default=2041)
    parser.add_argument("--split-seed", type=int, default=1729)
    parser.add_argument("--train-frac", type=float, default=0.5)
    parser.add_argument("--dev-frac", type=float, default=0.25)
    parser.add_argument("--cnf-root", type=Path, default=ROOT / "data/benchmark_transition_band_residual_large")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--require-existing", action="store_true")
    args = parser.parse_args()

    cnf_root = args.cnf_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = build_candidate_frame(args.sizes, args.instances, cnf_root=cnf_root)
    manifest = assign_splits(candidates, train_frac=args.train_frac, dev_frac=args.dev_frac, seed=args.split_seed)
    missing_files = verify_existing_files(manifest)
    if args.require_existing and missing_files:
        raise FileNotFoundError(f"{missing_files} candidate CNF files are missing under {cnf_root}")

    manifest_path = output_dir / "manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    for split, group in manifest.groupby("split", sort=True):
        group.to_csv(output_dir / f"{split}.csv", index=False)
    manifest_sha256 = file_sha256(manifest_path)

    metadata = {
        "kind": "full_candidate_split",
        "cnf_root": display_path(cnf_root),
        "sizes": [int(size) for size in args.sizes],
        "instances_per_size": int(args.instances),
        "generation_seed": int(args.generation_seed),
        "split_seed": int(args.split_seed),
        "train_frac": float(args.train_frac),
        "dev_frac": float(args.dev_frac),
        "manifest_rows": int(len(manifest)),
        "manifest_sha256": manifest_sha256,
        "missing_files": int(missing_files),
        "split_counts": {
            str(split): int(count)
            for split, count in manifest.groupby("split", sort=True).size().items()
        },
    }
    (output_dir / "candidate_split_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_doc(
        manifest=manifest,
        output_dir=output_dir,
        doc_path=args.doc.resolve(),
        cnf_root=cnf_root,
        sizes=args.sizes,
        instances=args.instances,
        generation_seed=args.generation_seed,
        split_seed=args.split_seed,
        train_frac=args.train_frac,
        dev_frac=args.dev_frac,
        missing_files=missing_files,
        manifest_sha256=manifest_sha256,
    )
    print(manifest.groupby(["split", "size"], sort=True).size().to_string())
    print(display_path(manifest_path))
    print(display_path(args.doc.resolve()))


if __name__ == "__main__":
    main()
