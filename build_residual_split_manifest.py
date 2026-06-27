from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "runs/analysis/benchmark_transition_band_expanded/both_unknown_subset.csv"
DEFAULT_OUTPUT_DIR = ROOT / "runs/analysis/residual_split_manifest"
DEFAULT_DOC = ROOT / "docs/residual_split_manifest.md"


def stable_row_id(row: pd.Series) -> str:
    return f"{row['family']}:{int(row['size'])}:{row['file_key']}"


def row_cnf_path(row: pd.Series, cnf_root: Path | None) -> Path | None:
    if "cnf_path" in row and pd.notna(row["cnf_path"]):
        return Path(str(row["cnf_path"]))
    if "file" in row and pd.notna(row["file"]):
        return Path(str(row["file"]))
    if cnf_root is None:
        return None
    return cnf_root / str(row["family"]) / str(int(row["size"])) / str(row["file_key"])


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def assign_splits(frame: pd.DataFrame, train_frac: float, dev_frac: float, seed: int) -> pd.DataFrame:
    if not 0.0 <= train_frac <= 1.0 or not 0.0 <= dev_frac <= 1.0:
        raise ValueError("Fractions must be in [0, 1].")
    if train_frac + dev_frac >= 1.0:
        raise ValueError("train_frac + dev_frac must leave held-out residual instances.")

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
            split_for[idx] = "residual_train"
        for idx in indices[train_n : train_n + dev_n]:
            split_for[idx] = "residual_dev"
        for idx in indices[train_n + dev_n :]:
            split_for[idx] = "residual_heldout"
        for idx in group.index:
            row = group.loc[idx].to_dict()
            row["split"] = split_for[idx]
            row["row_id"] = stable_row_id(group.loc[idx])
            rows.append(row)
    result = pd.DataFrame(rows)
    return result.sort_values(["split", "size", "file_key"]).reset_index(drop=True)


def project_candidate_splits(frame: pd.DataFrame, candidate_manifest_csv: Path) -> pd.DataFrame:
    candidates = pd.read_csv(candidate_manifest_csv)
    required = {"family", "size", "file_key", "split"}
    missing = required - set(candidates.columns)
    if missing:
        raise ValueError(f"Candidate manifest is missing columns: {sorted(missing)}")
    mapping = {}
    for _, row in candidates.iterrows():
        split = str(row["split"])
        if not split.startswith("candidate_"):
            raise ValueError(f"Unexpected candidate split name: {split}")
        mapping[stable_row_id(row)] = split.replace("candidate_", "residual_", 1)

    rows = []
    missing_ids = []
    for _, row in frame.iterrows():
        row_id = stable_row_id(row)
        split = mapping.get(row_id)
        if split is None:
            missing_ids.append(row_id)
            continue
        out = row.to_dict()
        out["split"] = split
        out["row_id"] = row_id
        rows.append(out)
    if missing_ids:
        raise ValueError(f"Residual rows missing from candidate manifest: {missing_ids[:10]}")
    return pd.DataFrame(rows).sort_values(["split", "size", "file_key"]).reset_index(drop=True)


def add_cnf_paths(frame: pd.DataFrame, cnf_root: Path) -> pd.DataFrame:
    frame = frame.copy()
    paths = []
    for _, row in frame.iterrows():
        paths.append(str(cnf_root / str(row["family"]) / str(int(row["size"])) / str(row["file_key"])))
    frame["cnf_path"] = paths
    return frame


def filter_excluded(
    frame: pd.DataFrame,
    exclude_csv: Path | None,
    input_cnf_root: Path | None,
    exclude_cnf_root: Path | None,
) -> tuple[pd.DataFrame, int, str]:
    if exclude_csv is None:
        return frame, 0, "none"
    excluded = pd.read_csv(exclude_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(excluded.columns)
    if missing:
        raise ValueError(f"Exclude CSV is missing columns: {sorted(missing)}")

    input_hashes: dict[int, str | None] = {}
    excluded_hashes: set[str] = set()
    can_hash = True
    for _, row in excluded.iterrows():
        path = row_cnf_path(row, exclude_cnf_root)
        if path is None or not path.exists():
            can_hash = False
            break
        excluded_hashes.add(file_sha256(path))
    if can_hash:
        keep = []
        for idx, row in frame.iterrows():
            path = row_cnf_path(row, input_cnf_root)
            if path is None or not path.exists():
                can_hash = False
                break
            digest = file_sha256(path)
            input_hashes[idx] = digest
            keep.append(digest not in excluded_hashes)
        if can_hash:
            keep_series = pd.Series(keep, index=frame.index)
            return frame.loc[keep_series].reset_index(drop=True), int((~keep_series).sum()), "cnf_sha256"

    excluded_ids = {stable_row_id(row) for _, row in excluded.iterrows()}
    keep = [stable_row_id(row) not in excluded_ids for _, row in frame.iterrows()]
    keep_series = pd.Series(keep, index=frame.index)
    return frame.loc[keep_series].reset_index(drop=True), int((~keep_series).sum()), "row_id_fallback"


def materialize_split_files(manifest: pd.DataFrame, output_dir: Path, mode: str) -> None:
    if mode == "none":
        return
    for _, row in manifest.iterrows():
        source = Path(row["cnf_path"])
        if not source.exists():
            raise FileNotFoundError(source)
        target = output_dir / "cnf" / str(row["split"]) / str(int(row["size"])) / str(row["file_key"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            target.unlink()
        if mode == "copy":
            shutil.copy2(source, target)
        elif mode == "symlink":
            rel_source = os.path.relpath(source.resolve(), start=target.parent.resolve())
            target.symlink_to(rel_source)
        else:
            raise ValueError(f"Unknown materialize mode: {mode}")


def write_doc(
    manifest: pd.DataFrame,
    input_csv: Path,
    cnf_root: Path,
    output_dir: Path,
    seed: int,
    train_frac: float,
    dev_frac: float,
    input_sha256: str,
    exclude_csv: Path | None,
    excluded_count: int,
    exclude_mode: str,
    materialize: str,
    candidate_manifest_csv: Path | None,
    candidate_manifest_sha256: str | None,
    split_source: str,
    doc_path: Path,
) -> None:
    summary = (
        manifest.groupby(["split", "size"], sort=True)
        .size()
        .reset_index(name="instances")
    )
    split_totals = manifest.groupby("split", sort=True).size().reset_index(name="instances")

    def table(frame: pd.DataFrame) -> list[str]:
        columns = list(frame.columns)
        lines = [
            "| " + " | ".join(columns) + " |",
            "| " + " | ".join("---" for _ in columns) + " |",
        ]
        for _, row in frame.iterrows():
            lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
        return lines

    lines = [
        "# Residual Split Manifest",
        "",
        "Scope: immutable train/dev/held-out split for March/CaDiCaL both-unknown",
        "transition-band residual instances. This split is created before selector",
        "thresholds, adaptive budget rules, or non-neural schedules are tuned.",
        "",
        "## Source",
        "",
        f"- input CSV: `{display_path(input_csv)}`",
        f"- input sha256: `{input_sha256}`",
        f"- CNF root: `{display_path(cnf_root)}`",
        f"- excluded CSV: `{display_path(exclude_csv) if exclude_csv else 'none'}`",
        f"- excluded rows: `{excluded_count}`",
        f"- exclude mode: `{exclude_mode}`",
        f"- split seed: `{seed}`",
        f"- train fraction: `{train_frac}`",
        f"- dev fraction: `{dev_frac}`",
        f"- split source: `{split_source}`",
        f"- candidate manifest: `{display_path(candidate_manifest_csv) if candidate_manifest_csv else 'none'}`",
        f"- candidate manifest sha256: `{candidate_manifest_sha256 or 'none'}`",
        f"- materialized CNFs: `{materialize}`",
        "",
        "## Split Totals",
        "",
        *table(split_totals),
        "",
        "## Split By Size",
        "",
        *table(summary),
        "",
        "## Artifacts",
        "",
        "```text",
        display_path(output_dir / "manifest.csv"),
        display_path(output_dir / "residual_train.csv"),
        display_path(output_dir / "residual_dev.csv"),
        display_path(output_dir / "residual_heldout.csv"),
        display_path(output_dir / "cnf"),
        "```",
    ]
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_metadata(
    manifest: pd.DataFrame,
    input_csv: Path,
    cnf_root: Path,
    output_dir: Path,
    seed: int,
    train_frac: float,
    dev_frac: float,
    input_sha256: str,
    exclude_csv: Path | None,
    exclude_sha256: str | None,
    excluded_count: int,
    exclude_mode: str,
    materialize: str,
    candidate_manifest_csv: Path | None,
    candidate_manifest_sha256: str | None,
    split_source: str,
) -> None:
    split_counts = {
        str(split): int(count)
        for split, count in manifest.groupby("split", sort=True).size().items()
    }
    size_split_counts = {
        f"{split}:{int(size)}": int(count)
        for (split, size), count in manifest.groupby(["split", "size"], sort=True).size().items()
    }
    metadata = {
        "input_csv": display_path(input_csv),
        "input_sha256": input_sha256,
        "cnf_root": display_path(cnf_root),
        "exclude_csv": display_path(exclude_csv) if exclude_csv else None,
        "exclude_sha256": exclude_sha256,
        "excluded_count": int(excluded_count),
        "exclude_mode": exclude_mode,
        "seed": int(seed),
        "train_frac": float(train_frac),
        "dev_frac": float(dev_frac),
        "split_source": split_source,
        "candidate_manifest_csv": display_path(candidate_manifest_csv) if candidate_manifest_csv else None,
        "candidate_manifest_sha256": candidate_manifest_sha256,
        "materialize": materialize,
        "manifest_rows": int(len(manifest)),
        "split_counts": split_counts,
        "size_split_counts": size_split_counts,
    }
    (output_dir / "split_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build immutable residual train/dev/held-out split manifests.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--cnf-root", type=Path, default=ROOT / "data/benchmark_transition_band_expanded")
    parser.add_argument("--exclude-csv", type=Path, default=None)
    parser.add_argument(
        "--exclude-cnf-root",
        type=Path,
        default=None,
        help="CNF root for --exclude-csv when it does not contain absolute file paths.",
    )
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--train-frac", type=float, default=0.5)
    parser.add_argument("--dev-frac", type=float, default=0.25)
    parser.add_argument(
        "--candidate-manifest",
        type=Path,
        default=None,
        help="Optional full-candidate split manifest; residual split is projected from it.",
    )
    parser.add_argument("--materialize", choices=["none", "symlink", "copy"], default="none")
    args = parser.parse_args()

    input_csv = args.input.resolve()
    if not input_csv.exists():
        raise FileNotFoundError(input_csv)
    frame = pd.read_csv(input_csv)
    required = {"family", "size", "file_key"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Input is missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Input residual CSV is empty.")

    cnf_root = args.cnf_root.resolve()
    exclude_csv = args.exclude_csv.resolve() if args.exclude_csv else None
    exclude_cnf_root = args.exclude_cnf_root.resolve() if args.exclude_cnf_root else None
    frame, excluded_count, exclude_mode = filter_excluded(
        frame,
        exclude_csv,
        input_cnf_root=cnf_root,
        exclude_cnf_root=exclude_cnf_root,
    )
    if frame.empty:
        raise ValueError("All residual rows were excluded.")

    candidate_manifest = args.candidate_manifest.resolve() if args.candidate_manifest else None
    candidate_hash = file_sha256(candidate_manifest) if candidate_manifest and candidate_manifest.exists() else None
    if candidate_manifest is not None:
        manifest = project_candidate_splits(frame, candidate_manifest_csv=candidate_manifest)
        split_source = "candidate_manifest"
    else:
        manifest = assign_splits(frame, train_frac=args.train_frac, dev_frac=args.dev_frac, seed=args.seed)
        split_source = "residual_pool_random"
    manifest = add_cnf_paths(manifest, cnf_root=cnf_root)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output_dir / "manifest.csv", index=False)
    for split, group in manifest.groupby("split", sort=True):
        group.to_csv(output_dir / f"{split}.csv", index=False)
    materialize_split_files(manifest, output_dir=output_dir, mode=args.materialize)

    input_hash = file_sha256(input_csv)
    exclude_hash = file_sha256(exclude_csv) if exclude_csv and exclude_csv.exists() else None
    write_metadata(
        manifest=manifest,
        input_csv=input_csv,
        cnf_root=cnf_root,
        output_dir=output_dir,
        seed=args.seed,
        train_frac=args.train_frac,
        dev_frac=args.dev_frac,
        input_sha256=input_hash,
        exclude_csv=exclude_csv,
        exclude_sha256=exclude_hash,
        excluded_count=excluded_count,
        exclude_mode=exclude_mode,
        materialize=args.materialize,
        candidate_manifest_csv=candidate_manifest,
        candidate_manifest_sha256=candidate_hash,
        split_source=split_source,
    )
    write_doc(
        manifest=manifest,
        input_csv=input_csv,
        cnf_root=cnf_root,
        output_dir=output_dir,
        seed=args.seed,
        train_frac=args.train_frac,
        dev_frac=args.dev_frac,
        input_sha256=input_hash,
        exclude_csv=exclude_csv,
        excluded_count=excluded_count,
        exclude_mode=exclude_mode,
        materialize=args.materialize,
        candidate_manifest_csv=candidate_manifest,
        candidate_manifest_sha256=candidate_hash,
        split_source=split_source,
        doc_path=args.doc.resolve(),
    )

    print(manifest.groupby(["split", "size"], sort=True).size().to_string())
    print(display_path(output_dir / "manifest.csv"))
    print(display_path(args.doc.resolve()))


if __name__ == "__main__":
    main()
