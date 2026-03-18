import pandas as pd
import pytest

from etl.pipeline import validate_raw_schemas


class DummyCtx:
    pass


def test_validate_raw_schemas_raises_on_missing_columns(monkeypatch):
    def fake_safe_read_table(engine, schema, table):
        if table == "bcb_series":
            return pd.DataFrame({"series_id": ["1"], "value": [1.0]})
        return pd.DataFrame()

    monkeypatch.setattr("etl.pipeline.safe_read_table", fake_safe_read_table)

    with pytest.raises(RuntimeError):
        validate_raw_schemas(DummyCtx(), object())


def test_validate_raw_schemas_passes_when_columns_ok(monkeypatch):
    def fake_safe_read_table(engine, schema, table):
        if table == "bcb_series":
            return pd.DataFrame({"series_id": ["1"], "ref_date": ["2024-01-01"], "value": [1.0]})
        if table == "news":
            return pd.DataFrame({"sentiment_score": [1]})
        return pd.DataFrame()

    monkeypatch.setattr("etl.pipeline.safe_read_table", fake_safe_read_table)

    validate_raw_schemas(DummyCtx(), object())
