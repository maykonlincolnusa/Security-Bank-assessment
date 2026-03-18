from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from .metrics import ModelResult, evaluate_model, save_metrics
from .preprocess import build_preprocess_pipeline, split_xy


try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None


def train_baselines(
    df: pd.DataFrame,
    target_col: str,
    output_dir: str,
    seed: int = 42,
) -> Tuple[list[ModelResult], str, str]:
    base_pipeline, _ = build_preprocess_pipeline(df, target_col)
    X, y = split_xy(df, target_col)

    candidates: Dict[str, object] = {
        "logistic_regression": LogisticRegression(max_iter=400, random_state=seed),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1),
    }
    if XGBClassifier is not None:
        candidates["xgboost"] = XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=seed,
            eval_metric="logloss",
        )

    results: list[ModelResult] = []
    trained_pipelines: Dict[str, object] = {}

    for name, estimator in candidates.items():
        pipeline = clone(base_pipeline)
        pipeline.steps.append(("model", estimator))
        result = evaluate_model(pipeline, X, y, seed=seed)
        result.name = name
        results.append(result)

        # Fit full data for model registry/export.
        pipeline.fit(X, y)
        trained_pipelines[name] = pipeline

    metrics_path = save_metrics(results, output_dir)

    best_result = max(results, key=lambda r: r.metrics["roc_auc"])
    best_pipeline = trained_pipelines[best_result.name]

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model_path = Path(output_dir) / "best_model.joblib"
    joblib.dump(best_pipeline, model_path)

    return results, metrics_path, str(model_path)
