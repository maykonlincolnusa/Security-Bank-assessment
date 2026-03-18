from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline


@dataclass
class ModelResult:
    name: str
    metrics: Dict[str, float]
    fold_metrics: List[Dict[str, float]]


def evaluate_model(pipeline: Pipeline, X, y, seed: int = 42, folds: int = 5) -> ModelResult:
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)

    fold_metrics: List[Dict[str, float]] = []
    rocs = []
    pras = []
    briers = []
    calibration_errors = []

    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        pipeline.fit(X_train, y_train)
        proba = _predict_proba(pipeline, X_test)

        roc = float(roc_auc_score(y_test, proba))
        pr = float(average_precision_score(y_test, proba))
        brier = float(brier_score_loss(y_test, proba))
        ece = float(expected_calibration_error(y_test.to_numpy(), proba, bins=10))

        rocs.append(roc)
        pras.append(pr)
        briers.append(brier)
        calibration_errors.append(ece)
        fold_metrics.append({"roc_auc": roc, "pr_auc": pr, "brier": brier, "ece": ece})

    return ModelResult(
        name=pipeline.named_steps.get("model", pipeline).__class__.__name__,
        metrics={
            "roc_auc": float(np.mean(rocs)),
            "pr_auc": float(np.mean(pras)),
            "brier": float(np.mean(briers)),
            "ece": float(np.mean(calibration_errors)),
        },
        fold_metrics=fold_metrics,
    )


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, bins: int = 10) -> float:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)

    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=bins, strategy="uniform")
    if len(frac_pos) == 0:
        return 0.0

    # Approximate per-bin weights with equal bins when using uniform strategy.
    bin_weight = 1.0 / len(frac_pos)
    return float(np.sum(np.abs(frac_pos - mean_pred) * bin_weight))


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
