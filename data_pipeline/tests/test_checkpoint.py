from sqlalchemy import create_engine

from etl.db import CheckpointStore


def test_checkpoint_store_roundtrip():
    engine = create_engine("sqlite:///:memory:")
    store = CheckpointStore(engine, schema="")

    assert store.get("source") is None
    store.set("source", "2024-01-01")
    assert store.get("source") == "2024-01-01"
