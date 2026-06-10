from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULTS = [
    "--manifest",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_manifest_labeled.csv"),
    "--per-instance-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_per_instance.csv"),
    "--phases-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_phases.csv"),
    "--by-family-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_by_family.csv"),
    "--by-base-instance-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_by_base_instance.csv"),
    "--attribution-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_attribution.csv"),
    "--attribution-by-base-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_attribution_by_base.csv"),
    "--loss-diagnostics-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_guided_loss_diagnostics.csv"),
    "--timeout-correctness-csv",
    str(ROOT / "runs/analysis/symmetry_runtime_benchmark_v2_timeout_correctness.csv"),
    "--doc",
    str(ROOT / "docs/symmetry_runtime_benchmark_v2.md"),
    "--repeats",
    "3",
    "--final-cpu-lim",
    "5",
    "--warmup-cpu-lim",
    "5",
    "--warmup-conflicts",
    "20",
]


def main() -> None:
    if "--weighted-no-pre" in sys.argv[1:]:
        raise SystemExit(
            "runtime_benchmark_v2 keeps solver_path_role=patched_pretrue_main. "
            "Use run_symmetry_solver_protocol_preflight.py --weighted-no-pre only for diagnostic appendix runs."
        )
    from scripts.symmetry import run_symmetry_solver_protocol_preflight as preflight

    sys.argv = [sys.argv[0], *DEFAULTS, *sys.argv[1:]]
    preflight.main()


if __name__ == "__main__":
    main()
