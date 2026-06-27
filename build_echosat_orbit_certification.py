from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "runs/analysis/symmetry_grpo_speedup_full_manifest.csv"
DEFAULT_OUT = ROOT / "runs/analysis/echosat_orbit_certification.csv"
DEFAULT_DOC = ROOT / "docs/echosat_orbit_certification.md"


def resolve(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def read_json(path: str | Path) -> Any:
    path = resolve(path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def confidence_for(row: pd.Series, orbit_size: int) -> float:
    control_type = str(row.get("control_type", ""))
    strength = str(row.get("symmetry_strength", ""))
    if control_type == "non_symmetric_control" or strength == "none":
        return 0.0
    if orbit_size < 2:
        return 0.0
    if strength == "strong":
        return 1.0
    if strength == "weak":
        return 0.6
    if strength == "pseudo":
        return 0.3
    return 0.5


def structure_type_for(row: pd.Series, orbit_id: str) -> str:
    family = str(row.get("family", ""))
    if family in {"php", "php_exit_single", "php_exit_all"}:
        return "row_column"
    if family == "subset_cardinality":
        return "bandwidth_cardinality"
    if family in {"dominating_set_hex", "vertex_cover_torus", "even_colouring"}:
        return "grid_or_torus"
    if family == "complete_coloring":
        return "graph_coloring"
    if family == "tseitin_complete":
        return "complete_graph_parity"
    if family == "random_3sat_control":
        return "none"
    return "unknown"


def rows_for_instance(row: pd.Series) -> list[dict[str, Any]]:
    orbits_path = str(row.get("orbits_path", "") or "")
    orbit_map = read_json(orbits_path) if orbits_path else None
    base = str(row.get("base_instance_id", row.get("instance_id", "")))
    variant = str(row.get("variant", "base"))
    common = {
        "family": str(row.get("family", "")),
        "instance_id": str(row.get("instance_id", "")),
        "base_instance_id": base,
        "variant": variant,
        "cnf_path": str(resolve(str(row.get("cnf_path", ""))).resolve()) if str(row.get("cnf_path", "")) else "",
        "orbits_path": str(resolve(orbits_path).resolve()) if orbits_path else "",
        "metadata_path": str(resolve(str(row.get("metadata_path", ""))).resolve()) if str(row.get("metadata_path", "")) else "",
        "control_type": str(row.get("control_type", "")),
        "symmetry_strength": str(row.get("symmetry_strength", "")),
        "scale": str(row.get("scale", "")),
        "benchmark_role": str(row.get("benchmark_role", "")),
        "permutation_variant": bool(str(row.get("permutation_variant", "False")).lower() in {"true", "1", "yes"}),
    }
    if not isinstance(orbit_map, dict) or not orbit_map:
        return [
            {
                **common,
                "orbit_id": "missing_orbit_table",
                "vars": "",
                "orbit_size": 0,
                "structure_type": "none" if common["control_type"] == "non_symmetric_control" else "unknown",
                "certification_source": "missing",
                "orbit_confidence": 0.0,
                "valid_for_training": False,
                "needs_refinement": common["control_type"] != "non_symmetric_control",
                "notes": "missing or empty orbits_path",
            }
        ]

    grouped: dict[str, list[int]] = {}
    for raw_var, raw_orbit in orbit_map.items():
        try:
            var = int(raw_var)
        except (TypeError, ValueError):
            continue
        grouped.setdefault(str(raw_orbit), []).append(var)

    rows = []
    for orbit_id, variables in sorted(grouped.items(), key=lambda item: (item[0], min(item[1]) if item[1] else 0)):
        variables = sorted(set(int(var) for var in variables))
        conf = confidence_for(row, len(variables))
        valid = conf >= 0.5 and len(variables) >= 2 and common["control_type"] != "non_symmetric_control"
        rows.append(
            {
                **common,
                "orbit_id": orbit_id,
                "vars": " ".join(map(str, variables)),
                "orbit_size": len(variables),
                "structure_type": structure_type_for(row, orbit_id),
                "certification_source": "generator_or_manual_orbit_json",
                "orbit_confidence": conf,
                "valid_for_training": bool(valid),
                "needs_refinement": bool(conf < 0.5 and common["control_type"] != "non_symmetric_control"),
                "notes": "",
            }
        )
    return rows


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> list[str]:
    if frame.empty:
        return ["_empty_"]
    view = frame.head(max_rows).copy()
    columns = list(view.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return lines


def write_doc(path: Path, rows: pd.DataFrame, out_csv: Path, manifest: Path) -> None:
    summary = (
        rows.groupby(["family", "control_type", "symmetry_strength"], sort=True)
        .agg(
            instances=("instance_id", "nunique"),
            bases=("base_instance_id", "nunique"),
            orbit_rows=("orbit_id", "count"),
            valid_orbit_rows=("valid_for_training", lambda values: int(pd.Series(values).astype(bool).sum())),
            valid_orbit_vars=("orbit_size", lambda values: int(rows.loc[values.index, "orbit_size"][rows.loc[values.index, "valid_for_training"].astype(bool)].sum())),
            mean_orbit_confidence=("orbit_confidence", "mean"),
            needs_refinement_rows=("needs_refinement", lambda values: int(pd.Series(values).astype(bool).sum())),
        )
        .reset_index()
    )
    control = rows[rows["control_type"].astype(str).eq("non_symmetric_control")].copy()
    control_high = int((pd.to_numeric(control["orbit_confidence"], errors="coerce").fillna(0.0) > 0.0).sum()) if not control.empty else 0
    lines = [
        "# EchoSAT Orbit Certification",
        "",
        "This expands manifest orbit JSON files into an auditable orbit table for EchoSAT training boundaries. It is not a runtime benchmark and does not train a model.",
        "",
        "## Inputs",
        "",
        f"- manifest: `{manifest}`",
        f"- output CSV: `{out_csv}`",
        "",
        "## Sanity",
        "",
        f"- orbit rows: `{len(rows)}`",
        f"- base instances: `{rows['base_instance_id'].nunique() if not rows.empty else 0}`",
        f"- random-control rows with nonzero confidence: `{control_high}`",
        "",
        "## Family Summary",
        "",
        *markdown_table(summary, max_rows=80),
        "",
        "## Usage",
        "",
        "High-confidence rows with `valid_for_training=True` are eligible for symmetry-positive reward. Random controls keep `orbit_confidence=0` and must not enter the symmetry-positive denominator.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build EchoSAT orbit certification table from symmetry manifests.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = resolve(args.manifest)
    manifest = pd.read_csv(manifest_path)
    all_rows: list[dict[str, Any]] = []
    for _, row in manifest.iterrows():
        all_rows.extend(rows_for_instance(row))
    out = pd.DataFrame(all_rows).sort_values(["family", "base_instance_id", "variant", "orbit_id"]).reset_index(drop=True)
    out_path = resolve(args.out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    write_doc(resolve(args.doc), out, out_path.relative_to(ROOT), manifest_path.relative_to(ROOT))
    print(f"wrote {out_path} rows={len(out)} bases={out['base_instance_id'].nunique() if not out.empty else 0}")
    print(f"wrote {resolve(args.doc)}")


if __name__ == "__main__":
    main()
