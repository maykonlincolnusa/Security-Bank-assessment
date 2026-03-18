from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class FeatureConfig:
    id_col: str = "bank_id"
    date_col: str = "ref_date"


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
    return result


def _build_base_index(tables: Dict[str, pd.DataFrame], config: FeatureConfig) -> pd.DataFrame:
    candidates = []
    for name in ["open_banking_accounts", "open_banking_balances", "financial_statements", "regulatory_events"]:
        df = tables.get(name, pd.DataFrame())
        if df.empty or config.id_col not in df.columns:
            continue
        temp = df[[config.id_col]].copy()
        if config.date_col in df.columns:
            temp[config.date_col] = pd.to_datetime(df[config.date_col], errors="coerce").dt.date
        else:
            temp[config.date_col] = pd.Timestamp("today").date()
        candidates.append(temp.dropna().drop_duplicates())

    if not candidates:
        return pd.DataFrame()

    return pd.concat(candidates, ignore_index=True).drop_duplicates()


def _merge_features(frames: List[pd.DataFrame], config: FeatureConfig) -> pd.DataFrame:
    result = frames[0]
    for frame in frames[1:]:
        if frame.empty:
            continue
        join_keys = [k for k in [config.id_col, config.date_col] if k in result.columns and k in frame.columns]
        if not join_keys:
            continue
        result = result.merge(frame, on=join_keys, how="left")
    return result


def _features_financials(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "total_assets" in safe.columns and "total_liabilities" in safe.columns:
        safe["capital_ratio"] = _safe_divide(
            pd.to_numeric(safe["total_assets"], errors="coerce") - pd.to_numeric(safe["total_liabilities"], errors="coerce"),
            pd.to_numeric(safe["total_assets"], errors="coerce"),
        )
    if "current_assets" in safe.columns and "current_liabilities" in safe.columns:
        safe["liquidity_ratio"] = _safe_divide(
            pd.to_numeric(safe["current_assets"], errors="coerce"),
            pd.to_numeric(safe["current_liabilities"], errors="coerce"),
        )
    if "net_income" in safe.columns and "equity" in safe.columns:
        safe["roe"] = _safe_divide(
            pd.to_numeric(safe["net_income"], errors="coerce"),
            pd.to_numeric(safe["equity"], errors="coerce"),
        )
    if "non_performing_loans" in safe.columns and "total_loans" in safe.columns:
        safe["npl_ratio"] = _safe_divide(
            pd.to_numeric(safe["non_performing_loans"], errors="coerce"),
            pd.to_numeric(safe["total_loans"], errors="coerce"),
        )

    if "solvency_ratio" not in safe.columns:
        if "capital_ratio" in safe.columns:
            safe["solvency_ratio"] = safe["capital_ratio"]
        elif "equity" in safe.columns and "total_assets" in safe.columns:
            safe["solvency_ratio"] = _safe_divide(
                pd.to_numeric(safe["equity"], errors="coerce"),
                pd.to_numeric(safe["total_assets"], errors="coerce"),
            )

    if "total_assets" in safe.columns:
        safe = safe.sort_values([config.id_col, config.date_col])
        safe["asset_growth"] = safe.groupby(config.id_col)["total_assets"].pct_change()
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
        "solvency_ratio",
        "asset_volatility",
    ]
    keep = [c for c in keep if c in safe.columns]
    if len(keep) <= 2:
        return pd.DataFrame()
    return safe[keep].drop_duplicates()


def _features_open_banking(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty or config.id_col not in df.columns:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "available_amount" in safe.columns:
        safe["available_amount"] = pd.to_numeric(safe["available_amount"], errors="coerce")
        safe = safe.sort_values([config.id_col, config.date_col])
        safe["deposit_volatility"] = (
            safe.groupby(config.id_col)["available_amount"]
            .transform(lambda x: x.rolling(window=6, min_periods=2).std() / (x.rolling(window=6, min_periods=2).mean().abs() + 1e-9))
            .fillna(0.0)
        )

    keep = [config.id_col, config.date_col, "deposit_volatility"]
    keep = [c for c in keep if c in safe.columns]
    if len(keep) <= 2:
        return pd.DataFrame()
    return safe[keep].drop_duplicates()


def _features_regulatory(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    if config.id_col not in safe.columns:
        return pd.DataFrame()
    safe[config.date_col] = _resolve_date_column(safe, config)

    warning_col = "warning_count" if "warning_count" in safe.columns else None
    penalty_col = "penalty_count" if "penalty_count" in safe.columns else None

    if warning_col is None and "event_type" in safe.columns:
        safe["warning_count"] = (safe["event_type"].astype(str).str.lower() == "warning").astype(int)
        warning_col = "warning_count"
    if penalty_col is None and "event_type" in safe.columns:
        safe["penalty_count"] = (safe["event_type"].astype(str).str.lower() == "penalty").astype(int)
        penalty_col = "penalty_count"

    if warning_col is None:
        safe["warning_count"] = 0
        warning_col = "warning_count"
    if penalty_col is None:
        safe["penalty_count"] = 0
        penalty_col = "penalty_count"

    grouped = safe.groupby([config.id_col, config.date_col], as_index=False).agg(
        warning_count=(warning_col, "sum"),
        penalty_count=(penalty_col, "sum"),
    )
    grouped["regulatory_risk"] = grouped["warning_count"] + 2.0 * grouped["penalty_count"]
    return grouped


def _features_news(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if config.id_col not in safe.columns:
        # Daily aggregate replicated to all institutions at merge-time using date join only.
        pass

    if "avg_sentiment" not in safe.columns and "sentiment_score" in safe.columns:
        group_keys = [config.date_col] + ([config.id_col] if config.id_col in safe.columns else [])
        safe = safe.groupby(group_keys, as_index=False).agg(
            avg_sentiment=("sentiment_score", "mean"),
            negative_volume=("sentiment_score", lambda x: (pd.to_numeric(x, errors="coerce") < 0).sum()),
        )

    if "negative_volume" not in safe.columns and "article_count" in safe.columns:
        safe["negative_volume"] = pd.to_numeric(safe["article_count"], errors="coerce")

    if "search_spike_index" not in safe.columns:
        base = pd.to_numeric(safe.get("negative_volume", 0), errors="coerce").fillna(0)
        safe["search_spike_index"] = (base - base.rolling(7, min_periods=1).mean()).abs()

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

    safe["security_incidents"] = pd.to_numeric(safe.get("cve_count", 0), errors="coerce").fillna(0)

    keep = [config.date_col, "security_incidents"]
    if config.id_col in safe.columns:
        keep = [config.id_col] + keep
    return safe[keep].drop_duplicates()


def _features_operational(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    if config.id_col not in safe.columns:
        return pd.DataFrame()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "downtime_minutes" not in safe.columns:
        safe["downtime_minutes"] = pd.to_numeric(safe.get("unavailable_minutes", 0), errors="coerce").fillna(0)

    grouped = safe.groupby([config.id_col, config.date_col], as_index=False).agg(
        downtime_minutes=("downtime_minutes", "sum")
    )
    return grouped


def _features_macro(df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    safe = df.copy()
    safe[config.date_col] = _resolve_date_column(safe, config)

    if "value" in safe.columns:
        safe["value"] = pd.to_numeric(safe["value"], errors="coerce")
        macro_daily = safe.groupby(config.date_col, as_index=False).agg(macro_volatility=("value", "std"))
        macro_daily["macro_volatility"] = macro_daily["macro_volatility"].fillna(0.0)
        return macro_daily
    return pd.DataFrame()


def _resolve_date_column(df: pd.DataFrame, config: FeatureConfig) -> pd.Series:
    if config.date_col in df.columns:
        return pd.to_datetime(df[config.date_col], errors="coerce").dt.date
    for candidate in ["date", "ingested_at", "created_at", "publishedAt"]:
        if candidate in df.columns:
            return pd.to_datetime(df[candidate], errors="coerce").dt.date
    return pd.Series([pd.Timestamp("today").date()] * len(df), index=df.index)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)
