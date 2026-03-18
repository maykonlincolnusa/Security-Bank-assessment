from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_dataset(rows: int = 800, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic banking risk dataset with tabular, temporal and text-proxy signals.

    No real sensitive data is used.
    """

    rng = np.random.default_rng(seed)

    bank_ids = np.array(["001", "033", "104", "237", "341", "748", "260"])
    regions = np.array(["sudeste", "sul", "nordeste", "norte", "centro-oeste"])
    profiles = np.array(["varejo", "corporate", "digital", "misto"])

    base_dates = pd.date_range("2023-01-01", periods=rows, freq="D")

    df = pd.DataFrame(
        {
            "bank_id": rng.choice(bank_ids, size=rows),
            "ref_date": rng.choice(base_dates, size=rows),
            "region": rng.choice(regions, size=rows),
            "client_profile": rng.choice(profiles, size=rows),
            "bank_size_cluster": rng.choice(["small", "mid", "large"], size=rows, p=[0.45, 0.4, 0.15]),
            "capital_ratio": rng.normal(0.15, 0.035, size=rows).clip(0.01, 0.7),
            "liquidity_ratio": rng.normal(1.4, 0.4, size=rows).clip(0.1, 8.0),
            "roe": rng.normal(0.10, 0.05, size=rows).clip(-0.3, 0.5),
            "npl_ratio": rng.normal(0.04, 0.02, size=rows).clip(0.0, 0.6),
            "npa_to_assets_ratio": rng.normal(0.02, 0.01, size=rows).clip(0.0, 0.4),
            "deposit_volatility": rng.normal(0.14, 0.07, size=rows).clip(0.0, 1.2),
            "asset_volatility": rng.normal(0.09, 0.04, size=rows).clip(0.0, 0.9),
            "warning_count": rng.poisson(0.9, size=rows),
            "penalty_count": rng.poisson(0.25, size=rows),
            "avg_sentiment": rng.normal(0.0, 0.8, size=rows).clip(-3, 3),
            "negative_volume": rng.integers(0, 70, size=rows),
            "search_spike_index": rng.normal(5.0, 2.5, size=rows).clip(0.0, 30.0),
            "security_incidents": rng.poisson(1.4, size=rows),
            "downtime_minutes": rng.normal(20.0, 18.0, size=rows).clip(0.0, 360.0),
            "tx_latency_ms": rng.normal(180, 55, size=rows).clip(20, 1500),
            "news_text": rng.choice(
                [
                    "instituicao com resultados solidos e governanca reforcada",
                    "alerta regulatorio e investigacao em andamento",
                    "crescimento de clientes e estabilidade operacional",
                    "incidente cibernetico reportado e indisponibilidade parcial",
                    "melhora de liquidez e reforco de capital",
                ],
                size=rows,
            ),
        }
    )

    for i in range(16):
        df[f"news_emb_{i}"] = rng.normal(0.0, 1.0, size=rows)

    df = df.sort_values(["bank_id", "ref_date"]).reset_index(drop=True)

    df["regulatory_risk"] = df["warning_count"] + 2.0 * df["penalty_count"]

    for col in ["npl_ratio", "deposit_volatility", "security_incidents", "downtime_minutes", "avg_sentiment"]:
        df[f"{col}_lag_1"] = df.groupby("bank_id")[col].shift(1)

    for window in [7, 30, 90]:
        df[f"npl_ratio_mean_{window}d"] = df.groupby("bank_id")["npl_ratio"].transform(
            lambda x, w=window: x.rolling(w, min_periods=2).mean()
        )
        df[f"deposit_volatility_std_{window}d"] = df.groupby("bank_id")["deposit_volatility"].transform(
            lambda x, w=window: x.rolling(w, min_periods=2).std()
        )

    risk_signal = (
        0.22 * df["npl_ratio"]
        + 0.17 * df["deposit_volatility"]
        + 0.10 * df["asset_volatility"]
        + 0.13 * (df["regulatory_risk"] / (df["regulatory_risk"].max() + 1e-9))
        + 0.10 * (df["negative_volume"] / (df["negative_volume"].max() + 1e-9))
        + 0.10 * (df["security_incidents"] / (df["security_incidents"].max() + 1e-9))
        + 0.08 * (df["downtime_minutes"] / (df["downtime_minutes"].max() + 1e-9))
        + 0.05 * (df["tx_latency_ms"] / (df["tx_latency_ms"].max() + 1e-9))
        - 0.08 * df["capital_ratio"]
        - 0.07 * df["liquidity_ratio"]
        - 0.07 * df["roe"]
        - 0.05 * (df["avg_sentiment"] / (df["avg_sentiment"].abs().max() + 1e-9))
    )

    risk_signal = risk_signal.fillna(risk_signal.median())
    df["risk_score"] = (risk_signal - risk_signal.min()) / (risk_signal.max() - risk_signal.min() + 1e-9)

    threshold = float(df["risk_score"].median())
    df["trust_label"] = (df["risk_score"] < threshold).astype(int)
    df["trust_score"] = (1.0 - df["risk_score"]) * 100.0
    df["risk_class"] = pd.cut(
        df["trust_score"],
        bins=[-1, 40, 70, 101],
        labels=["alto", "medio", "baixo"],
    ).astype(str)

    # Inject missing values to benchmark imputation strategies.
    for col, frac in {
        "roe": 0.08,
        "liquidity_ratio": 0.06,
        "avg_sentiment": 0.10,
        "tx_latency_ms": 0.12,
    }.items():
        mask = rng.random(rows) < frac
        df.loc[mask, col] = np.nan

    return df
