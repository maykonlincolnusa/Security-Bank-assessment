from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_dataset(rows: int = 400, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    bank_ids = np.array(["001", "033", "104", "237", "341"])
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")

    df = pd.DataFrame(
        {
            "bank_id": rng.choice(bank_ids, size=rows),
            "ref_date": rng.choice(dates, size=rows),
            "capital_ratio": rng.normal(0.14, 0.03, size=rows).clip(0.01, 0.6),
            "liquidity_ratio": rng.normal(1.3, 0.35, size=rows).clip(0.1, 6.0),
            "roe": rng.normal(0.09, 0.05, size=rows).clip(-0.2, 0.4),
            "npl_ratio": rng.normal(0.035, 0.015, size=rows).clip(0.0, 0.4),
            "solvency_ratio": rng.normal(0.16, 0.04, size=rows).clip(0.02, 0.7),
            "deposit_volatility": rng.normal(0.15, 0.06, size=rows).clip(0.0, 0.8),
            "asset_volatility": rng.normal(0.08, 0.03, size=rows).clip(0.0, 0.6),
            "warning_count": rng.poisson(0.8, size=rows),
            "penalty_count": rng.poisson(0.3, size=rows),
            "avg_sentiment": rng.normal(0.0, 0.7, size=rows).clip(-3, 3),
            "negative_volume": rng.integers(0, 45, size=rows),
            "search_spike_index": rng.normal(4.0, 2.0, size=rows).clip(0.0, 20.0),
            "security_incidents": rng.poisson(1.2, size=rows),
            "downtime_minutes": rng.normal(25.0, 20.0, size=rows).clip(0.0, 240.0),
        }
    )

    for i in range(8):
        df[f"news_emb_{i}"] = rng.normal(0.0, 1.0, size=rows)

    regulatory_risk = df["warning_count"] + 2.0 * df["penalty_count"]
    external_risk = (
        0.20 * (df["negative_volume"] / (df["negative_volume"].max() + 1e-9))
        + 0.20 * (df["search_spike_index"] / (df["search_spike_index"].max() + 1e-9))
        + 0.20 * (df["security_incidents"] / (df["security_incidents"].max() + 1e-9))
        - 0.20 * (df["avg_sentiment"] / (df["avg_sentiment"].abs().max() + 1e-9))
    )

    base_risk = (
        0.25 * df["npl_ratio"]
        + 0.20 * df["deposit_volatility"]
        + 0.10 * df["asset_volatility"]
        + 0.10 * (regulatory_risk / (regulatory_risk.max() + 1e-9))
        + 0.10 * (df["downtime_minutes"] / (df["downtime_minutes"].max() + 1e-9))
        + 0.25 * external_risk
        - 0.15 * df["capital_ratio"]
        - 0.10 * df["solvency_ratio"]
        - 0.10 * df["roe"]
    )

    df["risk_score"] = (base_risk - base_risk.min()) / (base_risk.max() - base_risk.min() + 1e-9)
    threshold = float(np.median(df["risk_score"]))
    df["trust_label"] = (df["risk_score"] < threshold).astype(int)

    return df
