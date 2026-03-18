from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import pandas as pd
import requests

BCB_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}/dados"


def fetch_bcb_series(series_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    params = {"formato": "json"}
    if start_date:
        params["dataInicial"] = _date_to_bcb(start_date)
    if end_date:
        params["dataFinal"] = _date_to_bcb(end_date)
    response = requests.get(BCB_BASE_URL.format(series_id=series_id), params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["series_id"] = series_id
    df.rename(columns={"data": "ref_date", "valor": "value"}, inplace=True)
    df["ref_date"] = pd.to_datetime(df["ref_date"], dayfirst=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def fetch_bcb_series_bulk(series_ids: List[str], start_date: Optional[str], end_date: Optional[str]) -> pd.DataFrame:
    frames = []
    for series_id in series_ids:
        frames.append(fetch_bcb_series(series_id, start_date=start_date, end_date=end_date))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _date_to_bcb(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    return dt.strftime("%d/%m/%Y")
