from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from .storage import S3Storage


@dataclass
class LineageRecord:
    name: str
    inputs: List[str]
    outputs: List[str]
    transform: str


def infer_schema(df: pd.DataFrame) -> Dict[str, Any]:
    fields = []
    for col, dtype in df.dtypes.items():
        fields.append({"name": col, "type": str(dtype)})
    return {"fields": fields}


def write_schema(storage: S3Storage, key_prefix: str, table_name: str, df: pd.DataFrame) -> str:
    schema = {
        "table": table_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "schema": infer_schema(df),
    }
    key = f"{key_prefix}/catalog/{table_name}/schema.json"
    storage.upload_bytes(key, json.dumps(schema, indent=2).encode("utf-8"), "application/json")
    return key


def write_lineage(storage: S3Storage, key_prefix: str, lineage: LineageRecord) -> str:
    payload = {
        "name": lineage.name,
        "inputs": lineage.inputs,
        "outputs": lineage.outputs,
        "transform": lineage.transform,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    key = f"{key_prefix}/catalog/lineage/{lineage.name}.json"
    storage.upload_bytes(key, json.dumps(payload, indent=2).encode("utf-8"), "application/json")
    return key
