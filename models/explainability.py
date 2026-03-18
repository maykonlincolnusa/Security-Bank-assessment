from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


try:
    import shap
except Exception:  # pragma: no cover
    shap = None

try:
    from lime.lime_tabular import LimeTabularExplainer
except Exception:  # pragma: no cover
    LimeTabularExplainer = None


@dataclass
class ExplanationBundle:
    shap_values: Optional[Any]
    shap_summary: pd.DataFrame
    lime_explanation: Dict[str, float]
    counterfactual: Dict[str, float]


def generate_explanations(
    model,
    X_train: pd.DataFrame,
    instance: pd.Series,
    top_k: int = 10,
) -> ExplanationBundle:
    shap_values, shap_df = shap_summary(model, X_train, top_k=top_k)
    lime_dict = lime_explain_instance(model, X_train, instance)
    cf = generate_counterfactual(model, instance, desired_class=1)

    return ExplanationBundle(
        shap_values=shap_values,
        shap_summary=shap_df,
        lime_explanation=lime_dict,
        counterfactual=cf,
    )


def shap_summary(model, X: pd.DataFrame, top_k: int = 10):
    if shap is None:
        return None, pd.DataFrame(columns=["feature", "importance"])

    sample = X.head(min(300, len(X))).copy()
    try:
        explainer = shap.Explainer(model.predict_proba if hasattr(model, "predict_proba") else model, sample)
        values = explainer(sample)
        raw = values.values
        if raw.ndim == 3:  # multiclass shape
            raw = raw[:, :, -1]
        mean_abs = np.abs(raw).mean(axis=0)
        out = pd.DataFrame({"feature": sample.columns, "importance": mean_abs})
        out = out.sort_values("importance", ascending=False).head(top_k).reset_index(drop=True)
        return values, out
    except Exception:
        return None, pd.DataFrame(columns=["feature", "importance"])


def lime_explain_instance(model, X_train: pd.DataFrame, instance: pd.Series, top_k: int = 10) -> Dict[str, float]:
    if LimeTabularExplainer is None:
        return {}

    numeric = X_train.select_dtypes(include=[np.number]).copy()
    if numeric.empty:
        return {}

    inst = pd.to_numeric(instance.reindex(numeric.columns), errors="coerce").fillna(0.0).to_numpy()

    explainer = LimeTabularExplainer(
        training_data=numeric.to_numpy(),
        feature_names=numeric.columns.tolist(),
        mode="classification",
    )

    def predict_fn(data):
        frame = pd.DataFrame(data, columns=numeric.columns)
        return model.predict_proba(_merge_like(X_train, frame))

    exp = explainer.explain_instance(inst, predict_fn, num_features=min(top_k, len(numeric.columns)))
    return {k: float(v) for k, v in exp.as_list()}


def generate_counterfactual(
    model,
    instance: pd.Series,
    desired_class: int = 1,
    step: float = 0.05,
    max_iter: int = 80,
) -> Dict[str, float]:
    """Greedy counterfactual search for numeric features.

    This is a practical deterministic baseline for auditability.
    """

    x = instance.copy()
    numeric_cols = [c for c in x.index if pd.api.types.is_numeric_dtype(type(x[c])) or isinstance(x[c], (int, float, np.number))]
    if not numeric_cols:
        return {}

    current = _predict_single(model, x)
    target_hit = (current >= 0.5) if desired_class == 1 else (current < 0.5)
    if target_hit:
        return {col: float(pd.to_numeric(x[col], errors="coerce")) for col in numeric_cols}

    direction = 1 if desired_class == 1 else -1

    for _ in range(max_iter):
        # Move selected features according to risk logic.
        for col in numeric_cols:
            val = float(pd.to_numeric(x[col], errors="coerce") if pd.notna(x[col]) else 0.0)
            if col in {"capital_ratio", "liquidity_ratio", "roe", "avg_sentiment"}:
                x[col] = val + direction * step * max(1.0, abs(val))
            else:
                x[col] = val - direction * step * max(1.0, abs(val))

        current = _predict_single(model, x)
        target_hit = (current >= 0.5) if desired_class == 1 else (current < 0.5)
        if target_hit:
            break

    return {col: float(pd.to_numeric(x[col], errors="coerce")) for col in numeric_cols}


def _predict_single(model, row: pd.Series) -> float:
    frame = pd.DataFrame([row.to_dict()])
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(frame)[:, 1][0])
    if hasattr(model, "decision_function"):
        score = float(model.decision_function(frame)[0])
        return float(1.0 / (1.0 + np.exp(-score)))
    return float(model.predict(frame)[0])


def _merge_like(template: pd.DataFrame, numeric_part: pd.DataFrame) -> pd.DataFrame:
    """Recreate full frame expected by model using template schema.

    Non-numeric columns are filled with mode from training frame.
    """

    out = pd.DataFrame(index=numeric_part.index)
    for col in template.columns:
        if col in numeric_part.columns:
            out[col] = numeric_part[col]
        elif pd.api.types.is_numeric_dtype(template[col]):
            out[col] = float(pd.to_numeric(template[col], errors="coerce").median())
        else:
            out[col] = template[col].mode().iloc[0] if not template[col].mode().empty else "unknown"
    return out[template.columns]
