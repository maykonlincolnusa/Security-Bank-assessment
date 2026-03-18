import os

import pytest

pytest.importorskip("httpx")


@pytest.mark.integration
def test_agent_endpoint_integration_example():
    base_url = os.getenv("TRUST_SCORE_URL")
    token = os.getenv("TRUST_SCORE_TOKEN")

    if not base_url or not token:
        pytest.skip("Set TRUST_SCORE_URL and TRUST_SCORE_TOKEN for integration test")

    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"items": [{"institution_id": "001", "features": {"capital_ratio": 0.1}}]}

    response = httpx.post(f"{base_url.rstrip('/')}/batch/score", headers=headers, json=payload, timeout=10.0)
    assert response.status_code in (200, 404)
