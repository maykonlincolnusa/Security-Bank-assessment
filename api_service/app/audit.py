from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .db import audit_logs


async def log_audit(session: AsyncSession, actor: str, action: str, resource: str, details: Dict[str, Any]) -> None:
    payload = json.dumps(details, ensure_ascii=True)
    await session.execute(
        insert(audit_logs).values(actor=actor, action=action, resource=resource, details=payload)
    )
    await session.commit()
