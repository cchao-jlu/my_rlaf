from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(sys.executable)


def run(command: list[str], dry_run: bool) -> None:
    print(" ".join(command), flush=True)
    if dry_run:
        return
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize the large residual gate after raw solver artifacts are complete."
    )
    parser.add_argument("--sizes", type=int, nargs="+", default=[410, 425, 440])
    parser.add_argument("--instances", type=int, default=300)
    parser.add_argument("--seed", type=int, default=2041)
    parser.add_argument("--split-seed", type=int, default=1729)
    parser.add_argument("--limit", type=float, default=60.0)
    parser.add_argument("--timeout", type=float, default=65.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/benchmark_transition_band_residual_large/3sat")
    parser.add_argument("--cnf-root", type=Path, default=ROOT / "data/benchmark_transition_band_residual_large")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs/analysis/benchmark_transition_band_residual_large")
    parser.add_argument(
        "--exclude-csv",
        type=Path,
        default=ROOT / "runs/analysis/benchmark_march_expanded_sample_portfolio_oracle/both_unknown_subset.csv",
    )
    parser.add_argument("--exclude-cnf-root", type=Path, default=ROOT / "data/benchmark_transition_band_expanded")
    parser.add_argument("--skip-training-ready", action="store_true")
    parser.add_argument("--skip-paper-table", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    raw_dir = out_dir / "raw"
    candidate_dir = out_dir / f"candidate_split_seed{args.split_seed}"
    split_dir = out_dir / f"residual_split_seed{args.split_seed}"

    size_args = [str(size) for size in args.sizes]
    run(
        [
            str(PYTHON),
            "run_transition_band_expanded_gate.py",
            "--sizes",
            *size_args,
            "--instances",
            str(args.instances),
            "--seed",
            str(args.seed),
            "--limit",
            f"{args.limit:g}",
            "--timeout",
            f"{args.timeout:g}",
            "--workers",
            str(args.workers),
            "--data-root",
            str(args.data_root),
            "--out-dir",
            str(out_dir),
            "--raw-dir",
            str(raw_dir),
            "--doc-path",
            str(ROOT / "docs/benchmark_transition_band_residual_large_gate.md"),
            "--skip-solvers",
        ],
        dry_run=args.dry_run,
    )
    run(
        [
            str(PYTHON),
            "build_residual_split_manifest.py",
            "--input",
            str(out_dir / "both_unknown_subset.csv"),
            "--cnf-root",
            str(args.cnf_root),
            "--exclude-csv",
            str(args.exclude_csv),
            "--exclude-cnf-root",
            str(args.exclude_cnf_root),
            "--candidate-manifest",
            str(candidate_dir / "manifest.csv"),
            "--output-dir",
            str(split_dir),
            "--doc",
            str(ROOT / f"docs/benchmark_transition_band_residual_large_residual_split_seed{args.split_seed}.md"),
            "--seed",
            str(args.split_seed),
            "--train-frac",
            "0.5",
            "--dev-frac",
            "0.25",
            "--materialize",
            "symlink",
        ],
        dry_run=args.dry_run,
    )
    run(
        [
            str(PYTHON),
            "audit_residual_portfolio_protocol.py",
            "--strong-combined",
            str(out_dir / "combined.csv"),
            "--candidate-manifest",
            str(candidate_dir / "manifest.csv"),
            "--candidate-metadata",
            str(candidate_dir / "candidate_split_metadata.json"),
            "--expected-candidate-total",
            str(len(args.sizes) * args.instances),
            "--expected-generation-seed",
            str(args.seed),
            "--expected-split-seed",
            str(args.split_seed),
            "--require-candidate-files",
            "--split-manifest",
            str(split_dir / "manifest.csv"),
            "--split-metadata",
            str(split_dir / "split_metadata.json"),
            "--split-input",
            str(out_dir / "both_unknown_subset.csv"),
            "--exclude-csv",
            str(args.exclude_csv),
            "--exclude-cnf-root",
            str(args.exclude_cnf_root),
            "--output-csv",
            str(out_dir / f"protocol_audit_split_seed{args.split_seed}.csv"),
            "--doc",
            str(ROOT / f"docs/benchmark_transition_band_residual_large_protocol_audit_split_seed{args.split_seed}.md"),
            "--allow-incomplete",
        ],
        dry_run=args.dry_run,
    )
    if not args.skip_paper_table:
        run(
            [
                str(PYTHON),
                "summarize_residual_portfolio_paper_table.py",
                "--strong-combined",
                str(out_dir / "combined.csv"),
                "--candidate-manifest",
                str(candidate_dir / "manifest.csv"),
                "--candidate-metadata",
                str(candidate_dir / "candidate_split_metadata.json"),
                "--split-manifest",
                str(split_dir / "manifest.csv"),
                "--split-metadata",
                str(split_dir / "split_metadata.json"),
                "--output-csv",
                str(out_dir / f"residual_portfolio_paper_table_split_seed{args.split_seed}.csv"),
                "--doc",
                str(ROOT / f"docs/benchmark_transition_band_residual_large_paper_table_split_seed{args.split_seed}.md"),
            ],
            dry_run=args.dry_run,
        )
    if not args.skip_training_ready:
        run(
            [
                str(PYTHON),
                "audit_residual_training_ready.py",
                "--split-manifest",
                str(split_dir / "manifest.csv"),
                "--train-glob",
                str(split_dir / "cnf/residual_train/*/*.cnf"),
                "--dev-glob",
                str(split_dir / "cnf/residual_dev/*/*.cnf"),
                "--checkpoint",
                str(ROOT / "runs/GNN_March_3SAT/best.pt"),
                "--output-csv",
                str(out_dir / f"residual_training_ready_audit_seed{args.split_seed}.csv"),
                "--doc",
                str(ROOT / f"docs/benchmark_transition_band_residual_large_training_ready_audit_seed{args.split_seed}.md"),
            ],
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
