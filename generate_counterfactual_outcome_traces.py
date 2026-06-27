from __future__ import annotations

import os
from copy import copy
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any

import hydra
import numpy as np
import pandas as pd
import torch
from omegaconf import DictConfig, ListConfig, OmegaConf
from torch_geometric.data import HeteroData
from torch_geometric.loader import DataLoader
from torch_geometric.seed import seed_everything

from src.data.dataset import DimacsCNFDataset
from src.model.model import load_checkpoint
from src.policy import policy
from src.policy.evaluate import compute_solver_stats, sample_var_params
from src.solving.budget import apply_rollout_budget
from src.solving.state import attach_var_event_state_batch


UNSOLVED_RESULTS = {"INDETERMINATE", "TIMEOUT", "UNKNOWN", None}
DEFAULT_MULTI_POINT_FEATURES = [
    "base_rho_mean",
    "base_rho_std",
    "base_rho_range",
    "delta_abs_mean",
    "delta_abs_max",
    "delta_mu_abs_mean",
    "event_gate_mean",
    "event_entropy_norm",
    "event_top05_mass",
    "event_top10_mass",
    "rho_event_corr",
    "rho_event_top10_overlap",
    "event_conf_learnt_log_mean",
    "event_conf_learnt_log_max",
]


@dataclass(frozen=True)
class CounterfactualLabelSpec:
    positive_speedup_ratio: float = 0.80
    negative_slowdown_ratio: float = 1.10
    positive_weight: float = 4.0
    negative_weight: float = 8.0
    recovery_weight: float | None = None
    lost_weight: float | None = None
    speedup_weight: float | None = None
    slowdown_weight: float | None = None
    easy_slowdown_weight: float | None = None
    positive_min_base_time: float = 0.0
    positive_min_delta_time: float = 0.0
    negative_min_delta_time: float = 0.0
    easy_base_time_cutoff: float = 0.0
    easy_negative_delta_time: float = 0.0


def resolve_path(path: str, work_dir: str) -> str:
    return path if os.path.isabs(path) else os.path.join(work_dir, path)


def _cnf_id(data: HeteroData) -> int:
    value = data.cnf_id
    return int(value.item() if hasattr(value, "item") else value)


def _result_is_solved(result: Any) -> bool:
    if pd.isna(result):
        return False
    return str(result) not in UNSOLVED_RESULTS


def _list_from_cfg(value: Any) -> list[Any]:
    if isinstance(value, (DictConfig, ListConfig)):
        value = OmegaConf.to_container(value, resolve=True)
    elif isinstance(value, (list, tuple)):
        value = list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        return [part.strip() for part in stripped.split(",") if part.strip()]
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def intervention_conflict_points(counterfactual_cfg: DictConfig) -> list[int]:
    raw = None
    if "intervention_conflicts" in counterfactual_cfg and counterfactual_cfg.intervention_conflicts is not None:
        raw = counterfactual_cfg.intervention_conflicts
    else:
        raw = counterfactual_cfg.warmup_conflicts
    points = sorted({int(value) for value in _list_from_cfg(raw) if int(value) > 0})
    if not points:
        raise ValueError("counterfactual warmup/intervention conflicts must contain at least one positive value")
    return points


def multi_point_feature_names(counterfactual_cfg: DictConfig) -> list[str]:
    if "multi_point_feature_names" not in counterfactual_cfg or counterfactual_cfg.multi_point_feature_names is None:
        return list(DEFAULT_MULTI_POINT_FEATURES)
    return [str(name) for name in _list_from_cfg(counterfactual_cfg.multi_point_feature_names)]


def _point_prefix(conflicts: int) -> str:
    return f"warmup_c{int(conflicts)}"


def _batch_cnf_ids(batch: HeteroData) -> list[int]:
    cnf_id = batch.cnf_id
    if hasattr(cnf_id, "view"):
        return [int(value) for value in cnf_id.view(-1).tolist()]
    if isinstance(cnf_id, list):
        return [int(value.item() if hasattr(value, "item") else value) for value in cnf_id]
    return [int(cnf_id.item() if hasattr(cnf_id, "item") else cnf_id)]


def _single_mode_graph(data: HeteroData, y_var: torch.Tensor, scale_sigma: float) -> HeteroData:
    graph = copy(data)
    y_var = y_var.detach().to(dtype=torch.float32, device="cpu")
    var_params = policy.mode(y_var=y_var, scale_sigma=scale_sigma).transpose(0, 1).contiguous()
    graph["var"].num_nodes = int(graph["lit"].num_nodes // 2)
    graph["var"].var_params = var_params
    graph.gpu_time = 0.0
    return graph


def cached_base_branch_graphs(data_list: list[HeteroData], scale_sigma: float) -> list[HeteroData]:
    graphs = []
    for data in data_list:
        if not ("var" in data.node_types and hasattr(data["var"], "base_y")):
            raise ValueError("Counterfactual base branch requires cached data['var'].base_y")
        graphs.append(_single_mode_graph(data, data["var"].base_y, scale_sigma=scale_sigma))
    return graphs


def _gpu_time_frame(data_list: list[HeteroData], column: str) -> pd.DataFrame:
    rows = []
    for data in data_list:
        rows.append({"cnf_id": _cnf_id(data), column: float(getattr(data, "gpu_time", 0.0))})
    return pd.DataFrame(rows)


@contextmanager
def _preserve_model_selector_names(model: torch.nn.Module):
    names = list(getattr(model, "event_adapter_selector_feature_names", []))
    model.event_adapter_selector_feature_names = []
    try:
        yield
    finally:
        model.event_adapter_selector_feature_names = names


def _normalise_stats(stats: pd.DataFrame, prefix: str, data_list: list[HeteroData]) -> pd.DataFrame:
    frame = stats.copy()
    if "Result" not in frame.columns:
        frame["Result"] = "INDETERMINATE"
    frame["Result"] = frame["Result"].fillna("INDETERMINATE")
    if "CPU time" not in frame.columns:
        frame["CPU time"] = np.nan
    gpu_frame = _gpu_time_frame(data_list, f"{prefix}_gpu_time")
    frame = frame.merge(gpu_frame, on="cnf_id", how="left")
    frame[f"{prefix}_gpu_time"] = frame[f"{prefix}_gpu_time"].fillna(0.0)
    frame[f"{prefix}_cpu_time"] = frame["CPU time"].fillna(0.0).astype(float)
    frame[f"{prefix}_time"] = frame[f"{prefix}_cpu_time"] + frame[f"{prefix}_gpu_time"]
    keep = [
        "cnf_id",
        "sample_id",
        "file",
        "Result",
        "decisions",
        "conflicts",
        "propagations",
        "restarts",
        f"{prefix}_cpu_time",
        f"{prefix}_gpu_time",
        f"{prefix}_time",
    ]
    keep = [column for column in keep if column in frame.columns]
    renamed = {
        "Result": f"{prefix}_result",
        "decisions": f"{prefix}_decisions",
        "conflicts": f"{prefix}_conflicts",
        "propagations": f"{prefix}_propagations",
        "restarts": f"{prefix}_restarts",
    }
    return frame[keep].rename(columns=renamed)


@torch.no_grad()
def _extract_point_feature_frame(
    model: torch.nn.Module,
    graphs: list[HeteroData],
    feature_names: list[str],
    batch_size: int,
    device: torch.device | str,
) -> pd.DataFrame:
    rows = []
    if not feature_names:
        return pd.DataFrame({"cnf_id": [_cnf_id(graph) for graph in graphs]})
    model.to(device)
    model.eval()
    loader = DataLoader(dataset=graphs, batch_size=batch_size, num_workers=0, shuffle=False)
    for batch in loader:
        batch = batch.to(device)
        with _preserve_model_selector_names(model):
            y = model(batch)
        base_y = batch["var"].base_y.to(dtype=torch.float32)
        var_state = batch["var"].event_state.to(dtype=torch.float32)
        delta = y.to(dtype=torch.float32) - base_y
        var_batch = batch["var"].batch if hasattr(batch["var"], "batch") else batch["lit"].batch[0::2]
        var_batch = var_batch.to(device=base_y.device)
        num_graphs = int(var_batch.max().item()) + 1 if var_batch.numel() > 0 else 1
        feature_values = torch.stack(
            [
                model._event_adapter_selector_feature(
                    name,
                    base_y=base_y,
                    var_state=var_state,
                    delta=delta,
                    var_batch=var_batch,
                    num_graphs=num_graphs,
                )
                for name in feature_names
            ],
            dim=1,
        )
        for cnf_id, values in zip(_batch_cnf_ids(batch), feature_values.detach().cpu()):
            row = {"cnf_id": int(cnf_id)}
            row.update({name: float(value) for name, value in zip(feature_names, values.tolist())})
            rows.append(row)
    return pd.DataFrame(rows)


def _multi_point_frame(
    *,
    points: list[int],
    stats_by_point: dict[int, pd.DataFrame],
    graphs_by_point: dict[int, list[HeteroData]],
    feature_frames_by_point: dict[int, pd.DataFrame],
    feature_names: list[str],
) -> pd.DataFrame:
    merged = None
    for point in points:
        prefix = _point_prefix(point)
        status = _normalise_stats(stats_by_point[point], prefix, graphs_by_point[point])
        result_col = f"{prefix}_result"
        status[f"{prefix}_solved"] = status[result_col].map(_result_is_solved)
        features = feature_frames_by_point.get(point, pd.DataFrame({"cnf_id": status["cnf_id"]}))
        renamed = features.rename(columns={name: f"{prefix}_{name}" for name in feature_names})
        current = status.merge(renamed, on="cnf_id", how="left")
        if merged is None:
            merged = current
        else:
            current = current.drop(columns=["file"], errors="ignore")
            merged = merged.merge(current, on=["cnf_id", "sample_id"], how="outer")
    if merged is None:
        return pd.DataFrame()
    merged["final_intervention_conflicts"] = int(points[-1])
    if len(points) > 1:
        solved_cols = [f"{_point_prefix(point)}_solved" for point in points[:-1]]
        merged["solved_before_final_intervention"] = merged[solved_cols].fillna(False).any(axis=1)
    else:
        merged["solved_before_final_intervention"] = False
    drift_names = list(
        dict.fromkeys(
            [
                *feature_names,
                "decisions",
                "conflicts",
                "propagations",
                "cpu_time",
                "time",
            ]
        )
    )
    for prev_point, next_point in zip(points, points[1:]):
        prev_prefix = _point_prefix(prev_point)
        next_prefix = _point_prefix(next_point)
        for feature in drift_names:
            prev_col = f"{prev_prefix}_{feature}"
            next_col = f"{next_prefix}_{feature}"
            if prev_col in merged.columns and next_col in merged.columns:
                merged[f"{next_prefix}_minus_{prev_prefix}_{feature}"] = merged[next_col] - merged[prev_col]
    return merged


def _size_from_file(path: str) -> str:
    parent = os.path.basename(os.path.dirname(str(path)))
    return parent if parent else "unknown"


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_empty_"
    columns = [str(column) for column in frame.columns]
    rows = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in frame.columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:.4f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _label_rows(frame: pd.DataFrame, spec: CounterfactualLabelSpec) -> pd.DataFrame:
    frame = frame.copy()
    frame["warmup_solved"] = frame["warmup_result"].map(_result_is_solved)
    frame["base_solved"] = frame["base_result"].map(_result_is_solved)
    frame["adapter_solved"] = frame["adapter_result"].map(_result_is_solved)
    frame["base_pipeline_time"] = frame["warmup_time"] + frame["base_time"]
    frame["adapter_pipeline_time"] = frame["warmup_time"] + frame["adapter_time"]
    frame["adapter_minus_base_time"] = frame["adapter_time"] - frame["base_time"]
    frame["base_minus_adapter_time"] = frame["base_time"] - frame["adapter_time"]
    frame["adapter_speedup_ratio"] = frame["adapter_time"] / frame["base_time"].clip(lower=1.0e-9)

    reached = ~frame["warmup_solved"]
    both_solved = reached & frame["base_solved"] & frame["adapter_solved"]
    recovered = reached & ~frame["base_solved"] & frame["adapter_solved"]
    lost = reached & frame["base_solved"] & ~frame["adapter_solved"]
    speedup = (
        both_solved
        & (frame["base_time"] >= float(spec.positive_min_base_time))
        & (frame["base_minus_adapter_time"] >= float(spec.positive_min_delta_time))
        & (frame["adapter_time"] <= spec.positive_speedup_ratio * frame["base_time"])
    )
    slowdown = (
        both_solved
        & (frame["adapter_minus_base_time"] >= float(spec.negative_min_delta_time))
        & (frame["adapter_time"] >= spec.negative_slowdown_ratio * frame["base_time"])
    )
    easy_slowdown = (
        both_solved
        & (float(spec.easy_base_time_cutoff) > 0.0)
        & (frame["base_time"] <= float(spec.easy_base_time_cutoff))
        & (frame["adapter_minus_base_time"] >= float(spec.easy_negative_delta_time))
    )

    frame["counterfactual_class"] = "neutral"
    frame["counterfactual_reason"] = "neutral"
    frame.loc[frame["warmup_solved"], "counterfactual_class"] = "warmup_solved"
    frame.loc[frame["warmup_solved"], "counterfactual_reason"] = "warmup_solved"
    frame.loc[recovered, "counterfactual_class"] = "positive"
    frame.loc[recovered, "counterfactual_reason"] = "recovered_timeout"
    frame.loc[speedup, "counterfactual_class"] = "positive"
    frame.loc[speedup, "counterfactual_reason"] = "hard_speedup"
    frame.loc[slowdown, "counterfactual_class"] = "negative"
    frame.loc[slowdown, "counterfactual_reason"] = "slowdown"
    frame.loc[easy_slowdown, "counterfactual_class"] = "negative"
    frame.loc[easy_slowdown, "counterfactual_reason"] = "easy_slowdown"
    frame.loc[lost, "counterfactual_class"] = "negative"
    frame.loc[lost, "counterfactual_reason"] = "lost_solution"
    frame["counterfactual_label"] = np.nan
    frame.loc[frame["counterfactual_class"] == "positive", "counterfactual_label"] = 1.0
    frame.loc[frame["counterfactual_class"] == "negative", "counterfactual_label"] = 0.0
    frame["counterfactual_weight"] = 0.0
    frame.loc[frame["counterfactual_reason"] == "recovered_timeout", "counterfactual_weight"] = (
        spec.recovery_weight if spec.recovery_weight is not None else spec.positive_weight
    )
    frame.loc[frame["counterfactual_reason"] == "hard_speedup", "counterfactual_weight"] = (
        spec.speedup_weight if spec.speedup_weight is not None else spec.positive_weight
    )
    frame.loc[frame["counterfactual_reason"] == "slowdown", "counterfactual_weight"] = (
        spec.slowdown_weight if spec.slowdown_weight is not None else spec.negative_weight
    )
    frame.loc[frame["counterfactual_reason"] == "easy_slowdown", "counterfactual_weight"] = (
        spec.easy_slowdown_weight if spec.easy_slowdown_weight is not None else spec.negative_weight
    )
    frame.loc[frame["counterfactual_reason"] == "lost_solution", "counterfactual_weight"] = (
        spec.lost_weight if spec.lost_weight is not None else spec.negative_weight
    )
    frame["counterfactual_class_code"] = -1
    frame.loc[frame["counterfactual_class"] == "negative", "counterfactual_class_code"] = 0
    frame.loc[frame["counterfactual_class"] == "positive", "counterfactual_class_code"] = 1
    frame.loc[frame["counterfactual_class"] == "warmup_solved", "counterfactual_class_code"] = -2
    return frame


def attach_outcome_labels_to_graphs(
    graphs: list[HeteroData],
    outcome_frame: pd.DataFrame,
) -> list[HeteroData]:
    by_cnf = {int(row["cnf_id"]): row for _, row in outcome_frame.iterrows()}
    labelled = []
    for data in graphs:
        graph = copy(data)
        row = by_cnf.get(_cnf_id(graph))
        if row is None:
            continue
        graph.counterfactual_class_code = torch.tensor([int(row["counterfactual_class_code"])], dtype=torch.long)
        label = row["counterfactual_label"]
        graph.counterfactual_label = torch.tensor(
            [float(label) if not pd.isna(label) else -1.0],
            dtype=torch.float32,
        )
        graph.counterfactual_weight = torch.tensor([float(row["counterfactual_weight"])], dtype=torch.float32)
        graph.base_branch_time = torch.tensor([float(row["base_time"])], dtype=torch.float32)
        graph.adapter_branch_time = torch.tensor([float(row["adapter_time"])], dtype=torch.float32)
        graph.adapter_minus_base_time = torch.tensor([float(row["adapter_minus_base_time"])], dtype=torch.float32)
        labelled.append(graph)
    return labelled


def _disable_adapter_gates(model: torch.nn.Module, cfg: DictConfig) -> None:
    preserve_selector_features = bool(
        cfg.counterfactual.get("preserve_selector_feature_names", False)
    )
    if bool(cfg.counterfactual.disable_adapter_selector) and not preserve_selector_features:
        model.event_adapter_selector_feature_names = []
    if bool(cfg.counterfactual.disable_adapter_base_rho_gate):
        model.event_adapter_base_rho_gate_threshold = None
    if bool(cfg.counterfactual.disable_adapter_graph_gate):
        model.event_adapter_graph_gate_indices = []
        model.event_adapter_graph_gate_threshold = None


def _write_doc(path: str, outcome_frame: pd.DataFrame, cfg: DictConfig, conflict_points: list[int]) -> None:
    counts = outcome_frame["counterfactual_class"].value_counts().rename_axis("class").reset_index(name="count")
    reason_counts = (
        outcome_frame["counterfactual_reason"]
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="count")
        if "counterfactual_reason" in outcome_frame.columns
        else pd.DataFrame()
    )
    summary = outcome_frame.groupby("counterfactual_class", sort=False)[
        ["base_time", "adapter_time", "adapter_minus_base_time"]
    ].mean(numeric_only=True).reset_index()
    doc = [
        "# Counterfactual Outcome Trace 生成",
        "",
        "本次运行从共享 warmup event trace 生成 paired base-vs-adapter labels。",
        "流程是先用同一份 warmup guidance rollout，收集变量级 event evidence；",
        "随后 base 和 adapter 分支都基于这份相同 evidence 进行评估。",
        "",
        "重要实现说明：当前 Glucose wrapper 不能序列化并恢复内部 CDCL",
        "trail/clause database。因此这些标签是 same-evidence branch",
        "counterfactuals，不是 in-process CDCL clone continuations。",
        "",
        "## 配置",
        "",
        f"- checkpoint：`{cfg.checkpoint}`",
        f"- dataset：`{cfg.dataset.path}`",
        f"- warmup budget：`{cfg.counterfactual.warmup_budget_type}` / `{conflict_points}` conflicts",
        f"- intervention point：`{conflict_points[-1]}` conflicts",
        f"- final cpu limit：`{cfg.counterfactual.final_cpu_lim}`",
        "",
        "## 多点 evidence",
        "",
        "如果配置中包含多个 `intervention_conflicts`，脚本会用同一个初始",
        "GNN guidance 分别运行多个 conflict 上限，并把各点 graph-level",
        "event features 及相邻点 drift 写入 outcome CSV/PT payload。",
        "当前 Glucose wrapper 还不能导出并恢复 CDCL 快照，所以这些点是",
        "same-initial-guidance cumulative probes，不是单个 CDCL 进程的连续暂停恢复。",
        "",
        "## 标签计数",
        "",
        _markdown_table(counts),
        "",
        "## 标签原因计数",
        "",
        _markdown_table(reason_counts),
        "",
        "## 分支平均时间",
        "",
        _markdown_table(summary),
        "",
    ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(doc) + "\n")


@hydra.main(version_base=None, config_path="configs", config_name="config_generate_counterfactual_outcome_traces")
def main(cfg: DictConfig) -> None:
    OmegaConf.resolve(cfg)
    print(OmegaConf.to_yaml(cfg))
    seed_everything(cfg.seed)

    output_path = resolve_path(cfg.counterfactual.output_path, cfg.work_dir)
    output_csv = resolve_path(cfg.counterfactual.output_csv, cfg.work_dir)
    warmup_csv = resolve_path(cfg.counterfactual.warmup_stats_csv, cfg.work_dir)
    base_csv = resolve_path(cfg.counterfactual.base_stats_csv, cfg.work_dir)
    adapter_csv = resolve_path(cfg.counterfactual.adapter_stats_csv, cfg.work_dir)
    doc_path = resolve_path(cfg.counterfactual.doc_path, cfg.work_dir)
    for path in [output_path, output_csv, warmup_csv, base_csv, adapter_csv, doc_path]:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    model, transform, model_cfg = load_checkpoint(resolve_path(cfg.checkpoint, cfg.work_dir), var_output=True)
    if not getattr(model, "event_adapter_enabled", False):
        raise ValueError("Counterfactual trace generation requires an event-adapter checkpoint")
    _disable_adapter_gates(model, cfg)
    model.eval()
    conflict_points = intervention_conflict_points(cfg.counterfactual)
    if len(conflict_points) > 1 and str(cfg.counterfactual.warmup_budget_type) != "conflicts":
        raise ValueError("Multi-point counterfactual evidence currently requires warmup_budget_type=conflicts")
    point_feature_names = multi_point_feature_names(cfg.counterfactual)

    dataset = DimacsCNFDataset(
        path=resolve_path(cfg.dataset.path, cfg.work_dir),
        transform=transform,
        lazy=bool(cfg.dataset.lazy),
    )
    loader = DataLoader(
        dataset=dataset,
        batch_size=cfg.loader.batch_size,
        num_workers=cfg.loader.num_workers,
        shuffle=False,
    )
    device = "cuda:0" if torch.cuda.is_available() and bool(cfg.counterfactual.use_cuda) else "cpu"

    warmup_graphs = sample_var_params(
        model=model,
        loader=loader,
        num_samples=1,
        max_num_batches=int(cfg.counterfactual.max_num_batches),
        device=device,
        use_mode=True,
        scale_sigma=model_cfg.scale_sigma,
        add_timing=True,
        cache_var_features=True,
    )
    warmup_stats_by_point: dict[int, pd.DataFrame] = {}
    refined_graphs_by_point: dict[int, list[HeteroData]] = {}
    feature_frames_by_point: dict[int, pd.DataFrame] = {}
    for point in conflict_points:
        print(f"Running warmup evidence probe at {point} conflicts")
        warmup_params = apply_rollout_budget(
            dict(cfg.solver.params),
            budget_type=cfg.counterfactual.warmup_budget_type,
            cpu_lim=cfg.counterfactual.warmup_cpu_lim,
            conflicts=point,
        )
        warmup_params["collect-events"] = True
        point_stats = compute_solver_stats(
            dataset=dataset,
            data_list=warmup_graphs,
            num_workers=cfg.solver.num_workers,
            solver=cfg.solver.solver if cfg.solver.solver is not None else model_cfg.solver.solver,
            **warmup_params,
        )
        point_stats = point_stats.copy()
        point_stats["intervention_conflicts"] = int(point)
        warmup_stats_by_point[point] = point_stats
        point_graphs = attach_var_event_state_batch(
            warmup_graphs,
            point_stats,
            var_state_dim=int(model.var_state_dim),
            momentum=float(cfg.counterfactual.state_momentum),
            feature_mode=str(cfg.counterfactual.event_state_features),
        )
        refined_graphs_by_point[point] = point_graphs
        feature_frames_by_point[point] = _extract_point_feature_frame(
            model=model,
            graphs=point_graphs,
            feature_names=point_feature_names,
            batch_size=int(cfg.loader.batch_size),
            device=device,
        )
    warmup_stats_combined = pd.concat(
        [warmup_stats_by_point[point] for point in conflict_points],
        ignore_index=True,
    )
    warmup_stats_combined.to_csv(warmup_csv, index=False)

    warmup_stats = warmup_stats_by_point[conflict_points[-1]]
    refined_graphs = refined_graphs_by_point[conflict_points[-1]]
    multi_point = _multi_point_frame(
        points=conflict_points,
        stats_by_point=warmup_stats_by_point,
        graphs_by_point=refined_graphs_by_point,
        feature_frames_by_point=feature_frames_by_point,
        feature_names=point_feature_names,
    )

    reached_ids = set(
        int(row["cnf_id"])
        for _, row in warmup_stats.iterrows()
        if not _result_is_solved(row.get("Result", "INDETERMINATE"))
    )
    branch_graphs = [graph for graph in refined_graphs if _cnf_id(graph) in reached_ids]
    print(f"Intervention reached for {len(branch_graphs)} / {len(refined_graphs)} graphs")

    final_params = dict(cfg.solver.params)
    final_params["cpu-lim"] = float(cfg.counterfactual.final_cpu_lim)
    base_graphs = cached_base_branch_graphs(branch_graphs, scale_sigma=model_cfg.scale_sigma)
    adapter_loader = DataLoader(
        dataset=branch_graphs,
        batch_size=cfg.loader.batch_size,
        num_workers=cfg.loader.num_workers,
        shuffle=False,
    )
    with _preserve_model_selector_names(model):
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
        num_workers=cfg.solver.num_workers,
        solver=cfg.solver.solver if cfg.solver.solver is not None else model_cfg.solver.solver,
        **final_params,
    )
    adapter_stats = compute_solver_stats(
        dataset=dataset,
        data_list=adapter_graphs,
        num_workers=cfg.solver.num_workers,
        solver=cfg.solver.solver if cfg.solver.solver is not None else model_cfg.solver.solver,
        **final_params,
    )
    base_stats.to_csv(base_csv, index=False)
    adapter_stats.to_csv(adapter_csv, index=False)

    warmup_frame = _normalise_stats(warmup_stats, "warmup", warmup_graphs)
    base_frame = _normalise_stats(base_stats, "base", base_graphs)
    adapter_frame = _normalise_stats(adapter_stats, "adapter", adapter_graphs)
    outcome = (
        warmup_frame
        .merge(base_frame.drop(columns=["file"], errors="ignore"), on=["cnf_id", "sample_id"], how="left")
        .merge(adapter_frame.drop(columns=["file"], errors="ignore"), on=["cnf_id", "sample_id"], how="left")
    )
    if not multi_point.empty:
        outcome = outcome.merge(
            multi_point.drop(columns=["file"], errors="ignore"),
            on=["cnf_id", "sample_id"],
            how="left",
        )
    outcome["size"] = outcome["file"].map(_size_from_file)
    outcome = _label_rows(outcome, CounterfactualLabelSpec(**OmegaConf.to_container(cfg.counterfactual.label)))
    outcome.to_csv(output_csv, index=False)

    labelled_graphs = attach_outcome_labels_to_graphs(refined_graphs, outcome)
    torch.save(
        {
            "graphs": labelled_graphs,
            "outcome_frame": outcome,
            "warmup_stats": warmup_stats,
            "warmup_stats_by_point": warmup_stats_by_point,
            "refined_graphs_by_point": refined_graphs_by_point,
            "multi_point_feature_frame": multi_point,
            "multi_point_feature_names": point_feature_names,
            "intervention_conflicts": conflict_points,
            "base_stats": base_stats,
            "adapter_stats": adapter_stats,
            "label_spec": asdict(CounterfactualLabelSpec(**OmegaConf.to_container(cfg.counterfactual.label))),
            "config": OmegaConf.to_container(cfg, resolve=True),
        },
        output_path,
    )
    _write_doc(doc_path, outcome, cfg, conflict_points)
    print(f"Saved {len(labelled_graphs)} labelled graphs to {output_path}")
    print(f"Saved counterfactual outcomes to {output_csv}")
    print(f"Saved warmup/base/adapter stats to {warmup_csv}, {base_csv}, {adapter_csv}")
    print(f"Saved report to {doc_path}")


if __name__ == "__main__":
    main()
