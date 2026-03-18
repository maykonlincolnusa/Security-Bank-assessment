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

try:
    from transformers import AutoModel, AutoTokenizer
except Exception:  # pragma: no cover
    AutoModel = None
    AutoTokenizer = None


@dataclass
class MultimodalConfig:
    text_model_name: str = "distilbert-base-uncased"
    text_embedding_dim: int = 64
    tabular_hidden_dim: int = 64
    ts_hidden_dim: int = 32
    epochs: int = 15
    batch_size: int = 64
    lr: float = 1e-3
    device: str = "cpu"


if nn is not None:
    class MultimodalTrustNet(nn.Module):
        def __init__(self, tab_dim: int, text_dim: int, ts_dim: int, cfg: MultimodalConfig):
            super().__init__()
            self.tab_branch = nn.Sequential(
                nn.Linear(tab_dim, cfg.tabular_hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.text_branch = nn.Sequential(
                nn.Linear(text_dim, cfg.text_embedding_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.ts_branch = nn.Sequential(
                nn.Linear(ts_dim, cfg.ts_hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.head = nn.Sequential(
                nn.Linear(cfg.tabular_hidden_dim + cfg.text_embedding_dim + cfg.ts_hidden_dim, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
            )

        def forward(self, x_tab, x_text, x_ts):
            h_tab = self.tab_branch(x_tab)
            h_txt = self.text_branch(x_text)
            h_ts = self.ts_branch(x_ts)
            h = torch.cat([h_tab, h_txt, h_ts], dim=1)
            return self.head(h)
else:
    class MultimodalTrustNet:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch not installed")


def build_text_embeddings(texts: pd.Series, cfg: MultimodalConfig) -> np.ndarray:
    values = texts.fillna("").astype(str).tolist()

    if AutoTokenizer is None or AutoModel is None:
        return _hash_embeddings(values, dim=cfg.text_embedding_dim)

    try:
        tokenizer = AutoTokenizer.from_pretrained(cfg.text_model_name)
        model = AutoModel.from_pretrained(cfg.text_model_name)
        model.eval()

        embeddings = []
        with torch.no_grad():
            for text in values:
                tokens = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
                output = model(**tokens)
                vec = output.last_hidden_state.mean(dim=1).numpy().ravel()
                embeddings.append(vec)

        emb = np.asarray(embeddings)
        if emb.shape[1] > cfg.text_embedding_dim:
            emb = emb[:, : cfg.text_embedding_dim]
        elif emb.shape[1] < cfg.text_embedding_dim:
            pad = np.zeros((emb.shape[0], cfg.text_embedding_dim - emb.shape[1]))
            emb = np.hstack([emb, pad])
        return emb
    except Exception:
        return _hash_embeddings(values, dim=cfg.text_embedding_dim)


def split_multimodal_inputs(
    X: pd.DataFrame,
    text_col: str = "news_text",
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    text = X[text_col] if text_col in X.columns else pd.Series([""] * len(X))

    ts_cols = [
        col
        for col in X.columns
        if "_lag_" in col or col.endswith("_mean_7d") or col.endswith("_std_7d")
    ]
    if not ts_cols:
        ts_cols = [c for c in X.columns if c.startswith("news_emb_")][:8]

    ts = X[ts_cols].copy() if ts_cols else pd.DataFrame(np.zeros((len(X), 1)), columns=["ts_0"])
    tab = X.drop(columns=[c for c in [text_col] + ts_cols if c in X.columns], errors="ignore")
    tab = tab.select_dtypes(include=[np.number]).fillna(0.0)
    ts = ts.select_dtypes(include=[np.number]).fillna(0.0)

    if tab.empty:
        tab = pd.DataFrame(np.zeros((len(X), 1)), columns=["tab_0"])
    if ts.empty:
        ts = pd.DataFrame(np.zeros((len(X), 1)), columns=["ts_0"])

    return tab, text, ts


def train_multimodal_model(
    X: pd.DataFrame,
    y: pd.Series,
    cfg: MultimodalConfig,
) -> Tuple[object, float]:
    if torch is None:
        raise RuntimeError("PyTorch not installed")

    x_tab_df, text_series, x_ts_df = split_multimodal_inputs(X)
    x_text = build_text_embeddings(text_series, cfg)

    x_tab = torch.tensor(x_tab_df.to_numpy(dtype=np.float32))
    x_text_t = torch.tensor(x_text.astype(np.float32))
    x_ts = torch.tensor(x_ts_df.to_numpy(dtype=np.float32))
    y_t = torch.tensor(y.to_numpy(dtype=np.float32).reshape(-1, 1))

    ds = TensorDataset(x_tab, x_text_t, x_ts, y_t)
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True)

    model = MultimodalTrustNet(x_tab.shape[1], x_text_t.shape[1], x_ts.shape[1], cfg)
    model.to(cfg.device)

    optim = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    for _ in range(cfg.epochs):
        for b_tab, b_text, b_ts, b_y in dl:
            b_tab = b_tab.to(cfg.device)
            b_text = b_text.to(cfg.device)
            b_ts = b_ts.to(cfg.device)
            b_y = b_y.to(cfg.device)

            optim.zero_grad()
            logits = model(b_tab, b_text, b_ts)
            loss = loss_fn(logits, b_y)
            loss.backward()
            optim.step()

    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(x_tab.to(cfg.device), x_text_t.to(cfg.device), x_ts.to(cfg.device))).cpu().numpy().ravel()

    return model, float(np.mean(probs))


def predict_multimodal_proba(model, X: pd.DataFrame, cfg: MultimodalConfig) -> np.ndarray:
    if torch is None:
        raise RuntimeError("PyTorch not installed")

    x_tab_df, text_series, x_ts_df = split_multimodal_inputs(X)
    x_text = build_text_embeddings(text_series, cfg)

    with torch.no_grad():
        logits = model(
            torch.tensor(x_tab_df.to_numpy(dtype=np.float32)).to(cfg.device),
            torch.tensor(x_text.astype(np.float32)).to(cfg.device),
            torch.tensor(x_ts_df.to_numpy(dtype=np.float32)).to(cfg.device),
        )
        return torch.sigmoid(logits).cpu().numpy().ravel()


def _hash_embeddings(texts: list[str], dim: int = 64) -> np.ndarray:
    emb = np.zeros((len(texts), dim), dtype=np.float32)
    for i, text in enumerate(texts):
        for token in text.split():
            idx = abs(hash(token)) % dim
            emb[i, idx] += 1.0
        norm = np.linalg.norm(emb[i]) + 1e-9
        emb[i] /= norm
    return emb
