from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except Exception:  # pragma: no cover
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None


@dataclass
class TorchConfig:
    tabular_hidden_dim: int = 64
    embedding_hidden_dim: int = 32
    epochs: int = 25
    lr: float = 1e-3
    batch_size: int = 64


if nn is not None:
    class TabularTextNet(nn.Module):
        def __init__(self, tabular_dim: int, emb_dim: int, config: TorchConfig):
            super().__init__()
            self.tabular_branch = nn.Sequential(
                nn.Linear(tabular_dim, config.tabular_hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.embedding_branch = nn.Sequential(
                nn.Linear(emb_dim, config.embedding_hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.head = nn.Sequential(
                nn.Linear(config.tabular_hidden_dim + config.embedding_hidden_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
            )

        def forward(self, x_tab, x_emb):
            t = self.tabular_branch(x_tab)
            e = self.embedding_branch(x_emb)
            return self.head(torch.cat([t, e], dim=1))
else:
    class TabularTextNet:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch not installed")


def split_tabular_embedding_features(X: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    emb_cols = [c for c in X.columns if c.startswith("news_emb_")]
    if not emb_cols:
        emb = pd.DataFrame(np.zeros((len(X), 1)), columns=["news_emb_0"])
        tab = X.copy()
    else:
        emb = X[emb_cols].copy()
        tab = X.drop(columns=emb_cols).copy()

    tab = tab.select_dtypes(include=[np.number]).fillna(0.0)
    emb = emb.select_dtypes(include=[np.number]).fillna(0.0)
    return tab, emb


def train_torch_grouped(X: pd.DataFrame, y: pd.Series, config: TorchConfig) -> Tuple[object, float]:
    if torch is None:
        raise RuntimeError("PyTorch not installed")

    X_tab, X_emb = split_tabular_embedding_features(X)
    y_np = y.to_numpy(dtype=np.float32).reshape(-1, 1)

    ds = TensorDataset(
        torch.tensor(X_tab.to_numpy(dtype=np.float32)),
        torch.tensor(X_emb.to_numpy(dtype=np.float32)),
        torch.tensor(y_np),
    )
    loader = DataLoader(ds, batch_size=config.batch_size, shuffle=True)

    model = TabularTextNet(X_tab.shape[1], X_emb.shape[1], config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr)
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    for _ in range(config.epochs):
        for xb_tab, xb_emb, yb in loader:
            optimizer.zero_grad()
            logits = model(xb_tab, xb_emb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        logits = model(
            torch.tensor(X_tab.to_numpy(dtype=np.float32)),
            torch.tensor(X_emb.to_numpy(dtype=np.float32)),
        )
        probs = torch.sigmoid(logits).numpy().ravel()

    return model, float(np.mean(probs))
