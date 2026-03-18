from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from ..utils import simple_sentiment


def fetch_news(api_base_url: str, api_key: str, query: str, language: str = "pt") -> pd.DataFrame:
    if not api_base_url or not api_key:
        return pd.DataFrame()
    params = {
        "q": query,
        "language": language,
        "token": api_key,
    }
    response = requests.get(api_base_url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    articles = payload.get("articles") or payload.get("data") or []
    df = pd.DataFrame(articles)
    if df.empty:
        return df
    df["sentiment_score"] = df.apply(_sentiment_row, axis=1)
    df["ingested_at"] = datetime.utcnow().isoformat() + "Z"
    return df


def _sentiment_row(row: pd.Series) -> int:
    text_parts = [str(row.get("title", "")), str(row.get("description", ""))]
    return simple_sentiment(" ".join(text_parts))
