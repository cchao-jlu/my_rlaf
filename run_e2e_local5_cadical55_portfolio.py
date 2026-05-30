from __future__ import annotations

import argparse
import csv
import math
import os
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import hydra
import pandas as pd
import torch
from omegaconf import OmegaConf
from torch_geometric.loader import DataLoader

from evaluate_guided_solver import (
    DERIVED_SELECTOR_FEATURES,
    EXTERNAL_SELECTOR_FEATURES,
    MODEL_SELECTOR_FEATURES,
    _attach_derived_selector_stage_features,
    _attach_selector_feature_overrides,
    _cnf_id_value,
    _extract_selector_feature_frame,
    _feedback_intervention_conflicts,
    _list_from_cfg,
    _load_local_reopen_candidate_ids,
    _pre_warmup_skip_mask,
    _selector_base_feature_name,
    _stats_selector_feature_frame,
    add_total_time_columns,
)
from run_cadical_default_full400_cpu60 import solve_one as solve_cadical_one
from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy import policy
from src.policy.evaluate import sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.solver import cnf_to_dimacs
from src.solving.state import attach_var_event_state_batch


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "runs/analysis/portfolio_e2e_local5_cadical55"
DOC_PATH = ROOT / "docs/portfolio_e2e_local5_cadical55_eval.md"
CADICAL = ROOT / "solvers/cadical/cadical"
GLUCOSE = ROOT / "solvers/glucose/simp/glucose_static"
WEIGHTED_GLUCOSE = ROOT / "solvers/glucose_weighted/simp/glucose_release"
SOLVED_RESULTS = {"SATISFIABLE", "UNSATISFIABLE"}
EVENT_PREFIX = "c event "
STATS = ["decisions", "conflicts", "propagations", "restarts", "CPU time"]


def parse_glucose_stdout(stdout: str, collect_events: bool = False) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if collect_events and line.startswith(EVENT_PREFIX):
            parts = line[len(EVENT_PREFIX) :].split()
            if len(parts) >= 2:
                stats[f"event_{parts[0]}"] = [float(value) for value in parts[1:]]
            continue
        for stat in STATS:
            if line.startswith(f"c {stat}") or line.startswith(stat):
                _, value_part = line.split(":", 1)
                stats[stat] = float(value_part.strip().split()[0])
            elif line.startswith("s"):
                stats["Result"] = line.split()[1]
    return stats


def solve_graph_with_timeout(
    dataset: DimacsCNFDataset,
    graph,
    solver: str,
    params: dict[str, Any],
    external_timeout: float,
    collect_events: bool = False,
) -> pd.DataFrame:
    cnf_id = _cnf_id_value(graph)
    cnf = dataset.get_cnf(cnf_id)
    var_params_all = graph["var"].var_params.numpy()
    rows = []
    for sample_id in range(var_params_all.shape[1]):
        var_params = var_params_all[:, sample_id]
        dimacs = cnf_to_dimacs(cnf.clauses, var_params=var_params)
        bin_path = WEIGHTED_GLUCOSE if var_params is not None else GLUCOSE
        call = [str(bin_path), "-rnd-seed=1"]
        if collect_events:
            call.append("-collect-events")
        for key, value in params.items():
            call.append(f"-{key}={value}")
        start = time.monotonic()
        with tempfile.TemporaryFile(mode="w+") as handle:
            handle.write(dimacs)
            handle.seek(0)
            try:
                proc = subprocess.run(
                    call,
                    capture_output=True,
                    text=True,
                    stdin=handle,
                    timeout=max(0.001, external_timeout),
                )
                wall = time.monotonic() - start
                stats = parse_glucose_stdout(proc.stdout, collect_events=collect_events)
                stats.setdefault("Result", "INDETERMINATE")
                stats["external_timeout"] = False
            except subprocess.TimeoutExpired as exc:
                wall = time.monotonic() - start
                stdout = exc.stdout or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode(errors="replace")
                stats = parse_glucose_stdout(stdout, collect_events=collect_events)
                stats["Result"] = "TIMEOUT"
                stats["CPU time"] = min(float(external_timeout), float(params.get("cpu-lim", external_timeout)))
                stats["external_timeout"] = True
        stats["wall_time"] = wall
        stats["cnf_id"] = cnf_id
        stats["sample_id"] = sample_id
        stats["file"] = dataset.id_to_file[cnf_id]
        rows.append(stats)
    return pd.DataFrame.from_records(rows)


def remaining(start: float, budget: float) -> float:
    return budget - (time.monotonic() - start)


def params_with_time_cap(params: dict[str, Any], seconds: float) -> dict[str, Any]:
    updated = dict(params)
    updated["cpu-lim"] = max(1, int(math.ceil(max(seconds, 0.001))))
    return updated


class ResidentLocalRunner:
    def __init__(self, first_cap: float):
        self.first_cap = first_cap
        with hydra.initialize_config_dir(config_dir=str(ROOT / "configs"), version_base=None):
            self.cfg = hydra.compose(
                config_name="config_eval_guided_solver_local_reopen_guarded_full400",
                overrides=[
                    "dataset.lazy=True",
                    "loader.batch_size=1",
                    "solver.num_workers=1",
                    "solver.params.cpu-lim=60",
                ],
            )
        OmegaConf.resolve(self.cfg)
        self.model, self.transform, self.model_cfg = load_checkpoint(self.cfg.checkpoint, var_output=True)
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.var_state_dim = getattr(self.model, "var_state_dim", 0)
        if self.var_state_dim <= 0:
            raise ValueError("Local Boundary Correction checkpoint must expose var_state_dim")
        self.event_state_feature_mode = self.cfg.feedback_refinement.event_state_features
        self.use_event_adapter_cache = bool(getattr(self.model, "event_adapter_enabled", False))

    def _dataset_for_file(self, file_path: Path) -> DimacsCNFDataset:
        return DimacsCNFDataset(path=str(file_path), transform=self.transform, lazy=True)

    def warm_model(self, file_path: Path) -> None:
        dataset = self._dataset_for_file(file_path)
        loader = DataLoader(dataset=dataset, batch_size=1, num_workers=0, shuffle=False)
        with torch.no_grad():
            data = next(iter(loader)).to(self.device)
            y_var = self.model(data)
            _ = policy.mode(y_var)

    def run_one(self, file_path: Path) -> dict[str, Any]:
        start = time.monotonic()
        dataset = self._dataset_for_file(file_path)
        loader = DataLoader(dataset=dataset, batch_size=1, num_workers=0, shuffle=False)
        local_reopen_candidate_ids = _load_local_reopen_candidate_ids(
            str(self.cfg.feedback_refinement.local_reopen_candidate_manifest),
            dataset,
        )
        base_params = dict(self.cfg.solver.params)
        try:
            current_loader = loader
            base_data_list = sample_var_params(
                model=self.model,
                loader=current_loader,
                device=self.device,
                use_mode=True,
                num_samples=1,
                scale_sigma=self.model_cfg.scale_sigma,
                add_timing=True,
                cache_var_features=self.use_event_adapter_cache,
            )
            if remaining(start, self.first_cap) <= 0:
                return self._timeout_row(file_path, start, "base_guidance")

            pre_skip_mask, pre_warmup_skip_features = _pre_warmup_skip_mask(
                self.model,
                base_data_list,
                self.cfg.feedback_refinement,
            )
            warmup_data_list = [graph for graph, skip in zip(base_data_list, pre_skip_mask) if not skip]
            skipped_data_list = [graph for graph, skip in zip(base_data_list, pre_skip_mask) if skip]

            refinement_stats_list = []
            refinement_data_lists = []
            pre_warmup_final_data_list = skipped_data_list
            if warmup_data_list:
                refinement_data_lists.append(warmup_data_list)

            selector_feature_names = list(getattr(self.model, "event_adapter_selector_feature_names", []))
            intervention_conflicts = _feedback_intervention_conflicts(
                self.cfg.feedback_refinement,
                selector_feature_names=selector_feature_names,
            )
            base_feature_names = sorted({_selector_base_feature_name(name) for name in selector_feature_names})
            model_feature_names = [name for name in base_feature_names if name in MODEL_SELECTOR_FEATURES]
            refined_by_point = {}
            feature_by_point = {}
            refined_graphs = []
            if warmup_data_list:
                for point in intervention_conflicts:
                    time_left = remaining(start, self.first_cap)
                    if time_left <= 0:
                        return self._timeout_row(file_path, start, f"warmup_c{point}")
                    point_params = apply_rollout_budget(
                        params_with_time_cap(base_params, time_left),
                        budget_type=self.cfg.feedback_refinement.rollout_budget_type,
                        cpu_lim=min(float(self.cfg.feedback_refinement.warmup_cpu_lim), max(time_left, 0.001)),
                        conflicts=point,
                    )
                    warmup_stats = solve_graph_with_timeout(
                        dataset=dataset,
                        graph=warmup_data_list[0],
                        solver=self.model_cfg.solver.solver if self.cfg.solver.solver is None else self.cfg.solver.solver,
                        params=point_params,
                        external_timeout=time_left,
                        collect_events=True,
                    )
                    refinement_stats_list.append(warmup_stats)
                    if remaining(start, self.first_cap) <= 0:
                        return self._timeout_row(file_path, start, f"warmup_c{point}")
                    refined_graphs = attach_var_event_state_batch(
                        warmup_data_list,
                        warmup_stats,
                        var_state_dim=self.var_state_dim,
                        momentum=float(self.cfg.feedback_refinement.state_momentum),
                        feature_mode=self.event_state_feature_mode,
                    )
                    refined_by_point[point] = refined_graphs
                    point_feature = _stats_selector_feature_frame(warmup_stats)
                    if selector_feature_names:
                        if model_feature_names:
                            model_feature = _extract_selector_feature_frame(
                                model=self.model,
                                graphs=refined_graphs,
                                feature_names=model_feature_names,
                                batch_size=1,
                                device=self.device,
                            )
                            point_feature = point_feature.merge(model_feature, on="cnf_id", how="left")
                        missing = sorted(set(base_feature_names).difference(point_feature.columns))
                        missing = [
                            name
                            for name in missing
                            if name not in DERIVED_SELECTOR_FEATURES and name not in EXTERNAL_SELECTOR_FEATURES
                        ]
                        if missing:
                            raise ValueError("missing selector features: " + ", ".join(missing))
                        feature_by_point[point] = point_feature.set_index("cnf_id")
                final_point = intervention_conflicts[-1]
                refined_graphs = refined_by_point[final_point]
                feature_by_point = _attach_derived_selector_stage_features(
                    self.model,
                    selector_feature_names=selector_feature_names,
                    final_point=final_point,
                    feature_by_point=feature_by_point,
                )
                refined_graphs = _attach_selector_feature_overrides(
                    refined_graphs,
                    selector_feature_names=selector_feature_names,
                    final_point=final_point,
                    feature_by_point=feature_by_point,
                    local_reopen_candidate_ids=local_reopen_candidate_ids,
                )

            data_list = []
            if refined_graphs:
                current_loader = DataLoader(dataset=refined_graphs, batch_size=1, num_workers=0, shuffle=False)
                data_list = sample_var_params(
                    model=self.model,
                    loader=current_loader,
                    device=self.device,
                    use_mode=True,
                    num_samples=1,
                    scale_sigma=self.model_cfg.scale_sigma,
                    add_timing=True,
                    cache_var_features=self.use_event_adapter_cache,
                )
            if pre_warmup_final_data_list:
                data_list = sorted([*pre_warmup_final_data_list, *data_list], key=_cnf_id_value)
            if not data_list:
                return self._timeout_row(file_path, start, "selector_closed")

            time_left = remaining(start, self.first_cap)
            if time_left <= 0:
                return self._timeout_row(file_path, start, "before_final")
            final_stats = solve_graph_with_timeout(
                dataset=dataset,
                graph=data_list[0],
                solver=self.model_cfg.solver.solver if self.cfg.solver.solver is None else self.cfg.solver.solver,
                params=params_with_time_cap(base_params, time_left),
                external_timeout=time_left,
                collect_events=False,
            )
            solver_stats = add_total_time_columns(
                final_stats,
                data_list,
                refinement_stats_list=refinement_stats_list,
                refinement_data_lists=refinement_data_lists,
            )
            if pre_warmup_skip_features is not None and not pre_warmup_skip_features.empty:
                solver_stats = solver_stats.merge(pre_warmup_skip_features, on="cnf_id", how="left")
            row = solver_stats.iloc[0].to_dict()
            wall = time.monotonic() - start
            result = str(row.get("Result", "INDETERMINATE"))
            solved = result in SOLVED_RESULTS and wall <= self.first_cap
            return {
                "file": str(file_path),
                "file_key": file_path.name,
                "local_result": result if solved else "TIMEOUT",
                "local_solved": solved,
                "local_wall_time": min(wall, self.first_cap),
                "local_actual_wall_time": wall,
                "local_stage": "final",
                "local_cpu_time_reported": row.get("CPU time", ""),
                "local_total_time_reported": row.get("time", ""),
                "local_external_timeout": bool(row.get("external_timeout", False)) or wall > self.first_cap,
            }
        except Exception as exc:
            return {
                "file": str(file_path),
                "file_key": file_path.name,
                "local_result": "ERROR",
                "local_solved": False,
                "local_wall_time": min(time.monotonic() - start, self.first_cap),
                "local_actual_wall_time": time.monotonic() - start,
                "local_stage": "error",
                "local_cpu_time_reported": "",
                "local_total_time_reported": "",
                "local_external_timeout": False,
                "error": repr(exc),
            }

    def _timeout_row(self, file_path: Path, start: float, stage: str) -> dict[str, Any]:
        wall = time.monotonic() - start
        return {
            "file": str(file_path),
            "file_key": file_path.name,
            "local_result": "TIMEOUT",
            "local_solved": False,
            "local_wall_time": min(wall, self.first_cap),
            "local_actual_wall_time": wall,
            "local_stage": stage,
            "local_cpu_time_reported": "",
            "local_total_time_reported": "",
            "local_external_timeout": wall >= self.first_cap,
        }


def smoke_files() -> list[Path]:
    keys = [
        "3sat_25.cnf",
        "3sat_132.cnf",
        "3sat_111.cnf",
        "3sat_48.cnf",
        "3sat_10.cnf",
        "3sat_188.cnf",
        "3sat_66.cnf",
        "3sat_0.cnf",
    ]
    return [ROOT / "data/test/3sat/400" / key for key in keys]


def full400_files() -> list[Path]:
    return sorted((ROOT / "data/test/3sat/400").glob("*.cnf"))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_analysis_tables(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    baseline = pd.read_csv(ROOT / "runs/analysis/cadical_neural_overlap/combined.csv")
    baseline["file_key"] = baseline["file_key"].astype(str)
    merged = frame.merge(
        baseline[
            [
                "file_key",
                "cadical_solved",
                "cadical_time",
                "local_correction_solved",
                "local_correction_time_mean",
                "pattern",
            ]
        ],
        on="file_key",
        how="left",
        suffixes=("", "_baseline"),
    )
    merged["pattern"] = merged["pattern"].astype(str).str.zfill(4)
    merged["portfolio_only_vs_cadical"] = (
        merged["portfolio_solved"].astype(bool) & ~merged["cadical_solved_baseline"].astype(bool)
    )
    merged["cadical_only_vs_portfolio"] = (
        ~merged["portfolio_solved"].astype(bool) & merged["cadical_solved_baseline"].astype(bool)
    )
    portfolio_only = merged.loc[
        merged["portfolio_only_vs_cadical"],
        [
            "file_key",
            "local_result",
            "local_solved",
            "local_wall_time",
            "cadical_result",
            "cadical_time",
            "portfolio_time",
            "local_correction_time_mean",
            "pattern",
        ],
    ].sort_values("file_key")
    cadical_only = merged.loc[
        merged["cadical_only_vs_portfolio"],
        [
            "file_key",
            "local_result",
            "local_solved",
            "cadical_result",
            "cadical_time",
            "portfolio_time",
            "local_correction_time_mean",
            "pattern",
        ],
    ].sort_values("file_key")
    summary = {
        "mode": mode,
        "instances": int(len(merged)),
        "portfolio_solved": int(merged["portfolio_solved"].sum()),
        "local_first_stage_solved": int(merged["local_solved"].sum()),
        "cadical_second_stage_solved": int(
            ((~merged["local_solved"].astype(bool)) & merged["cadical_solved"].astype(bool)).sum()
        ),
        "cadical_60s_baseline_solved": int(merged["cadical_solved_baseline"].sum()),
        "delta_vs_cadical_60s": int(merged["portfolio_solved"].sum() - merged["cadical_solved_baseline"].sum()),
        "portfolio_only_vs_cadical": int(merged["portfolio_only_vs_cadical"].sum()),
        "cadical_only_vs_portfolio": int(merged["cadical_only_vs_portfolio"].sum()),
        "local_errors": int((merged["local_result"] == "ERROR").sum()),
        "mean_portfolio_time": float(pd.to_numeric(merged["portfolio_time"], errors="coerce").mean()),
        "median_portfolio_time": float(pd.to_numeric(merged["portfolio_time"], errors="coerce").median()),
    }
    pd.DataFrame([summary]).to_csv(OUT_DIR / f"{mode}_summary.csv", index=False)
    portfolio_only.to_csv(OUT_DIR / f"{mode}_portfolio_only_vs_cadical.csv", index=False)
    cadical_only.to_csv(OUT_DIR / f"{mode}_cadical_only_vs_portfolio.csv", index=False)
    return summary


def run_cadical_stage(rows: list[dict[str, Any]], second_cap: float, workers: int) -> list[dict[str, Any]]:
    pending = [row for row in rows if not bool(row["local_solved"])]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(solve_cadical_one, row["file"], str(CADICAL), second_cap, second_cap + 5.0): row
            for row in pending
        }
        for future in as_completed(futures):
            row = futures[future]
            cad = future.result()
            row["cadical_result"] = cad["Result"]
            row["cadical_time"] = cad["time"]
            row["cadical_wall_time"] = cad["wall_time"]
            row["cadical_solved"] = str(cad["Result"]) in SOLVED_RESULTS
    for row in rows:
        if bool(row["local_solved"]):
            row["cadical_result"] = ""
            row["cadical_time"] = ""
            row["cadical_wall_time"] = ""
            row["cadical_solved"] = False
        row["portfolio_solved"] = bool(row["local_solved"]) or bool(row["cadical_solved"])
        row["portfolio_time"] = (
            float(row["local_wall_time"])
            if bool(row["local_solved"])
            else 5.0 + float(row["cadical_time"] if row["cadical_time"] != "" else second_cap)
        )
    return rows


def write_doc(rows: list[dict[str, Any]], mode: str, raw_name: str, summary: dict[str, Any]) -> None:
    portfolio_only = pd.read_csv(OUT_DIR / f"{mode}_portfolio_only_vs_cadical.csv", dtype={"pattern": str})
    cadical_only = pd.read_csv(OUT_DIR / f"{mode}_cadical_only_vs_portfolio.csv", dtype={"pattern": str})
    for frame in [portfolio_only, cadical_only]:
        if "pattern" in frame.columns:
            frame["pattern"] = frame["pattern"].astype(str).str.zfill(4)
    lines = [
        "# End-to-End Local-5s / CaDiCaL-55s Portfolio Evaluation",
        "",
        f"Mode: `{mode}`.",
        "",
        "This runner loads the Local Boundary Correction checkpoint once, then",
        "executes the Local workflow per instance under a 5s wall-clock budget.",
        "Warmup and final weighted-Glucose calls are externally capped by the",
        "remaining first-stage budget. Unsolved instances are then sent to",
        "CaDiCaL for 55s.",
        "",
        "Smoke mode is only a runner validation artifact. Full mode is the",
        "paper-relevant end-to-end interrupted schedule over full400.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| instances | {summary['instances']} |",
        f"| portfolio solved | {summary['portfolio_solved']} |",
    ]
    if mode == "full":
        lines.extend(
            [
                f"| CaDiCaL 60s baseline solved | {summary['cadical_60s_baseline_solved']} |",
                f"| delta vs CaDiCaL 60s | {summary['delta_vs_cadical_60s']:+d} |",
                f"| portfolio-only vs CaDiCaL | {summary['portfolio_only_vs_cadical']} |",
                f"| CaDiCaL-only vs portfolio | {summary['cadical_only_vs_portfolio']} |",
            ]
        )
    lines.extend(
        [
            f"| Local first-stage solved | {summary['local_first_stage_solved']} |",
            f"| CaDiCaL second-stage solved | {summary['cadical_second_stage_solved']} |",
            f"| mean portfolio time | {summary['mean_portfolio_time']:.3f}s |",
            f"| median portfolio time | {summary['median_portfolio_time']:.3f}s |",
            f"| Local errors | {summary['local_errors']} |",
            "",
            "## Portfolio-Only Instances",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            portfolio_only,
            [
                "file_key",
                "local_result",
                "local_solved",
                "local_wall_time",
                "cadical_result",
                "cadical_time",
                "portfolio_time",
                "local_correction_time_mean",
                "pattern",
            ],
        )
    )
    lines.extend(["", "## CaDiCaL-Only Instances", ""])
    lines.extend(
        markdown_table(
            cadical_only,
            [
                "file_key",
                "local_result",
                "local_solved",
                "cadical_result",
                "cadical_time",
                "portfolio_time",
                "local_correction_time_mean",
                "pattern",
            ],
        )
    )
    if mode == "full":
        lines.extend(
            [
                "",
                "## Decision",
                "",
            ]
        )
        if int(summary["delta_vs_cadical_60s"]) > 0:
            lines.extend(
                [
                    f"- The true end-to-end schedule improves over CaDiCaL 60s by {summary['delta_vs_cadical_60s']:+d}",
                    "  solved instances.",
                    "- This supports a real neural/CDCL complementarity portfolio result.",
                ]
            )
        else:
            lines.extend(
                [
                    "- The true end-to-end schedule does not improve over CaDiCaL 60s.",
                    "- The portfolio direction should stay as complementarity analysis,",
                    "  not a main performance claim.",
                ]
            )
    lines.extend(
        [
            "",
            "Generated artifacts:",
            "",
            "```text",
            f"runs/analysis/portfolio_e2e_local5_cadical55/{raw_name}",
            f"runs/analysis/portfolio_e2e_local5_cadical55/{mode}_summary.csv",
            f"runs/analysis/portfolio_e2e_local5_cadical55/{mode}_portfolio_only_vs_cadical.csv",
            f"runs/analysis/portfolio_e2e_local5_cadical55/{mode}_cadical_only_vs_portfolio.csv",
            "```",
        ]
    )
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None._"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        vals = []
        for col in columns:
            value = row[col]
            if isinstance(value, float):
                if pd.isna(value):
                    vals.append("")
                else:
                    vals.append(f"{value:.3f}")
            elif pd.isna(value):
                vals.append("")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Run resident end-to-end Local-5s then CaDiCaL-55s portfolio.")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--first-cap", type=float, default=5.0)
    parser.add_argument("--second-cap", type=float, default=55.0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    files = smoke_files() if args.mode == "smoke" else full400_files()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_name = f"{args.mode}_raw.csv"
    raw_path = OUT_DIR / raw_name
    runner = ResidentLocalRunner(first_cap=args.first_cap)
    runner.warm_model(files[0])
    rows = []
    for idx, file_path in enumerate(files, start=1):
        row = runner.run_one(file_path)
        rows.append(row)
        print(
            f"[{idx}/{len(files)}] {file_path.name} local={row['local_result']} "
            f"wall={float(row['local_wall_time']):.3f} stage={row['local_stage']}",
            flush=True,
        )
    rows = run_cadical_stage(rows, second_cap=args.second_cap, workers=args.workers)
    write_rows(raw_path, rows)
    summary = write_analysis_tables(rows, mode=args.mode)
    write_doc(rows, mode=args.mode, raw_name=raw_name, summary=summary)
    print(pd.DataFrame(rows).to_string(index=False))
    print(DOC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    main()
