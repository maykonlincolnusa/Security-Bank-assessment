import hashlib
import hmac
import json
import os
import time

import httpx

BASE_URL = os.getenv("TRUST_SCORE_URL", "http://localhost:8000")
TOKEN = os.getenv("TRUST_SCORE_TOKEN", "")
AGENT_ID = os.getenv("AGENT_ID", "agent-001")
AGENT_SKILL = os.getenv("AGENT_SKILL", "trust-score-skill")
AGENT_SIGNING_SECRET = os.getenv("AGENT_SIGNING_SECRET", "change-me")
REPORT_PATH = os.getenv("REPORT_PATH", "reports/trust_score_report.json")

# This skill MUST run in an isolated environment with read-only credentials.
# Do NOT grant write access to production systems.


def _sign(method: str, path: str, body: bytes) -> str:
    msg = f"{AGENT_ID}:{method}:{path}".encode("utf-8") + body
    return hmac.new(AGENT_SIGNING_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def get_score(institution_id: str):
    path = f"/score/{institution_id}"
    signature = _sign("GET", path, b"")
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Agent-Id": AGENT_ID,
        "X-Agent-Signature": signature,
        "X-Agent-Skill": AGENT_SKILL,
        "X-Agent-Vetted": "true",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}{path}", headers=headers)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Rate limiting (client side)
    time.sleep(1.0)
    result = get_score("001")
    report_dir = os.path.dirname(REPORT_PATH)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
    # Store the report in isolated, least-privilege storage (read-only for other systems).
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=True, indent=2)
    print(result)
