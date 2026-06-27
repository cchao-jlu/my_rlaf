from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from omegaconf import OmegaConf
from pysat.formula import CNF
from torch_geometric.loader import DataLoader

from generate_counterfactual_outcome_traces import cached_base_branch_graphs
from src.data.cnf import cnf_to_pyg
from src.model.model import load_checkpoint
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch


UNSOLVED_RESULTS = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", None}


class ExplicitCNFDataset:
    def __init__(self, files_by_id: dict[int, str]):
        self.id_to_file = dict(files_by_id)
        self._cnf_cache: dict[int, CNF] = {}

    def get_cnf(self, idx: int) -> CNF:
        idx = int(idx)
        if idx not in self._cnf_cache:
            self._cnf_cache[idx] = CNF(from_file=self.id_to_file[idx])
        return self._cnf_cache[idx]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repeatedly rerun recovered_timeout candidates and estimate recovery stability."
    )
    parser.add_argument("--trace", action="append", required=True)
    parser.add_argument(
        "--checkpoint",
        default="runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt",
    )
    parser.add_argument("--num-repeats", type=int, default=3)
    parser.add_argument("--num-workers", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--use-cuda", action="store_true")
    parser.add_argument("--candidate-limit", type=int, default=-1)
    parser.add_argument("--final-cpu-lim", type=float, default=None)
    parser.add_argument("--warmup-cpu-lim", type=float, default=None)
    parser.add_argument("--intervention-conflicts", type=int, default=None)
    parser.add_argument("--state-momentum", type=float, default=None)
    parser.add_argument("--event-state-features", default=None)
    parser.add_argument("--min-weight", type=float, default=0.15)
    parser.add_argument("--stable-threshold", type=float, default=0.60)
    parser.add_argument(
        "--detail-csv",
        default="runs/analysis/recovered_timeout_stability_repeats.csv",
    )
    parser.add_argument(
        "--summary-csv",
        default="runs/analysis/recovered_timeout_stability_summary.csv",
    )
    parser.add_argument(
        "--doc-path",
        default="docs/recovered_timeout_stability.md",
    )
    return parser.parse_args()


def _result_is_solved(result) -> bool:
    if pd.isna(result):
        return False
    return str(result) not in UNSOLVED_RESULTS


def _get_nested(config: dict, *keys, default=None):
    value = config
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def _file_key(path: str) -> str:
    return os.path.basename(str(path))


def _normalise_size(value) -> str:
    if pd.isna(value):
        return "unknown"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _load_payload(path: str) -> dict:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "outcome_frame" not in payload:
        raise ValueError(f"{path} is not a counterfactual trace payload")
    return payload


def _candidate_frame(trace_paths: list[str], candidate_limit: int) -> pd.DataFrame:
    frames = []
    for trace_id, path in enumerate(trace_paths):
        payload = _load_payload(path)
        outcome = payload["outcome_frame"]
        if not isinstance(outcome, pd.DataFrame):
            outcome = pd.DataFrame(outcome)
        candidates = outcome[outcome["counterfactual_reason"].eq("recovered_timeout")].copy()
        if candidates.empty:
            continue
        candidates["trace_path"] = path
        candidates["trace_id"] = int(trace_id)
        candidates["size"] = candidates["size"].map(_normalise_size)
        candidates["file_key"] = candidates["file"].map(_file_key)
        frames.append(candidates)
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.sort_values(["size", "file_key", "trace_path", "cnf_id"]).reset_index(drop=True)
    if candidate_limit is not None and int(candidate_limit) > 0:
        frame = frame.head(int(candidate_limit)).copy()
    return frame


def _build_graphs(candidates: pd.DataFrame, transform) -> list:
    graphs = []
    for _, row in candidates.iterrows():
        cnf = CNF(from_file=str(row["file"]))
        graph = cnf_to_pyg(f=cnf.clauses, num_var=cnf.nv)
        if transform is not None:
            graph = transform(graph)
        graph.cnf_id = torch.tensor(int(row["cnf_id"]), dtype=torch.long)
        graphs.append(graph)
    return graphs


def _disable_selector_gates(model) -> None:
    model.event_adapter_selector_feature_names = []
    model.event_adapter_base_rho_gate_threshold = None
    model.event_adapter_graph_gate_indices = []
    model.event_adapter_graph_gate_threshold = None


def _payload_run_cfg(payload: dict, args: argparse.Namespace, model_cfg) -> dict:
    config = payload.get("config", {})
    solver_cfg = config.get("solver", {}) if isinstance(config, dict) else {}
    counterfactual_cfg = config.get("counterfactual", {}) if isinstance(config, dict) else {}
    solver_params = dict(solver_cfg.get("params", {}))
    if not solver_params:
        solver_params = {"cpu-lim": 60.0, "rnd-freq": 0.0, "K": 0.1}
    final_cpu_lim = (
        float(args.final_cpu_lim)
        if args.final_cpu_lim is not None
        else float(counterfactual_cfg.get("final_cpu_lim", solver_params.get("cpu-lim", 60.0)))
    )
    warmup_cpu_lim = (
        float(args.warmup_cpu_lim)
        if args.warmup_cpu_lim is not None
        else float(counterfactual_cfg.get("warmup_cpu_lim", 15.0))
    )
    points = payload.get("intervention_conflicts")
    if args.intervention_conflicts is not None:
        intervention_conflicts = int(args.intervention_conflicts)
    elif isinstance(points, (list, tuple)) and points:
        intervention_conflicts = int(points[-1])
    else:
        intervention_conflicts = int(counterfactual_cfg.get("warmup_conflicts", 2000))
    state_momentum = (
        float(args.state_momentum)
        if args.state_momentum is not None
        else float(counterfactual_cfg.get("state_momentum", 0.5))
    )
    event_state_features = (
        str(args.event_state_features)
        if args.event_state_features is not None
        else str(counterfactual_cfg.get("event_state_features", "enhanced"))
    )
    return {
        "solver": solver_cfg.get("solver") or model_cfg.solver.solver,
        "solver_params": solver_params,
        "final_cpu_lim": final_cpu_lim,
        "warmup_cpu_lim": warmup_cpu_lim,
        "warmup_budget_type": str(counterfactual_cfg.get("warmup_budget_type", "conflicts")),
        "intervention_conflicts": intervention_conflicts,
        "state_momentum": state_momentum,
        "event_state_features": event_state_features,
    }


def _gpu_time_by_cnf(graphs: list) -> dict[int, float]:
    result = {}
    for graph in graphs:
        cnf_id = int(graph.cnf_id.item() if hasattr(graph.cnf_id, "item") else graph.cnf_id)
        result[cnf_id] = float(getattr(graph, "gpu_time", 0.0))
    return result


def _stats_by_cnf(stats: pd.DataFrame) -> dict[int, pd.Series]:
    return {int(row["cnf_id"]): row for _, row in stats.iterrows()}


def _row_stat(row, key: str, default=0.0):
    if row is None or key not in row or pd.isna(row[key]):
        return default
    return row[key]


def _run_repeat_for_trace(
    *,
    payload: dict,
    trace_path: str,
    trace_id: int,
    candidates: pd.DataFrame,
    model,
    transform,
    model_cfg,
    args: argparse.Namespace,
    device: str,
) -> list[dict]:
    if candidates.empty:
        return []
    run_cfg = _payload_run_cfg(payload, args, model_cfg)
    files_by_id = {int(row["cnf_id"]): str(row["file"]) for _, row in candidates.iterrows()}
    dataset = ExplicitCNFDataset(files_by_id)
    rows = []
    for repeat_id in range(int(args.num_repeats)):
        initial_graphs = _build_graphs(candidates, transform)
        initial_loader = DataLoader(
            dataset=initial_graphs,
            batch_size=int(args.batch_size),
            num_workers=0,
            shuffle=False,
        )
        warmup_graphs = sample_var_params(
            model=model,
            loader=initial_loader,
            num_samples=1,
            device=device,
            use_mode=True,
            scale_sigma=model_cfg.scale_sigma,
            add_timing=True,
            cache_var_features=True,
        )
        warmup_params = apply_rollout_budget(
            dict(run_cfg["solver_params"]),
            budget_type=run_cfg["warmup_budget_type"],
            cpu_lim=run_cfg["warmup_cpu_lim"],
            conflicts=run_cfg["intervention_conflicts"],
        )
        warmup_params["collect-events"] = True
        warmup_stats = compute_solver_stats(
            dataset=dataset,
            data_list=warmup_graphs,
            num_workers=int(args.num_workers),
            solver=run_cfg["solver"],
            **warmup_params,
        )
        refined_graphs = attach_var_event_state_batch(
            warmup_graphs,
            warmup_stats,
            var_state_dim=int(model.var_state_dim),
            momentum=float(run_cfg["state_momentum"]),
            feature_mode=str(run_cfg["event_state_features"]),
        )
        final_params = dict(run_cfg["solver_params"])
        final_params["cpu-lim"] = float(run_cfg["final_cpu_lim"])
        base_graphs = cached_base_branch_graphs(refined_graphs, scale_sigma=model_cfg.scale_sigma)
        adapter_loader = DataLoader(
            dataset=refined_graphs,
            batch_size=int(args.batch_size),
            num_workers=0,
            shuffle=False,
        )
        adapter_graphs = sample_var_params(
            model=model,
            loader=adapter_loader,
            num_samples=1,
            device=device,
            use_mode=True,
            scale_sigma=model_cfg.scale_sigma,
            add_timing=True,
            cache_var_features=False,
        )
        base_stats = compute_solver_stats(
            dataset=dataset,
            data_list=base_graphs,
            num_workers=int(args.num_workers),
            solver=run_cfg["solver"],
            **final_params,
        )
        adapter_stats = compute_solver_stats(
            dataset=dataset,
            data_list=adapter_graphs,
            num_workers=int(args.num_workers),
            solver=run_cfg["solver"],
            **final_params,
        )
        warmup_by_cnf = _stats_by_cnf(warmup_stats)
        base_by_cnf = _stats_by_cnf(base_stats)
        adapter_by_cnf = _stats_by_cnf(adapter_stats)
        warmup_gpu = _gpu_time_by_cnf(warmup_graphs)
        adapter_gpu = _gpu_time_by_cnf(adapter_graphs)
        for _, candidate in candidates.iterrows():
            cnf_id = int(candidate["cnf_id"])
            warmup = warmup_by_cnf.get(cnf_id)
            base = base_by_cnf.get(cnf_id)
            adapter = adapter_by_cnf.get(cnf_id)
            warmup_result = _row_stat(warmup, "Result", "INDETERMINATE")
            base_result = _row_stat(base, "Result", "INDETERMINATE")
            adapter_result = _row_stat(adapter, "Result", "INDETERMINATE")
            warmup_solved = _result_is_solved(warmup_result)
            base_solved = _result_is_solved(base_result)
            adapter_solved = _result_is_solved(adapter_result)
            recovered = (not warmup_solved) and (not base_solved) and adapter_solved
            rows.append(
                {
                    "trace_path": trace_path,
                    "trace_id": int(trace_id),
                    "repeat_id": int(repeat_id),
                    "size": _normalise_size(candidate["size"]),
                    "file_key": str(candidate["file_key"]),
                    "file": str(candidate["file"]),
                    "cnf_id": cnf_id,
                    "warmup_result": warmup_result,
                    "base_result": base_result,
                    "adapter_result": adapter_result,
                    "warmup_solved": bool(warmup_solved),
                    "base_solved": bool(base_solved),
                    "adapter_solved": bool(adapter_solved),
                    "recovered_timeout": bool(recovered),
                    "warmup_cpu_time": float(_row_stat(warmup, "CPU time", 0.0)),
                    "base_cpu_time": float(_row_stat(base, "CPU time", 0.0)),
                    "adapter_cpu_time": float(_row_stat(adapter, "CPU time", 0.0)),
                    "warmup_gpu_time": float(warmup_gpu.get(cnf_id, 0.0)),
                    "adapter_gpu_time": float(adapter_gpu.get(cnf_id, 0.0)),
                    "warmup_time": float(_row_stat(warmup, "CPU time", 0.0)) + float(warmup_gpu.get(cnf_id, 0.0)),
                    "base_time": float(_row_stat(base, "CPU time", 0.0)),
                    "adapter_time": float(_row_stat(adapter, "CPU time", 0.0)) + float(adapter_gpu.get(cnf_id, 0.0)),
                    "base_conflicts": float(_row_stat(base, "conflicts", 0.0)),
                    "adapter_conflicts": float(_row_stat(adapter, "conflicts", 0.0)),
                    "base_decisions": float(_row_stat(base, "decisions", 0.0)),
                    "adapter_decisions": float(_row_stat(adapter, "decisions", 0.0)),
                }
            )
    return rows


def _summarise(detail: pd.DataFrame, min_weight: float, stable_threshold: float) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame()
    rows = []
    group_cols = ["trace_path", "trace_id", "size", "file_key", "file", "cnf_id"]
    for keys, group in detail.groupby(group_cols, sort=True, dropna=False):
        row = dict(zip(group_cols, keys))
        repeats = len(group)
        row["repeats"] = int(repeats)
        row["warmup_solved_rate"] = float(group["warmup_solved"].mean())
        row["base_solved_rate"] = float(group["base_solved"].mean())
        row["base_unsolved_rate"] = float((~group["base_solved"].astype(bool)).mean())
        row["adapter_solved_rate"] = float(group["adapter_solved"].mean())
        row["recovered_rate"] = float(group["recovered_timeout"].mean())
        row["base_mean_time"] = float(group["base_time"].mean())
        row["adapter_mean_time"] = float(group["adapter_time"].mean())
        row["adapter_time_std"] = float(group["adapter_time"].std(ddof=0))
        row["mean_adapter_minus_base_time"] = float((group["adapter_time"] - group["base_time"]).mean())
        row["recovery_stability_weight_raw"] = row["recovered_rate"]
        row["recovery_stability_weight"] = float(
            min(1.0, max(float(min_weight), row["recovered_rate"]))
        )
        row["stable_recovered"] = bool(row["recovered_rate"] >= float(stable_threshold))
        rows.append(row)
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_空_"
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame[columns].iterrows():
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _write_doc(path: str, summary: pd.DataFrame, detail: pd.DataFrame, args: argparse.Namespace) -> None:
    if summary.empty:
        doc = [
            "# recovered_timeout 重复运行稳定性标注",
            "",
            "没有找到 `recovered_timeout` 候选，未生成稳定性权重。",
            "",
        ]
    else:
        size_summary = (
            summary.groupby("size", sort=True)
            .agg(
                n=("file_key", "count"),
                stable_recovered=("stable_recovered", "sum"),
                recovered_rate_mean=("recovered_rate", "mean"),
                stability_weight_mean=("recovery_stability_weight", "mean"),
            )
            .reset_index()
        )
        key_cols = [
            "size",
            "file_key",
            "repeats",
            "recovered_rate",
            "base_unsolved_rate",
            "adapter_solved_rate",
            "base_mean_time",
            "adapter_mean_time",
            "recovery_stability_weight",
            "stable_recovered",
        ]
        doc = [
            "# recovered_timeout 重复运行稳定性标注",
            "",
            "本报告只针对训练 trace 中原本标为 `recovered_timeout` 的样本。",
            "每个候选重复执行 warmup -> event state -> base/adapter 分支，",
            "用 `recovered_rate = P(base 未解且 adapter 解出)` 估计恢复稳定性。",
            "",
            "训练时不会翻转原始标签，只会把 `recovered_timeout` 的 recovery detector",
            "样本权重乘以 `recovery_stability_weight`，从而降低不稳定恢复样本的影响。",
            "",
            "## 配置",
            "",
            f"- repeats：`{args.num_repeats}`",
            f"- min weight：`{args.min_weight}`",
            f"- stable threshold：`{args.stable_threshold}`",
            f"- detail csv：`{args.detail_csv}`",
            f"- summary csv：`{args.summary_csv}`",
            "",
            "## 按规模汇总",
            "",
            _markdown_table(
                size_summary,
                ["size", "n", "stable_recovered", "recovered_rate_mean", "stability_weight_mean"],
            ),
            "",
            "## 候选明细",
            "",
            _markdown_table(summary.sort_values(["size", "file_key"]), key_cols),
            "",
        ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(doc) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    candidates = _candidate_frame(args.trace, candidate_limit=int(args.candidate_limit))
    Path(args.detail_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary_csv).parent.mkdir(parents=True, exist_ok=True)
    if candidates.empty:
        pd.DataFrame().to_csv(args.detail_csv, index=False)
        pd.DataFrame().to_csv(args.summary_csv, index=False)
        _write_doc(args.doc_path, pd.DataFrame(), pd.DataFrame(), args)
        print("No recovered_timeout candidates found.")
        return

    model, transform, model_cfg = load_checkpoint(args.checkpoint, var_output=True)
    _disable_selector_gates(model)
    device = "cuda:0" if torch.cuda.is_available() and bool(args.use_cuda) else "cpu"
    model.to(device)
    model.eval()

    rows = []
    for (trace_id, trace_path), trace_candidates in candidates.groupby(["trace_id", "trace_path"], sort=True):
        payload = _load_payload(str(trace_path))
        rows.extend(
            _run_repeat_for_trace(
                payload=payload,
                trace_path=str(trace_path),
                trace_id=int(trace_id),
                candidates=trace_candidates.copy(),
                model=model,
                transform=transform,
                model_cfg=model_cfg,
                args=args,
                device=device,
            )
        )
    detail = pd.DataFrame(rows)
    summary = _summarise(detail, min_weight=float(args.min_weight), stable_threshold=float(args.stable_threshold))
    detail.to_csv(args.detail_csv, index=False)
    summary.to_csv(args.summary_csv, index=False)
    _write_doc(args.doc_path, summary, detail, args)
    print(f"candidates: {len(summary)}")
    print(f"detail rows: {len(detail)}")
    if not summary.empty:
        print(f"stable recovered: {int(summary['stable_recovered'].sum())}/{len(summary)}")
        print(f"mean recovered rate: {summary['recovered_rate'].mean():.4f}")
    print(f"saved detail csv: {args.detail_csv}")
    print(f"saved summary csv: {args.summary_csv}")
    print(f"saved report: {args.doc_path}")


if __name__ == "__main__":
    main()
