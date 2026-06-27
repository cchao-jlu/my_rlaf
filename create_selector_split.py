import argparse
import csv
import os
import random
from glob import glob
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a clean difficulty-matched selector split from 3SAT test-like sizes."
    )
    parser.add_argument("--source-root", default="data/test/3sat")
    parser.add_argument("--output-root", default="data/selector_splits/3sat")
    parser.add_argument("--sizes", default="300,350")
    parser.add_argument("--train-per-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--link-mode", choices=["symlink", "copy"], default="symlink")
    return parser.parse_args()


def ensure_empty_or_create(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            ensure_empty_or_create(child)
            child.rmdir()


def place_file(source: Path, target: Path, link_mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    if link_mode == "copy":
        target.write_bytes(source.read_bytes())
    else:
        rel_source = os.path.relpath(source.resolve(), start=target.parent.resolve())
        target.symlink_to(rel_source)


def main() -> None:
    args = parse_args()
    sizes = [size.strip() for size in args.sizes.split(",") if size.strip()]
    if not sizes:
        raise ValueError("At least one size is required")

    source_root = Path(args.source_root)
    output_root = Path(args.output_root)
    selector_train_root = output_root / "selector_train"
    heldout_test_root = output_root / "heldout_test"
    ensure_empty_or_create(selector_train_root)
    ensure_empty_or_create(heldout_test_root)

    rng = random.Random(args.seed)
    rows = []
    for size in sizes:
        files = sorted(Path(path) for path in glob(str(source_root / size / "*.cnf")))
        if len(files) <= args.train_per_size:
            raise ValueError(
                f"Need more than {args.train_per_size} files for size {size}, found {len(files)}"
            )
        shuffled = list(files)
        rng.shuffle(shuffled)
        train_set = set(shuffled[: args.train_per_size])

        for source in files:
            split = "selector_train" if source in train_set else "heldout_test"
            target = output_root / split / size / source.name
            place_file(source, target, args.link_mode)
            rows.append(
                {
                    "size": size,
                    "split": split,
                    "source_file": str(source),
                    "split_file": str(target),
                }
            )

    manifest = output_root / "split_manifest.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["size", "split", "source_file", "split_file"])
        writer.writeheader()
        writer.writerows(rows)

    for size in sizes:
        train_count = sum(1 for row in rows if row["size"] == size and row["split"] == "selector_train")
        heldout_count = sum(1 for row in rows if row["size"] == size and row["split"] == "heldout_test")
        print(f"{size}: selector_train={train_count}, heldout_test={heldout_count}")
    print(f"wrote manifest: {manifest}")


if __name__ == "__main__":
    main()
