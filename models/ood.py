from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class OODResult:
    score: np.ndarray
    threshold: float
    is_ood: np.ndarray


def mahalanobis_ood(train_matrix: np.ndarray, candidate_matrix: np.ndarray, q: float = 0.99) -> OODResult:
    train = np.asarray(train_matrix, dtype=float)
    cand = np.asarray(candidate_matrix, dtype=float)

    mu = train.mean(axis=0)
    cov = np.cov(train, rowvar=False)

    reg = 1e-6 * np.eye(cov.shape[0])
    inv_cov = np.linalg.pinv(cov + reg)

    train_dist = _mahalanobis(train, mu, inv_cov)
    cand_dist = _mahalanobis(cand, mu, inv_cov)

    threshold = float(np.quantile(train_dist, q))
    return OODResult(score=cand_dist, threshold=threshold, is_ood=cand_dist > threshold)


def odin_like_score(logits: np.ndarray, temperature: float = 1000.0) -> np.ndarray:
    """Lightweight ODIN-like confidence score from logits."""

    z = np.asarray(logits, dtype=float) / max(temperature, 1e-9)
    z = z - z.max(axis=1, keepdims=True)
    exp = np.exp(z)
    probs = exp / (exp.sum(axis=1, keepdims=True) + 1e-9)
    return probs.max(axis=1)


def density_autoencoder_stub(
    train_matrix: np.ndarray,
    candidate_matrix: np.ndarray,
    q: float = 0.99,
) -> OODResult:
    """Autoencoder-based OOD placeholder (non-neural reconstruction baseline).

    Uses PCA reconstruction error as a practical proxy where deep autoencoders
    are not available.
    """

    from sklearn.decomposition import PCA

    train = np.asarray(train_matrix, dtype=float)
    cand = np.asarray(candidate_matrix, dtype=float)

    n_comp = min(max(2, train.shape[1] // 2), train.shape[1])
    pca = PCA(n_components=n_comp, random_state=42)
    train_lat = pca.fit_transform(train)
    train_rec = pca.inverse_transform(train_lat)
    train_err = np.mean((train - train_rec) ** 2, axis=1)

    cand_lat = pca.transform(cand)
    cand_rec = pca.inverse_transform(cand_lat)
    cand_err = np.mean((cand - cand_rec) ** 2, axis=1)

    threshold = float(np.quantile(train_err, q))
    return OODResult(score=cand_err, threshold=threshold, is_ood=cand_err > threshold)


def _mahalanobis(X: np.ndarray, mu: np.ndarray, inv_cov: np.ndarray) -> np.ndarray:
    diff = X - mu
    left = diff @ inv_cov
    return np.sqrt(np.sum(left * diff, axis=1))


def to_frame(result: OODResult, prefix: str = "ood") -> pd.DataFrame:
    return pd.DataFrame(
        {
            f"{prefix}_score": result.score,
            f"{prefix}_threshold": result.threshold,
            f"{prefix}_flag": result.is_ood.astype(int),
        }
    )
