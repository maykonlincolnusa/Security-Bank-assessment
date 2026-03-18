from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class FeatureConfig:
    id_col: str = "bank_id"
    date_col: str = "ref_date"
    rolling_windows: tuple[int, ...] = (7, 30, 90, 365)


def build_feature_table(tables: Dict[str, pd.DataFrame], config: FeatureConfig) -> pd.DataFrame:
    base = _build_base_index(tables, config)
    if base.empty:
        return base

    frames = [
        base,
        _features_financials(tables.get("financial_statements", pd.DataFrame()), config),
        _features_open_banking(tables.get("open_banking_balances", pd.DataFrame()), config),
        _features_regulatory(tables.get("regulatory_events", pd.DataFrame()), config),
        _features_news(tables.get("news_sentiment_daily", pd.DataFrame()), config),
        _features_security(tables.get("security_cve_daily", pd.DataFrame()), config),
        _features_operational(tables.get("operational_telemetry", pd.DataFrame()), config),
        _features_macro(tables.get("macro_series", pd.DataFrame()), config),
    ]

    result = _merge_features(frames, config)
    result = result.sort_values([config.id_col, config.date_col]).reset_index(drop=True)

    result = _add_temporal_statistics(result, config)
    if "risk_score" not in result.columns:
        result["risk_score"] = _derive_risk_score(result)
    if "trust_label" not in result.columns:
        # Lower risk -> positive trust label.
        threshold = float(result["risk_score"].median()) if not result.empty else 0.5
        result["trust_label"] = (result["risk_score"] <= threshold).astype(int)

    return result


def _build_base_index(tables: Dict[str, pd.DataFrame], config: FeatureConfig) -> pd.DataFrame:
    candidates: List[pd.DataFrame] = []
    for name in [
        "open_banking_accounts",
        "open_banking_balances",
        "financial_statements",
        "regulatory_events",
        "operational_telemetry",
    ]:
        df = tables.get(name, pd.DataFrame())
        if df.empty or config.id_col not in df.columns:
            continue

        temp = pd.DataFrame({
            config.id_col: df[config.id_col],
            config.date_col: _resolve_date_column(df, config),
        })
        candidates.append(temp.dropna().drop_duplicates())

    if not candidates:
        return pd.DataFrame()

    return pd.concat(candidates, ignore_index=True).drop_duplicates()


def _merge_features(frames: List[pd.DataFrame], config: FeatureConfig) -> pd.DataFrame:
    result = frames[0]
    for frame in frames[1:]:
        if frame.empty:
            continue

        if config.id_col in frame.columns and config.id_col in result.columns:
            join_keys = [config.id_col, config.date_col]
        else:
            join_keys = [config.date_col]

        join_keys = [k for k in join_keys if k in frame.columns and k in result.columns]
        if not join_keys:
            continue

        result = result.merge(frame, on=join_keys, how="left")

    return result


def _features_financials(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    assets = pd.to_numeric(safe.get("total_assets"), errors="coerce")
    liabilities = pd.to_numeric(safe.get("total_liabilities"), errors="coerce")
    current_assets = pd.to_numeric(safe.get("current_assets"), errors="coerce")
    current_liabilities = pd.to_numeric(safe.get("current_liabilities"), errors="coerce")
    equity = pd.to_numeric(safe.get("equity"), errors="coerce")
    net_income = pd.to_numeric(safe.get("net_income"), errors="coerce")
    npl = pd.to_numeric(safe.get("non_performing_loans"), errors="coerce")
    loans = pd.to_numeric(safe.get("total_loans"), errors="coerce")

    safe["capital_ratio"] = _safe_divide(assets - liabilities, assets)
    safe["liquidity_ratio"] = _safe_divide(current_assets, current_liabilities)
    safe["roe"] = _safe_divide(net_income, equity)
    safe["npl_ratio"] = _safe_divide(npl, loans)
    safe["npa_to_assets_ratio"] = _safe_divide(npl, assets)
    safe["npl_total_loans_ratio"] = safe["npl_ratio"]
    safe["solvency_ratio"] = _safe_divide(equity, assets)

    safe = safe.sort_values([config.id_col, config.date_col])
    safe["asset_growth"] = safe.groupby(config.id_col)["total_assets"].pct_change() if "total_assets" in safe.columns else np.nan
    safe["asset_volatility"] = (
        safe.groupby(config.id_col)["asset_growth"]
        .transform(lambda x: x.rolling(window=6, min_periods=2).std())
        .fillna(0.0)
    )

    keep = [
        config.id_col,
        config.date_col,
        "capital_ratio",
        "liquidity_ratio",
        "roe",
        "npl_ratio",
        "npa_to_assets_ratio",
        "npl_total_loans_ratio",
        "solvency_ratio",
        "asset_volatility",
    ]
    keep = [c for c in keep if c in safe.columns]
    return safe[keep].drop_duplicates()


def _features_open_banking(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)
    safe["available_amount"] = pd.to_numeric(safe.get("available_amount"), errors="coerce")

    safe = safe.sort_values([config.id_col, config.date_col])
    roll_mean = safe.groupby(config.id_col)["available_amount"].transform(
        lambda x: x.rolling(window=6, min_periods=2).mean()
    )
    roll_std = safe.groupby(config.id_col)["available_amount"].transform(
        lambda x: x.rolling(window=6, min_periods=2).std()
    )
    safe["deposit_volatility"] = (roll_std / (roll_mean.abs() + 1e-9)).fillna(0.0)

    return safe[[config.id_col, config.date_col, "deposit_volatility"]].drop_duplicates()


def _features_regulatory(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "warning_count" not in safe.columns:
        safe["warning_count"] = (safe.get("event_type", "").astype(str).str.lower() == "warning").astype(int)
    if "penalty_count" not in safe.columns:
        safe["penalty_count"] = (safe.get("event_type", "").astype(str).str.lower() == "penalty").astype(int)

    grouped = safe.groupby([config.id_col, config.date_col], as_index=False).agg(
        warning_count=("warning_count", "sum"),
        penalty_count=("penalty_count", "sum"),
    )
    grouped["regulatory_risk"] = grouped["warning_count"] + 2.0 * grouped["penalty_count"]
    return grouped


def _features_news(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "avg_sentiment" not in safe.columns and "sentiment_score" in safe.columns:
        group_keys = [config.date_col] + ([config.id_col] if config.id_col in safe.columns else [])
        safe = safe.groupby(group_keys, as_index=False).agg(
            avg_sentiment=("sentiment_score", "mean"),
            negative_volume=("sentiment_score", lambda x: (pd.to_numeric(x, errors="coerce") < 0).sum()),
        )

    if "negative_volume" not in safe.columns and "article_count" in safe.columns:
        safe["negative_volume"] = pd.to_numeric(safe["article_count"], errors="coerce")

    safe["search_spike_index"] = (
        pd.to_numeric(safe.get("negative_volume", 0), errors="coerce").fillna(0.0)
        - pd.to_numeric(safe.get("negative_volume", 0), errors="coerce").fillna(0.0).rolling(7, min_periods=1).mean()
    ).abs()

    keep = [config.date_col, "avg_sentiment", "negative_volume", "search_spike_index"]
    if config.id_col in safe.columns:
        keep = [config.id_col] + keep
    keep = [c for c in keep if c in safe.columns]
    return safe[keep].drop_duplicates()


def _features_security(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "cve_count" not in safe.columns and "cve_id" in safe.columns:
        group_keys = [config.date_col] + ([config.id_col] if config.id_col in safe.columns else [])
        safe = safe.groupby(group_keys, as_index=False).agg(cve_count=("cve_id", "count"))

    safe["security_incidents"] = pd.to_numeric(safe.get("cve_count"), errors="coerce").fillna(0)

    keep = [config.date_col, "security_incidents"]
    if config.id_col in safe.columns:
        keep = [config.id_col] + keep
    return safe[keep].drop_duplicates()


def _features_operational(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)
    safe["downtime_minutes"] = pd.to_numeric(safe.get("downtime_minutes", safe.get("unavailable_minutes", 0)), errors="coerce").fillna(0)
    safe["tx_latency_ms"] = pd.to_numeric(safe.get("tx_latency_ms", np.nan), errors="coerce")

    grouped = safe.groupby([config.id_col, config.date_col], as_index=False).agg(
        downtime_minutes=("downtime_minutes", "sum"),
        tx_latency_ms=("tx_latency_ms", "mean"),
    )
    return grouped


def _features_macro(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)
    safe["value"] = pd.to_numeric(safe.get("value"), errors="coerce")

    macro_daily = safe.groupby(config.date_col, as_index=False).agg(
        macro_mean=("value", "mean"),
        macro_volatility=("value", "std"),
        macro_min=("value", "min"),
        macro_max=("value", "max"),
    )
    macro_daily["macro_volatility"] = macro_daily["macro_volatility"].fillna(0.0)
    return macro_daily


def _add_temporal_statistics(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    safe = df.copy()
    safe[config.date_col] = pd.to_datetime(safe[config.date_col], errors="coerce")
    safe = safe.sort_values([config.id_col, config.date_col])

    numeric_cols = [
        c
        for c in safe.columns
        if c not in {config.id_col, config.date_col, "trust_label"}
        and pd.api.types.is_numeric_dtype(safe[c])
    ]

    key_cols = [
        "npl_ratio",
        "capital_ratio",
        "deposit_volatility",
        "security_incidents",
        "downtime_minutes",
        "regulatory_risk",
        "avg_sentiment",
    ]
    key_cols = [c for c in key_cols if c in safe.columns]

    for col in key_cols:
        safe[f"{col}_lag_1"] = safe.groupby(config.id_col)[col].shift(1)
        safe[f"{col}_lag_7"] = safe.groupby(config.id_col)[col].shift(7)

    for col in key_cols:
        grouped = safe.groupby(config.id_col)[col]
        for window in config.rolling_windows:
            safe[f"{col}_mean_{window}d"] = grouped.transform(
                lambda x, w=window: x.rolling(window=w, min_periods=2).mean()
            )
            safe[f"{col}_std_{window}d"] = grouped.transform(
                lambda x, w=window: x.rolling(window=w, min_periods=2).std()
            )
            safe[f"{col}_min_{window}d"] = grouped.transform(
                lambda x, w=window: x.rolling(window=w, min_periods=2).min()
            )
            safe[f"{col}_max_{window}d"] = grouped.transform(
                lambda x, w=window: x.rolling(window=w, min_periods=2).max()
            )

    # Simple autocorrelation proxy over recent 30 records.
    for col in key_cols:
        safe[f"{col}_autocorr_30"] = safe.groupby(config.id_col)[col].transform(
            lambda x: x.rolling(30, min_periods=5).apply(_autocorr_lag1, raw=True)
        )

    # Preserve base numeric columns and engineered columns.
    keep_cols = [config.id_col, config.date_col] + [c for c in safe.columns if c not in {config.id_col, config.date_col}]
    safe = safe[keep_cols]

    # Fill engineered NaNs conservatively; document bias in README.
    engineered_cols = [c for c in safe.columns if c not in {config.id_col, config.date_col}]
    safe[engineered_cols] = safe[engineered_cols].replace([np.inf, -np.inf], np.nan)
    return safe


def _derive_risk_score(df: pd.DataFrame) -> pd.Series:
    # Weighted risk proxy used when no labeled target is available.
    safe = df.copy()
    def _norm(series):
        s = pd.to_numeric(series, errors="coerce")
        return (s - s.min()) / (s.max() - s.min() + 1e-9)

    risk = (
        0.20 * _norm(safe.get("npl_ratio", 0))
        + 0.15 * _norm(safe.get("deposit_volatility", 0))
        + 0.10 * _norm(safe.get("asset_volatility", 0))
        + 0.15 * _norm(safe.get("regulatory_risk", 0))
        + 0.10 * _norm(safe.get("security_incidents", 0))
        + 0.10 * _norm(safe.get("downtime_minutes", 0))
        + 0.10 * _norm(safe.get("negative_volume", 0))
        - 0.05 * _norm(safe.get("capital_ratio", 0))
        - 0.05 * _norm(safe.get("liquidity_ratio", 0))
    )
    return risk.fillna(risk.median() if not risk.empty else 0.5)


def _resolve_date_column(df: pd.DataFrame, config: FeatureConfig) -> pd.Series:
    if config.date_col in df.columns:
        return pd.to_datetime(df[config.date_col], errors="coerce").dt.date
    for candidate in ["date", "ingested_at", "created_at", "publishedAt"]:
        if candidate in df.columns:
            return pd.to_datetime(df[candidate], errors="coerce").dt.date
    return pd.Series([pd.Timestamp("today").date()] * len(df), index=df.index)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return pd.to_numeric(numerator, errors="coerce") / pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)


def _autocorr_lag1(values: np.ndarray) -> float:
    if values.size < 3:
        return np.nan
    a = values[:-1]
    b = values[1:]
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])
