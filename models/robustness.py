from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd


@dataclass
class StabilityResult:
    baseline_mean: float
    perturbed_mean: float
    abs_delta_mean: float
    pct_large_delta: float


def perturb_tabular_features(
    X: pd.DataFrame,
    sensitive_cols: Iterable[str],
    pct: float = 0.05,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    pert = X.copy()

    for col in sensitive_cols:
        if col not in pert.columns:
            continue
        if not pd.api.types.is_numeric_dtype(pert[col]):
            continue

        noise = rng.uniform(-pct, pct, size=len(pert))
        base = pd.to_numeric(pert[col], errors="coerce").fillna(0.0)
        pert[col] = base * (1.0 + noise)

    return pert


def perturb_text_noise(texts: pd.Series) -> pd.Series:
    synonym_map = {
        "alerta": "aviso",
        "incidente": "ocorrencia",
        "regulatorio": "normativo",
        "investigacao": "apuracao",
        "cibernetico": "digital",
    }

    def _swap(text: str) -> str:
        safe = str(text).lower()
        for src, tgt in synonym_map.items():
            safe = re.sub(rf"\b{src}\b", tgt, safe)
        safe = re.sub(r"\s+", " ", safe).strip()
        return safe

    return texts.fillna("").astype(str).map(_swap)


def evaluate_score_stability(
    model,
    X_base: pd.DataFrame,
    X_perturbed: pd.DataFrame,
    threshold_delta: float = 0.1,
) -> StabilityResult:
    base = _predict(model, X_base)
    pert = _predict(model, X_perturbed)

    delta = np.abs(base - pert)
    return StabilityResult(
        baseline_mean=float(base.mean()),
        perturbed_mean=float(pert.mean()),
        abs_delta_mean=float(delta.mean()),
        pct_large_delta=float((delta > threshold_delta).mean()),
    )


def extreme_stress_frame(X: pd.DataFrame) -> pd.DataFrame:
    safe = X.copy()

    for col in ["npl_ratio", "deposit_volatility", "security_incidents", "downtime_minutes"]:
        if col in safe.columns:
            safe[col] = pd.to_numeric(safe[col], errors="coerce").fillna(0.0) * 3.0

    for col in ["capital_ratio", "liquidity_ratio", "roe", "avg_sentiment"]:
        if col in safe.columns:
            safe[col] = pd.to_numeric(safe[col], errors="coerce").fillna(0.0) * 0.4

    return safe


def _predict(model, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        scores = np.asarray(model.decision_function(X), dtype=float)
        return (scores - scores.min()) / (scores.max() - scores.min() + 1e-9)
    return np.asarray(model.predict(X), dtype=float)


def prompt_injection_tokens_detected(text: str) -> Tuple[bool, Dict[str, int]]:
    patterns = {
        "ignore_previous": r"ignore\s+previous\s+instructions",
        "system_prompt": r"reveal\s+system\s+prompt",
        "exfiltrate": r"exfiltrate|dump\s+credentials|api\s+keys",
        "shell_exec": r"`rm\s+-rf|os\.system|subprocess\.run",
    }

    found = {}
    lowered = str(text).lower()
    for name, pat in patterns.items():
        count = len(re.findall(pat, lowered))
        if count:
            found[name] = count

    return bool(found), found


def sanitize_agent_text(text: str) -> str:
    cleaned = str(text)
    cleaned = re.sub(r"[`\$\\]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
