import os

import torch
import torch.nn as nn
from torch import Tensor
from torch_geometric.data import HeteroData
from omegaconf import DictConfig, OmegaConf

from src.data.transform import AddNodeFeatures
from src.model.modules import GNNLayer, FeatureEncoder, SinusoidalNumericalEncoder


class GNN(nn.Module):

    def __init__(
            self,
            channels: int,
            lit_feat_dim: int,
            cls_feat_dim: int,
            num_layers: int,
            out_dim: int = 2,
            aggr: str | list[str] = "mean",
            feature_encoder: str = "mlp",
            dropout: float = 0.0,
            var_output: bool = True,
            separate_encoders: bool = False,
    ):
        """
        A message-passing Graph Neural Network
        :param channels: Hidden model dimension
        :param lit_feat_dim: Dimension of literal node features
        :param cls_feat_dim: Dimension of clause node features
        :param num_layers: Number of message passing layers
        :param out_dim: node-level output dimension
        :param aggr: Message aggregation function either mean, max, or sum. If a list is provided, than multiple types of aggregation are performed in parallel.
        :param feature_encoder: Type of node feature encoder. Either "mlp" for a simple perceptron or "sin" for a sinusoidal numerical encoder.
        :param dropout: Dropout probability
        :param var_output: If true, the output will be per variable. If false, the output will be per literal, which is useful for our supervised tasks like backbone prediction.
        """
        super(GNN, self).__init__()
        self.channels = channels
        self.separate_encoders = separate_encoders

        if feature_encoder not in {"mlp", "sin"}:
            raise ValueError(f"Unknown feature encoder type {feature_encoder}")
        encoder_cls = FeatureEncoder if feature_encoder == "mlp" else SinusoidalNumericalEncoder

        if not separate_encoders and lit_feat_dim != cls_feat_dim:
            raise ValueError("Shared literal/clause encoder requires matching feature dimensions")

        self.lit_enc = encoder_cls(
            channels_in=lit_feat_dim,
            channels_out=channels,
            dropout=dropout,
        )
        if separate_encoders:
            self.cls_enc = encoder_cls(
                channels_in=cls_feat_dim,
                channels_out=channels,
                dropout=dropout,
            )
        else:
            self.cls_enc = self.lit_enc

        self.layers = nn.ModuleList([
            GNNLayer(channels=channels, aggr=aggr, dropout=dropout) for _ in range(num_layers)
        ])

        self.var_output = var_output
        if self.var_output:
            # output mlp with last layer initialized with zeros
            self.out_lin1 = nn.Linear(2 * channels, 2 * channels)
            self.out_lin2 = nn.Linear(2 * channels, out_dim)
            nn.init.zeros_(self.out_lin2.weight)
            self.out_act = nn.SiLU(inplace=True)
        else:
            # output mlp with last layer initialized with zeros
            self.out_lin1 = nn.Linear(channels, 2 * channels)
            self.out_lin2 = nn.Linear(2 * channels, out_dim)
            self.out_act = nn.SiLU(inplace=True)

    def forward(self, data: HeteroData) -> Tensor:
        x_lit = data["lit"].x
        h_lit = self.lit_enc(x_lit)

        x_cls = data["cls"].x
        h_cls = self.cls_enc(x_cls)

        for layer in self.layers:
            h_lit, h_cls = layer(h_lit, h_cls, data)

        if self.var_output:
            # concatenate interleaved embeddings and apply an mlp
            h_var = torch.cat([h_lit[0::2], h_lit[1::2]], dim=1)
            y_var = self.out_lin2(self.out_act(self.out_lin1(h_var)))
            return y_var
        else:
            y_lit = self.out_lin2(self.out_act(self.out_lin1(h_lit)))
            return y_lit


def init_transform(cfg: DictConfig | None = None) -> AddNodeFeatures:
    feature_set = "legacy"
    if cfg is not None and "model" in cfg and "feature_set" in cfg.model:
        feature_set = cfg.model.feature_set
    return AddNodeFeatures(feature_set=feature_set)


def init_model(cfg: DictConfig, transform: AddNodeFeatures, **model_kwargs) -> GNN:
    var_output = model_kwargs.get("var_output", True)
    if "out_dim" not in model_kwargs:
        if var_output:
            learnable_sigma = bool(cfg.model.learnable_sigma) if "learnable_sigma" in cfg.model else False
            model_kwargs["out_dim"] = 3 if learnable_sigma else 2
        else:
            model_kwargs["out_dim"] = 1

    model = GNN(
        channels=cfg.model.channels,
        lit_feat_dim=transform.lit_dim(),
        cls_feat_dim=transform.cls_dim(),
        num_layers=cfg.model.num_layers,
        aggr=OmegaConf.to_container(cfg.model.aggr),
        feature_encoder=cfg.model.feature_encoder,
        dropout=cfg.model.dropout if "dropout" in cfg.model else 0.0,
        separate_encoders=bool(cfg.model.separate_encoders) if "separate_encoders" in cfg.model else False,
        **model_kwargs,
    )
    return model


def load_checkpoint(ckpt_path: str, **model_kwargs) -> tuple[GNN, AddNodeFeatures, DictConfig]:
    cfg_path = os.path.join(os.path.dirname(ckpt_path), "config.yaml")
    cfg = OmegaConf.load(cfg_path)

    transform = init_transform(cfg)

    model = init_model(cfg, transform, **model_kwargs)

    state_dict = torch.load(ckpt_path)
    model.load_state_dict(state_dict)
    return model, transform, cfg
