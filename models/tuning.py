from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np

from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline


try:
    import optuna
except Exception:  # pragma: no cover
    optuna = None


@dataclass
class OptunaConfig:
    enabled: bool = False
    trials: int = 30
    timeout_sec: Optional[int] = None


def _sample_xgboost_params(trial) -> Dict[str, float]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 200, 800),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
    }


def _sample_lightgbm_params(trial) -> Dict[str, float]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
    }


def optimize_tree_model(
    model_name: str,
    base_pipeline_builder: Callable[[], Pipeline],
    estimator_builder: Callable[[Dict[str, float]], object],
    X_train,
    y_train,
    X_valid,
    y_valid,
    config: OptunaConfig,
) -> Dict[str, float]:
    if not config.enabled or optuna is None:
        return {}

    sampler_map = {
        "xgboost": _sample_xgboost_params,
        "lightgbm": _sample_lightgbm_params,
        "catboost": _sample_lightgbm_params,
    }
    sampler = sampler_map.get(model_name)
    if sampler is None:
        return {}

    def objective(trial) -> float:
        params = sampler(trial)
        estimator = estimator_builder(params)
        pipeline = base_pipeline_builder()
        pipeline.steps.append(("model", estimator))

        pipeline.fit(X_train, y_train)

        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba(X_valid)[:, 1]
        else:
            scores = np.asarray(pipeline.decision_function(X_valid), dtype=float)
            proba = (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)

        return float(roc_auc_score(y_valid, proba))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=config.trials, timeout=config.timeout_sec)
    return dict(study.best_params)
