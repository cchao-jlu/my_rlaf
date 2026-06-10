import os
import sys
from pathlib import Path

import hydra
import numpy as np
import pandas as pd
import torch

import wandb
from omegaconf import DictConfig, OmegaConf
from torch_geometric.loader import DataLoader
from torch_geometric.seed import seed_everything

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.evaluate_guided_solver import load_checkpoint
from src.data.dataset import DimacsCNFDataset, RLTrainingDataset
from src.policy.evaluate import compute_solver_stats, sample_random_var_params, sample_var_params
from src.model.model import GNN, init_model, init_transform
from src.solving.state import attach_global_state_batch

from src.training.dpo import train_dpo
from src.training.grpo import train_grpo, get_grpo_advantage

import warnings
warnings.filterwarnings("ignore", category=UserWarning)


COMPOSITE_TARGETS = {"composite"}


def solver_params(cfg: DictConfig) -> dict:
    return {
        str(key): value
        for key, value in dict(cfg.solver.params).items()
        if value is not None
    }


def log_solver_metrics(
        solver_stats: pd.DataFrame,
        iteration: int,
        global_step: int,
        prefix: str = "train",
        add_target_histogram: bool = False,
        target_stat: str = "decisions",
) -> None:
    keys = ["decisions", "conflicts", "propagations", "restarts", "CPU time"]
    metrics = {f"{prefix}/{key}": solver_stats[key].mean() for key in keys if key in solver_stats.columns}

    print(
        f"Solver metrics at iteration {iteration} ({prefix}): \n"
        + "\n".join(f"{key}: {val:.2f}" for key, val in metrics.items())
    )

    metrics[f"iteration"] = iteration
    metrics[f"global_step"] = global_step

    for key in keys:
        if key in metrics:
            metrics[f"{prefix}/{key}_histogram"] = wandb.Histogram(solver_stats[key])

    if add_target_histogram:
        grouped = solver_stats[["cnf_id", target_stat]].groupby("cnf_id")
        target_mean = grouped.mean().loc[solver_stats["cnf_id"]]
        target_mean = target_mean[target_stat].to_numpy()
        if not np.any(np.isnan(target_mean)):
            metrics[f"{prefix}/{target_stat}_histogram_mean"] = wandb.Histogram(target_mean)
        target_std = grouped.std().loc[solver_stats["cnf_id"]]
        target_std = target_std[target_stat].to_numpy()
        if not np.any(np.isnan(target_std)):
            metrics[f"{prefix}/{target_stat}_histogram_std"] = wandb.Histogram(target_std)

    wandb.log(metrics, step=global_step)


def solved_mask(solver_stats: pd.DataFrame) -> pd.Series:
    if "Result" not in solver_stats.columns:
        return pd.Series(False, index=solver_stats.index)
    return solver_stats["Result"].astype(str).isin({"SATISFIABLE", "UNSATISFIABLE"})


def add_composite_target(solver_stats: pd.DataFrame, cfg: DictConfig) -> pd.DataFrame:
    if str(cfg.training.target_stat) not in COMPOSITE_TARGETS:
        return solver_stats

    solver_stats = solver_stats.copy()

    def stat_values(column: str) -> np.ndarray:
        if column not in solver_stats.columns:
            return np.zeros(len(solver_stats), dtype=np.float64)
        values = pd.to_numeric(solver_stats[column], errors="coerce")
        fill_value = values.max()
        if pd.isna(fill_value):
            fill_value = 0.0
        return values.fillna(fill_value).to_numpy(dtype=np.float64)

    composite = np.zeros(len(solver_stats), dtype=np.float64)
    composite += float(cfg.training.composite_cpu_weight) * np.log1p(stat_values("CPU time"))
    composite += float(cfg.training.composite_conflicts_weight) * np.log1p(stat_values("conflicts"))
    composite += float(cfg.training.composite_decisions_weight) * np.log1p(stat_values("decisions"))
    if "composite_unsolved_penalty" in cfg.training:
        composite += float(cfg.training.composite_unsolved_penalty) * (~solved_mask(solver_stats)).to_numpy()
    solver_stats["composite"] = composite
    return solver_stats


def save_model(model: GNN, cfg: DictConfig, checkpoint_name: str = "last") -> None:
    model_dir = cfg.model_dir
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    cfg_path = os.path.join(model_dir, "config.yaml")
    with open(cfg_path, "w") as f:
        OmegaConf.save(cfg, f)
    ckpt_path = os.path.join(model_dir, f"{checkpoint_name}.pt")
    state_dict = model.state_dict()
    torch.save(state_dict, ckpt_path)


def build_feedback_state_loader(
        model: GNN,
        dataset: DimacsCNFDataset,
        loader: DataLoader,
        cfg: DictConfig,
        device: torch.device | str,
        max_num_batches: int = -1,
        mode: str | None = None,
        shuffle: bool = True,
) -> DataLoader:
    mode = cfg.training.feedback_input_mode if mode is None else mode
    if mode == "none":
        return loader

    global_state_dim = getattr(model, "global_state_dim", 0)
    if global_state_dim <= 0:
        raise ValueError("global feedback requires model.global_state_dim > 0")

    if mode == "mixed_warmup":
        mode = "model_warmup" if np.random.random() < cfg.training.feedback_model_warmup_prob else "random_warmup"

    if mode == "random_warmup":
        warmup_data_list = sample_random_var_params(
            loader=loader,
            num_samples=cfg.training.feedback_warmup_num_samples,
            max_num_batches=max_num_batches,
            weight_scale=cfg.training.feedback_random_weight,
        )
    elif mode == "model_warmup":
        warmup_data_list = sample_var_params(
            model=model,
            loader=loader,
            num_samples=cfg.training.feedback_warmup_num_samples,
            max_num_batches=max_num_batches,
            device=device,
            use_mode=True,
            scale_sigma=cfg.scale_sigma,
        )
    else:
        raise ValueError(f"Unknown feedback_input_mode {mode}")

    warmup_params = solver_params(cfg)
    warmup_params["cpu-lim"] = cfg.training.feedback_warmup_cpu_lim
    warmup_stats = compute_solver_stats(
        dataset=dataset,
        data_list=warmup_data_list,
        num_workers=cfg.solver.num_workers,
        solver=cfg.solver.solver,
        **warmup_params,
    )
    refined_graphs = attach_global_state_batch(
        warmup_data_list,
        warmup_stats,
        global_state_dim=global_state_dim,
    )
    return DataLoader(
        dataset=refined_graphs,
        batch_size=cfg.loader.batch_size,
        num_workers=cfg.loader.num_workers,
        shuffle=shuffle,
    )


@hydra.main(version_base=None, config_path="../../configs", config_name="config_train_rlaf")
def main(cfg: DictConfig):
    OmegaConf.resolve(cfg)
    print(OmegaConf.to_yaml(cfg))
    seed_everything(cfg.seed)

    wandb.init(
        project=cfg.wandb.project,
        name=cfg.wandb.name,
        config=OmegaConf.to_container(cfg),
    )

    if cfg.from_checkpoint is not None:
        model, transform, _ = load_checkpoint(cfg.from_checkpoint)
    else:
        transform = init_transform(cfg)
        model = init_model(cfg, transform)

    dataset_train = DimacsCNFDataset(
        path=cfg.dataset.train_path,
        transform=transform,
    )
    loader_train = DataLoader(
        dataset=dataset_train,
        batch_size=cfg.loader.batch_size,
        num_workers=cfg.loader.num_workers,
        shuffle=True,
    )

    dataset_val = DimacsCNFDataset(
        path=cfg.dataset.val_path,
        transform=transform,
    )
    loader_val = DataLoader(
        dataset=dataset_val,
        batch_size=cfg.loader.batch_size,
        num_workers=cfg.loader.num_workers,
        shuffle=False,
    )

    assert cfg.training.cnf_per_iter % cfg.loader.batch_size == 0
    train_sample_num_batches = cfg.training.cnf_per_iter // cfg.loader.batch_size

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Using device {device}")

    optim = torch.optim.AdamW(
        params=model.parameters(),
        lr=cfg.optim.lr,
        weight_decay=cfg.optim.weight_decay,
        maximize=True,
    )

    warmup_iterations = 5
    def lr_lambda(step):
        if step < warmup_iterations:
            # Warmup from 0 to 1.0
            return float(step + 1) / float(warmup_iterations)
        else:
            return 1.0
    sched = torch.optim.lr_scheduler.LambdaLR(optim, lr_lambda)

    if cfg.ckpt_interval is not None:
        print(f"Saving checkpoint at iteration 0")
        save_model(model, cfg, f"iter=0")

    best_score = np.inf

    global_step = 0
    for iteration in range(cfg.training.iterations):
        print(f" ----------------------- {'GRPO' if cfg.method == 'grpo' else 'DPO'} Iteration {iteration} ----------------------- ")

        # validate if necessary
        if iteration % cfg.val_interval == 0:
            loader_val_current = build_feedback_state_loader(
                model=model,
                dataset=dataset_val,
                loader=loader_val,
                cfg=cfg,
                device=device,
                mode=cfg.training.feedback_val_mode,
                shuffle=False,
            )
            data_list_val = sample_var_params(
                model=model,
                loader=loader_val_current,
                num_samples=1,
                device=device,
                use_mode=True,
                scale_sigma=cfg.scale_sigma,
            )

            solver_stats_val = compute_solver_stats(
                dataset=dataset_val,
                data_list=data_list_val,
                num_workers=cfg.solver.num_workers,
                solver=cfg.solver.solver,
                **solver_params(cfg),
            )
            solver_stats_val = add_composite_target(solver_stats_val, cfg)

            log_solver_metrics(
                solver_stats=solver_stats_val,
                iteration=iteration,
                global_step=global_step,
                prefix="val",
                add_target_histogram=True,
                target_stat=cfg.training.target_stat
            )

            score = solver_stats_val[cfg.training.target_stat].mean()
            if score < best_score:
                print("Saving new best checkpoint")
                save_model(model, cfg, "best")
                best_score = score

        loader_train_current = build_feedback_state_loader(
            model=model,
            dataset=dataset_train,
            loader=loader_train,
            cfg=cfg,
            device=device,
            max_num_batches=train_sample_num_batches,
            shuffle=True,
        )

        data_list_train = sample_var_params(
            model=model,
            loader=loader_train_current,
            num_samples=cfg.training.num_samples,
            max_num_batches=train_sample_num_batches,
            device=device,
            scale_sigma=cfg.scale_sigma,
        )

        solver_stats = compute_solver_stats(
            dataset=dataset_train,
            data_list=data_list_train,
            num_workers=cfg.solver.num_workers,
            solver=cfg.solver.solver,
            **solver_params(cfg),
        )
        solver_stats = add_composite_target(solver_stats, cfg)

        log_solver_metrics(
            solver_stats=solver_stats,
            iteration=iteration,
            global_step=global_step,
            prefix="train",
            add_target_histogram=True,
            target_stat=cfg.training.target_stat,
        )

        if cfg.method == "grpo":
            solver_stats["advantage"] = get_grpo_advantage(solver_stats, cfg.training.target_stat)
            iteration_dataset = RLTrainingDataset(
                data_list=data_list_train,
                solver_stats=solver_stats,
                target_stat="advantage",
                objective="maximize",
            )
        else:
            iteration_dataset = RLTrainingDataset(
                data_list=data_list_train,
                solver_stats=solver_stats,
                target_stat=cfg.training.target_stat
            )

        iteration_loader = DataLoader(
            dataset=iteration_dataset,
            batch_size=cfg.loader.batch_size,
            num_workers=cfg.loader.num_workers,
            shuffle=True
        )

        if cfg.method == "grpo":
            global_step = train_grpo(
                model=model,
                optim=optim,
                sched=sched,
                loader=iteration_loader,
                steps=cfg.training.steps_per_iter,
                clip_ratio=cfg.training.clip_ratio,
                kl_penalty=cfg.training.kl_penalty,
                global_step=global_step,
                device=device,
                use_amp=cfg.training.use_amp,
                scale_sigma=cfg.scale_sigma,
            )
        else:
            global_step = train_dpo(
                model=model,
                optim=optim,
                sched=sched,
                loader=iteration_loader,
                steps=cfg.training.steps_per_iter,
                beta=cfg.training.beta,
                kl_penalty=cfg.training.kl_penalty,
                global_step=global_step,
                device=device,
                use_amp=cfg.training.use_amp,
                scale_sigma=cfg.scale_sigma,
            )

        if cfg.ckpt_interval is not None and iteration % cfg.ckpt_interval == 0:
            print(f"Saving checkpoint at iteration {iteration}")
            save_model(model, cfg, f"iter={iteration}")

    wandb.finish()


if __name__ == '__main__':
    main()
