from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


metadata = MetaData()

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("actor", String(128), nullable=False),
    Column("action", String(128), nullable=False),
    Column("resource", String(256), nullable=False),
    Column("details", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

trust_features = Table(
    "trust_features",
    metadata,
    Column("institution_id", String(128), primary_key=True),
    Column("features", Text, nullable=False),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)


def get_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(db_url, pool_pre_ping=True)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
