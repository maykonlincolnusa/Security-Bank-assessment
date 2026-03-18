from __future__ import annotations

import json
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_features(session: AsyncSession, institution_id: str) -> Optional[Dict[str, float]]:
    try:
        query = text(
            "SELECT features FROM curated.trust_features WHERE institution_id = :institution_id LIMIT 1"
        )
        result = await session.execute(query, {"institution_id": institution_id})
        row = result.fetchone()
        if not row:
            # SQLite/test fallback without schema.
            fallback = text(
                "SELECT features FROM trust_features WHERE institution_id = :institution_id LIMIT 1"
            )
            result = await session.execute(fallback, {"institution_id": institution_id})
            row = result.fetchone()
        if not row:
            return None
        payload = row[0]
        if isinstance(payload, dict):
            return payload
        return json.loads(payload)
    except Exception:
        return None
