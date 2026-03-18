import hashlib
import hmac
import json
import os
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

MODEL_PATH = os.getenv("MODEL_ONNX_PATH", "models/output/model.onnx")
FEATURES_PATH = os.getenv("MODEL_FEATURES_PATH", "models/output/model_features.json")

os.environ.setdefault("MODEL_ONNX_PATH", MODEL_PATH)
os.environ.setdefault("MODEL_FEATURES_PATH", FEATURES_PATH)
os.environ.setdefault("MODEL_FEATURE_IMPORTANCE_PATH", "")
os.environ.setdefault("SERVICE_DB_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ISSUER", "trust-score-service")
os.environ.setdefault("JWT_AUDIENCE", "trust-score-clients")
os.environ.setdefault("AGENT_SIGNING_SECRET", "agent-secret")
os.environ.setdefault("AGENT_ALLOWED_IDS", "agent-001")
os.environ.setdefault("AGENT_SKILL_ALLOWLIST", "trust-score-skill")
os.environ.setdefault("AGENT_SKILL_BLACKLIST", "skill-dangerous-001")

def _require_artifacts():
    if not Path(MODEL_PATH).exists() or not Path(FEATURES_PATH).exists():
        pytest.skip("ONNX model or model_features not available for integration tests")
    __import__("prometheus_client")
    __import__("onnxruntime")
    __import__("redis")


def _client() -> TestClient:
    from api_service.app.main import app  # noqa: WPS433

    return TestClient(app)


def test_integration_module_loaded():
    assert True


def _token():
    payload = {
        "sub": "tester",
        "client_id": "client-1",
        "roles": ["analyst"],
        "iss": os.environ["JWT_ISSUER"],
        "aud": os.environ["JWT_AUDIENCE"],
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def _sign(agent_id: str, method: str, path: str, body: bytes) -> str:
    msg = f"{agent_id}:{method}:{path}".encode("utf-8") + body
    return hmac.new(os.environ["AGENT_SIGNING_SECRET"].encode("utf-8"), msg, hashlib.sha256).hexdigest()


def test_batch_score_with_model_and_features_payload():
    _require_artifacts()
    client = _client()
    features = {
        "capital_ratio": 0.1,
        "liquidity_ratio": 1.2,
        "roe": 0.08,
        "npl_ratio": 0.04,
        "deposit_volatility": 0.11,
        "avg_sentiment": -0.1,
        "negative_volume": 8.0,
        "security_incidents": 2.0,
    }
    response = client.post(
        "/batch/score",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"items": [{"institution_id": "001", "features": features}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert "trust_score" in data["results"][0]


def test_agent_signature_enforced_when_agent_headers_present():
    _require_artifacts()
    client = _client()
    payload = {"items": [{"institution_id": "001", "features": {"capital_ratio": 0.2}}]}
    body = json.dumps(payload).encode("utf-8")

    bad_headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "X-Agent-Id": "agent-001",
        "X-Agent-Skill": "trust-score-skill",
        "X-Agent-Vetted": "true",
        "X-Agent-Signature": "bad-signature",
    }
    bad = client.post("/batch/score", headers=bad_headers, content=body)
    assert bad.status_code == 403

    signature = _sign("agent-001", "POST", "/batch/score", body)
    good_headers = dict(bad_headers)
    good_headers["X-Agent-Signature"] = signature
    good = client.post("/batch/score", headers=good_headers, content=body)
    assert good.status_code == 200
