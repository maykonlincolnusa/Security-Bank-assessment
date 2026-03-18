from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import requests


def fetch_cves(api_base_url: str, last_cursor: Optional[str] = None) -> pd.DataFrame:
    params = {"resultsPerPage": 2000}
    if last_cursor:
        params["lastModStartDate"] = _iso_to_nvd(last_cursor)
        params["lastModEndDate"] = _iso_to_nvd(datetime.utcnow().isoformat())
    response = requests.get(api_base_url, params=params, timeout=60)
    response.raise_for_status()
    payload = response.json()
    items = payload.get("vulnerabilities", [])
    if not items:
        return pd.DataFrame()
    records = []
    for item in items:
        cve = item.get("cve", {})
        records.append(
            {
                "cve_id": cve.get("id"),
                "published": cve.get("published"),
                "last_modified": cve.get("lastModified"),
                "source": cve.get("sourceIdentifier"),
                "description": _extract_description(cve),
            }
        )
    df = pd.DataFrame(records)
    return df


def fetch_virustotal_iocs(api_base_url: str, api_key: str, query: str = "bank") -> pd.DataFrame:
    if not api_base_url or not api_key:
        return pd.DataFrame()
    headers = {"x-apikey": api_key}
    response = requests.get(f"{api_base_url}/intelligence/search", headers=headers, params={"query": query}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data", [])
    if not data:
        return pd.DataFrame()
    records = []
    for item in data:
        attributes = item.get("attributes", {})
        records.append(
            {
                "type": item.get("type"),
                "id": item.get("id"),
                "last_analysis_stats": attributes.get("last_analysis_stats"),
                "last_analysis_date": attributes.get("last_analysis_date"),
            }
        )
    return pd.DataFrame(records)


def _extract_description(cve: dict) -> str:
    descriptions = cve.get("descriptions", [])
    for entry in descriptions:
        if entry.get("lang") == "en":
            return entry.get("value", "")
    if descriptions:
        return descriptions[0].get("value", "")
    return ""


def _iso_to_nvd(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", ""))
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
