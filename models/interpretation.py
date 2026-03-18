from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def get_feature_names(preprocessor: ColumnTransformer) -> List[str]:
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        names = []
        for name, _, cols in preprocessor.transformers_:
            if name == "remainder":
                continue
            if isinstance(cols, list):
                names.extend([f"{name}__{c}" for c in cols])
        return names


def feature_importance(model, feature_names: List[str]) -> Optional[pd.Series]:
    if hasattr(model, "coef_"):
        coef = np.ravel(model.coef_)
        return pd.Series(coef, index=feature_names).abs().sort_values(ascending=False)
    if hasattr(model, "feature_importances_"):
        return pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)
    return None


def example_interpretations(pipeline: Pipeline, X: pd.DataFrame, n: int = 3) -> List[dict]:
    if not isinstance(pipeline, Pipeline) or "model" not in pipeline.named_steps:
        return []
    model = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["preprocess"]
    if not isinstance(model, LogisticRegression):
        return []

    X_transformed = preprocessor.transform(X)
    feature_names = get_feature_names(preprocessor)
    coefs = np.ravel(model.coef_)

    samples = []
    for idx in range(min(n, X.shape[0])):
        row = X_transformed[idx].toarray().ravel() if hasattr(X_transformed, "toarray") else X_transformed[idx]
        contributions = row * coefs
        top_idx = np.argsort(np.abs(contributions))[-5:][::-1]
        top_features = {feature_names[i]: float(contributions[i]) for i in top_idx}
        score = float(pipeline.predict_proba(X.iloc[[idx]])[:, 1][0])
        samples.append({"score": score, "top_contributions": top_features})
    return samples
