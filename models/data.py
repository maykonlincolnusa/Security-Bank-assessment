from __future__ import annotations

from typing import Dict

import pandas as pd
from sqlalchemy import create_engine


CURATED_SCHEMA = "curated"
STAGING_SCHEMA = "staging"


def load_curated_tables(db_url: str) -> Dict[str, pd.DataFrame]:
    engine = create_engine(db_url)
    tables = {
        "macro_series": _safe_read(engine, CURATED_SCHEMA, "macro_series"),
        "news_sentiment_daily": _safe_read(engine, CURATED_SCHEMA, "news_sentiment_daily"),
        "security_cve_daily": _safe_read(engine, CURATED_SCHEMA, "security_cve_daily"),
        "open_banking_accounts": _safe_read(engine, STAGING_SCHEMA, "open_banking_accounts"),
        "open_banking_balances": _safe_read(engine, STAGING_SCHEMA, "open_banking_balances"),
        "financial_statements": _safe_read(engine, STAGING_SCHEMA, "financial_statements"),
        "regulatory_events": _safe_read(engine, STAGING_SCHEMA, "regulatory_events"),
        "operational_telemetry": _safe_read(engine, STAGING_SCHEMA, "operational_telemetry"),
    }
    return tables


def _safe_read(engine, schema: str, table: str) -> pd.DataFrame:
    try:
        return pd.read_sql_table(table, con=engine, schema=schema)
    except Exception:
        return pd.DataFrame()
