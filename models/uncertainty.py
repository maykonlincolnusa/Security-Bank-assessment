from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

import numpy as np


try:
    import torch
except Exception:  # pragma: no cover
    torch = None


@dataclass(frozen=True)
class UncertaintyResult:
    mean: np.ndarray
    std: np.ndarray
    lower: np.ndarray
    upper: np.ndarray


def ensemble_predict_proba(models: Iterable[object], X) -> UncertaintyResult:
    preds = []
    for model in models:
        if hasattr(model, "predict_proba"):
            preds.append(model.predict_proba(X)[:, 1])
        elif hasattr(model, "decision_function"):
            scores = np.asarray(model.decision_function(X), dtype=float)
            preds.append((scores - scores.min()) / (scores.max() - scores.min() + 1e-9))

    if not preds:
        raise ValueError("No probabilistic predictions available")

    mat = np.vstack(preds)
    mean = mat.mean(axis=0)
    std = mat.std(axis=0)

    return UncertaintyResult(
        mean=mean,
        std=std,
        lower=np.clip(mean - 1.96 * std, 0.0, 1.0),
        upper=np.clip(mean + 1.96 * std, 0.0, 1.0),
    )


def mc_dropout_predict(
    model,
    x_tab,
    x_text,
    x_ts,
    n_passes: int = 30,
) -> UncertaintyResult:
    if torch is None:
        raise RuntimeError("PyTorch not installed")

    model.train()  # Keep dropout active for Monte Carlo passes.
    preds = []
    with torch.no_grad():
        for _ in range(n_passes):
            logits = model(x_tab, x_text, x_ts)
            preds.append(torch.sigmoid(logits).cpu().numpy().ravel())

    mat = np.vstack(preds)
    mean = mat.mean(axis=0)
    std = mat.std(axis=0)

    return UncertaintyResult(
        mean=mean,
        std=std,
        lower=np.clip(mean - 1.96 * std, 0.0, 1.0),
        upper=np.clip(mean + 1.96 * std, 0.0, 1.0),
    )


def quantile_interval(y_pred: np.ndarray, residuals: np.ndarray, alpha: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
    """Simple conformal-style interval from residual quantiles."""

    q = np.quantile(np.abs(residuals), 1 - alpha)
    lower = np.clip(y_pred - q, 0.0, 1.0)
    upper = np.clip(y_pred + q, 0.0, 1.0)
    return lower, upper
