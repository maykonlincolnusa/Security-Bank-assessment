from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline


@dataclass
class ModelResult:
    name: str
    metrics: Dict[str, float]
    fold_metrics: List[Dict[str, float]]


def evaluate_model(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    seed: int = 42,
    folds: int = 5,
    splitter: Optional[Sequence] = None,
    cost_matrix: Optional[Dict[str, float]] = None,
) -> ModelResult:
    if splitter is None:
        splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed).split(X, y)

    fold_metrics: List[Dict[str, float]] = []

    for train_idx, test_idx in splitter:
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        pipeline.fit(X_train, y_train)
        proba = _predict_proba(pipeline, X_test)
        metrics = compute_binary_metrics(y_test.to_numpy(), proba, cost_matrix=cost_matrix)
        fold_metrics.append(metrics)

    avg_metrics = {
        key: float(np.mean([fold[key] for fold in fold_metrics])) for key in fold_metrics[0].keys()
    }

    return ModelResult(
        name=pipeline.named_steps.get("model", pipeline).__class__.__name__,
        metrics=avg_metrics,
        fold_metrics=fold_metrics,
    )


def compute_binary_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    bins: int = 10,
    cost_matrix: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)

    roc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    pr = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else float(y_true.mean())
    brier = float(brier_score_loss(y_true, y_prob))
    ece = float(expected_calibration_error(y_true, y_prob, bins=bins))

    custom_cost = expected_cost(y_true, y_prob >= threshold, cost_matrix)

    return {
        "roc_auc": roc,
        "pr_auc": pr,
        "brier": brier,
        "ece": ece,
        "custom_cost": custom_cost,
    }


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 10) -> float:
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=bins, strategy="uniform")
    if len(frac_pos) == 0:
        return 0.0
    bin_weight = 1.0 / len(frac_pos)
    return float(np.sum(np.abs(frac_pos - mean_pred) * bin_weight))


def reliability_curve_data(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 10) -> pd.DataFrame:
    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=bins, strategy="uniform")
    return pd.DataFrame({"mean_pred": mean_pred, "frac_pos": frac_pos})


def expected_cost(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cost_matrix: Optional[Dict[str, float]] = None,
) -> float:
    costs = {
        "tp": 0.0,
        "tn": 0.0,
        "fp": 1.0,
        "fn": 5.0,
    }
    if cost_matrix:
        costs.update(cost_matrix)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    total = tp + tn + fp + fn
    if total == 0:
        return 0.0

    weighted = tp * costs["tp"] + tn * costs["tn"] + fp * costs["fp"] + fn * costs["fn"]
    return float(weighted / total)


def probability_to_trust_score(y_prob: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(y_prob, dtype=float) * 100.0, 0.0, 100.0)


def classify_risk(trust_score: float) -> str:
    if trust_score >= 70:
        return "baixo"
    if trust_score >= 40:
        return "medio"
    return "alto"


def add_score_columns(df: pd.DataFrame, prob_col: str = "score_prob") -> pd.DataFrame:
    safe = df.copy()
    safe["trust_score"] = probability_to_trust_score(safe[prob_col].to_numpy())
    safe["risk_class"] = safe["trust_score"].map(classify_risk)
    return safe


def save_metrics(results: List[ModelResult], output_dir: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    payload = {
        r.name: {
            "metrics": r.metrics,
            "fold_metrics": r.fold_metrics,
        }
        for r in results
    }
    path = Path(output_dir) / "metrics.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def _predict_proba(pipeline: Pipeline, X):
    if hasattr(pipeline, "predict_proba"):
        return pipeline.predict_proba(X)[:, 1]
    if hasattr(pipeline, "decision_function"):
        scores = pipeline.decision_function(X)
        return (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
    pred = pipeline.predict(X)
    return np.asarray(pred, dtype=float)
