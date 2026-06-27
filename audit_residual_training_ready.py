from __future__ import annotations

import argparse
from glob import glob
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check(condition: bool, name: str, detail: str) -> dict[str, str]:
    return {"check": name, "status": "pass" if condition else "fail", "detail": detail}


def audit_manifest(manifest_path: Path) -> tuple[list[dict[str, str]], pd.DataFrame]:
    if not manifest_path.exists():
        return [check(False, "split_manifest_exists", f"missing: {manifest_path}")], pd.DataFrame()
    manifest = pd.read_csv(manifest_path)
    rows = [check(True, "split_manifest_exists", display_path(manifest_path))]
    required = {"family", "size", "file_key", "split", "cnf_path"}
    missing = required - set(manifest.columns)
    rows.append(check(not missing, "split_manifest_has_required_columns", f"missing={sorted(missing)}"))
    if missing:
        return rows, manifest
    split_counts = {str(split): int(count) for split, count in manifest.groupby("split", sort=True).size().items()}
    rows.append(
        check(
            split_counts.get("residual_train", 0) > 0,
            "residual_train_nonempty",
            f"count={split_counts.get('residual_train', 0)}",
        )
    )
    rows.append(
        check(
            split_counts.get("residual_dev", 0) > 0,
            "residual_dev_nonempty",
            f"count={split_counts.get('residual_dev', 0)}",
        )
    )
    missing_files = sum(1 for path in manifest["cnf_path"].astype(str) if not Path(path).exists())
    rows.append(check(missing_files == 0, "manifest_cnf_paths_exist", f"missing_files={missing_files}"))
    return rows, manifest


def audit_glob(name: str, pattern: str, expected_min: int) -> list[dict[str, str]]:
    files = sorted(glob(pattern))
    broken = sum(1 for file in files if not Path(file).exists())
    return [
        check(len(files) >= expected_min, f"{name}_glob_nonempty", f"count={len(files)} pattern={pattern}"),
        check(broken == 0, f"{name}_glob_paths_exist", f"broken_paths={broken}"),
    ]


def audit_checkpoint(path: Path) -> list[dict[str, str]]:
    return [check(path.exists(), "source_checkpoint_exists", display_path(path) if path.exists() else f"missing: {path}")]


def write_doc(rows: list[dict[str, str]], doc_path: Path) -> None:
    lines = [
        "# Residual Training Readiness Audit",
        "",
        "| check | status | detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {row['detail']} |")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit residual-targeted training inputs before launching GRPO.")
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--train-glob", required=True)
    parser.add_argument("--dev-glob", required=True)
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "runs/GNN_March_3SAT/best.pt")
    parser.add_argument("--output-csv", type=Path, default=ROOT / "runs/analysis/residual_training_ready_audit.csv")
    parser.add_argument("--doc", type=Path, default=ROOT / "docs/residual_training_ready_audit.md")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    rows, manifest = audit_manifest(args.split_manifest.resolve())
    expected_train = 1
    expected_dev = 1
    if not manifest.empty and "split" in manifest.columns:
        counts = manifest.groupby("split", sort=True).size()
        expected_train = int(counts.get("residual_train", 1))
        expected_dev = int(counts.get("residual_dev", 1))
    rows.extend(audit_glob("train", args.train_glob, expected_train))
    rows.extend(audit_glob("dev", args.dev_glob, expected_dev))
    rows.extend(audit_checkpoint(args.checkpoint.resolve()))

    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_csv, index=False)
    write_doc(rows, args.doc.resolve())
    print(pd.DataFrame(rows).to_string(index=False))
    print(display_path(output_csv))
    print(display_path(args.doc.resolve()))
    if not args.allow_incomplete and any(row["status"] != "pass" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
