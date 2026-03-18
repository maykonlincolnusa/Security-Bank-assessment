from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


@dataclass
class CheckpointStore:
    engine: Engine
    schema: str = "metadata"

    def _table(self) -> Table:
        metadata = MetaData(schema=self.schema or None)
        return Table(
            "etl_checkpoints",
            metadata,
            Column("source_name", String(128), primary_key=True),
            Column("last_cursor", String(128), nullable=True),
            Column("updated_at", DateTime, nullable=False),
        )

    def ensure(self) -> None:
        table = self._table()
        table.metadata.create_all(self.engine)

    def get(self, source_name: str) -> Optional[str]:
        self.ensure()
        qualified = f"{self.schema}.etl_checkpoints" if self.schema else "etl_checkpoints"
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    f"SELECT last_cursor FROM {qualified} "
                    "WHERE source_name = :source"
                ),
                {"source": source_name},
            ).fetchone()
        if not result:
            return None
        return result[0]

    def set(self, source_name: str, last_cursor: str) -> None:
        self.ensure()
        qualified = f"{self.schema}.etl_checkpoints" if self.schema else "etl_checkpoints"
        now = datetime.utcnow()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"INSERT INTO {qualified} (source_name, last_cursor, updated_at) "
                    "VALUES (:source, :cursor, :updated_at) "
                    "ON CONFLICT (source_name) DO UPDATE SET "
                    "last_cursor = :cursor, updated_at = :updated_at"
                ),
                {"source": source_name, "cursor": last_cursor, "updated_at": now},
            )


def get_engine(db_url: str) -> Engine:
    try:
        return create_engine(db_url, pool_pre_ping=True)
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Failed to create DB engine: {exc}") from exc
