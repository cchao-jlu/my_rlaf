from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


KEY_COLUMNS = ["family", "size", "file_key"]


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def load_oracle(path: Path, tag: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(KEY_COLUMNS + ["solved_any"]) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    out = frame.copy()
    out["tag"] = tag
    out["family"] = out["family"].astype(str)
    out["size"] = pd.to_numeric(out["size"], errors="raise").astype(int)
    out["file_key"] = out["file_key"].astype(str)
    out["solved_any"] = out["solved_any"].map(parse_bool)
    if "solved_samples" not in out.columns:
        out["solved_samples"] = out["solved_any"].astype(int)
    out["solved_samples"] = pd.to_numeric(out["solved_samples"], errors="coerce").fillna(0).astype(int)
    if "best_time" not in out.columns:
        out["best_time"] = float("nan")
    out["best_time"] = pd.to_numeric(out["best_time"], errors="coerce")
    return out[["tag", *KEY_COLUMNS, "solved_any", "solved_samples", "best_time"]]


def infer_tag(path: Path) -> str:
    parent = path.parent.name
    prefix = "benchmark_march_expanded_sample_portfolio_oracle_"
    if parent.startswith(prefix):
        return parent[len(prefix) :]
    return parent


def summarize(paths: list[Path], tags: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if len(paths) != len(tags):
        raise ValueError("paths and tags must have the same length.")
    frames = [load_oracle(path, tag) for path, tag in zip(paths, tags)]
    if not frames:
        raise ValueError("At least one oracle CSV is required.")
    all_rows = pd.concat(frames, ignore_index=True)
    duplicates = all_rows.duplicated(["tag", *KEY_COLUMNS], keep=False)
    if duplicates.any():
        shown = all_rows.loc[duplicates, ["tag", *KEY_COLUMNS]].head(5).to_dict(orient="records")
        raise ValueError(f"Duplicate oracle keys within tag: {shown}")
    union = (
        all_rows.groupby(KEY_COLUMNS, as_index=False)
        .agg(
            oracle_solved_any=("solved_any", "any"),
            total_solved_samples=("solved_samples", "sum"),
            min_best_time=("best_time", "min"),
        )
        .sort_values(KEY_COLUMNS)
    )
    per_tag = (
        all_rows.groupby("tag", as_index=False)
        .agg(total=("file_key", "count"), oracle_solved=("solved_any", "sum"), solved_samples=("solved_samples", "sum"))
        .sort_values(["oracle_solved", "tag"], ascending=[False, True])
    )
    by_size = (
        all_rows.groupby(["tag", "size"], as_index=False)
        .agg(total=("file_key", "count"), oracle_solved=("solved_any", "sum"), solved_samples=("solved_samples", "sum"))
        .sort_values(["tag", "size"])
    )
    return union, per_tag, by_size


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
                values.append(f"{value:.4g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def write_doc(path: Path, union: pd.DataFrame, per_tag: pd.DataFrame, by_size: pd.DataFrame, sources: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    solved = union[union["oracle_solved_any"]].copy()
    lines = [
        "# Residual Oracle Union Diagnostic",
        "",
        "This diagnostic unions oracle coverage across checkpoint-specific all-49",
        "sample-portfolio diagnostics. It is not a deployable selector result.",
        "",
        f"- checkpoint diagnostics: `{len(per_tag)}`",
        f"- residual instances: `{len(union)}`",
        f"- union oracle solved: `{int(union['oracle_solved_any'].sum())}`",
        "",
        "## Sources",
        "",
        *markdown_table(sources, ["tag", "path"]),
        "",
        "## Per Checkpoint",
        "",
        *markdown_table(per_tag, ["tag", "total", "oracle_solved", "solved_samples"]),
        "",
        "## By Size",
        "",
        *markdown_table(by_size, ["tag", "size", "total", "oracle_solved", "solved_samples"]),
        "",
        "## Union Positives",
        "",
        *markdown_table(solved, ["family", "size", "file_key", "total_solved_samples", "min_best_time"]),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize union oracle coverage across residual checkpoint gates.")
    parser.add_argument("--oracle-csv", type=Path, nargs="+", required=True)
    parser.add_argument("--tag", nargs="*", default=None)
    parser.add_argument("--output-union-csv", type=Path, required=True)
    parser.add_argument("--output-per-tag-csv", type=Path, required=True)
    parser.add_argument("--output-by-size-csv", type=Path, required=True)
    parser.add_argument("--doc", type=Path, required=True)
    parser.add_argument("--expected-total", type=int, default=0)
    parser.add_argument("--fail-max", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [path.resolve() for path in args.oracle_csv]
    tags = list(args.tag) if args.tag else [infer_tag(path) for path in paths]
    union, per_tag, by_size = summarize(paths, tags)
    if args.expected_total > 0 and len(union) != int(args.expected_total):
        raise ValueError(f"Union denominator mismatch: observed={len(union)} expected={args.expected_total}")
    args.output_union_csv.parent.mkdir(parents=True, exist_ok=True)
    union.to_csv(args.output_union_csv, index=False)
    args.output_per_tag_csv.parent.mkdir(parents=True, exist_ok=True)
    per_tag.to_csv(args.output_per_tag_csv, index=False)
    args.output_by_size_csv.parent.mkdir(parents=True, exist_ok=True)
    by_size.to_csv(args.output_by_size_csv, index=False)
    sources = pd.DataFrame({"tag": tags, "path": [str(path) for path in paths]})
    write_doc(args.doc, union=union, per_tag=per_tag, by_size=by_size, sources=sources)
    solved = int(union["oracle_solved_any"].sum())
    decision = "sparse" if solved <= int(args.fail_max) else "nontrivial"
    print(f"union_solved={solved} total={len(union)} decision={decision}", flush=True)


if __name__ == "__main__":
    main()
