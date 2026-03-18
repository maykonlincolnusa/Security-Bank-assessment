from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Iterable, List

import requests

from ..storage import S3Storage
from ..utils import rate_limit_sleep


def fetch_financial_statements(
    urls: Iterable[str],
    storage: S3Storage,
    key_prefix: str,
    rate_limit_sec: float = 2.0,
) -> List[str]:
    uploaded_keys: List[str] = []
    last_ts = 0.0
    for url in urls:
        last_ts = rate_limit_sleep(rate_limit_sec, last_ts)
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        content = response.content
        digest = hashlib.sha256(content).hexdigest()[:16]
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        ext = _guess_extension(response.headers.get("Content-Type", ""))
        key = f"{key_prefix}/financials/{timestamp}_{digest}{ext}"
        storage.upload_bytes(key, content, response.headers.get("Content-Type"))
        uploaded_keys.append(key)
    return uploaded_keys


def _guess_extension(content_type: str) -> str:
    if "pdf" in content_type:
        return ".pdf"
    if "html" in content_type:
        return ".html"
    return ".bin"
