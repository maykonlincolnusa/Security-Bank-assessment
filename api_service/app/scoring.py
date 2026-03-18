from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import onnxruntime as ort


@dataclass
class ModelArtifacts:
    session: ort.InferenceSession | None
    input_names: List[str]
    feature_names: List[str]
    feature_importance: Dict[str, float]


def load_model(onnx_path: str, features_path: str, importance_path: str = "") -> ModelArtifacts:
    onnx_file = Path(onnx_path)
    features_file = Path(features_path)
    if onnx_file.exists() and features_file.exists():
        session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        input_names = [i.name for i in session.get_inputs()]
        feature_names = json.loads(features_file.read_text())
    else:
        session = None
        input_names = ["features"]
        feature_names = _default_feature_names()

    importance = {}
    if importance_path and Path(importance_path).exists():
        importance = json.loads(Path(importance_path).read_text())
    return ModelArtifacts(
        session=session,
        input_names=input_names,
        feature_names=feature_names,
        feature_importance=importance,
    )


def score_features(artifacts: ModelArtifacts, features: Dict[str, float]) -> float:
    if artifacts.session is None:
        return _heuristic_score(features, artifacts.feature_names)

    feed = _to_feed_dict(artifacts, features)
    outputs = artifacts.session.run(None, feed)
    # If model returns probabilities, use positive class as trust score.
    if len(outputs) > 1:
        out = np.asarray(outputs[1])
        if out.ndim == 2 and out.shape[1] >= 2:
            return float(out[0, 1])
    return float(np.ravel(outputs[0])[0])


def explain_features(artifacts: ModelArtifacts, features: Dict[str, float], top_k: int = 5) -> Dict[str, float]:
    if artifacts.feature_importance:
        scored = {
            name: abs(features.get(name, 0.0)) * abs(artifacts.feature_importance.get(name, 0.0))
            for name in artifacts.feature_names
        }
    else:
        scored = {name: abs(features.get(name, 0.0)) for name in artifacts.feature_names}
    top = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return {k: float(v) for k, v in top}


def _to_feed_dict(artifacts: ModelArtifacts, features: Dict[str, float]) -> Dict[str, np.ndarray]:
    if len(artifacts.input_names) == 1:
        vector = [float(features.get(name, 0.0)) for name in artifacts.feature_names]
        return {artifacts.input_names[0]: np.array([vector], dtype=np.float32)}

    feed: Dict[str, np.ndarray] = {}
    for input_name in artifacts.input_names:
        value = features.get(input_name)
        if isinstance(value, str):
            feed[input_name] = np.array([[value]], dtype=object)
        else:
            feed[input_name] = np.array([[0.0 if value is None else float(value)]], dtype=np.float32)
    return feed


def _default_feature_names() -> List[str]:
    return [
        "capital_ratio",
        "liquidity_ratio",
        "roe",
        "npl_ratio",
        "deposit_volatility",
        "avg_sentiment",
        "negative_volume",
        "security_incidents",
    ]


def _heuristic_score(features: Dict[str, float], feature_names: List[str]) -> float:
    signal = 0.0
    for name in feature_names:
        value = float(features.get(name, 0.0))
        if name in {"capital_ratio", "liquidity_ratio", "roe", "avg_sentiment"}:
            signal += value
        else:
            signal -= value
    return 1.0 / (1.0 + math.exp(-signal))
