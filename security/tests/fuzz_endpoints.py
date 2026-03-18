from __future__ import annotations

import json
import os
import random
import string

import httpx

BASE_URL = os.getenv("TRUST_SCORE_URL", "http://localhost:8000")
TOKEN = os.getenv("TRUST_SCORE_TOKEN", "")


def _rand(n: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "{}_[]!@#$%^&*()"
    return "".join(random.choice(alphabet) for _ in range(n))


def fuzz_batch_score(iterations: int = 10):
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    with httpx.Client(timeout=8.0) as client:
        for i in range(iterations):
            payload = {
                "items": [
                    {
                        "institution_id": _rand(),
                        "features": {
                            _rand(6): random.uniform(-1e6, 1e6),
                            _rand(6): random.uniform(-1e6, 1e6),
                        },
                    }
                ]
            }
            resp = client.post(f"{BASE_URL}/batch/score", headers=headers, content=json.dumps(payload))
            print(f"iter={i} status={resp.status_code}")


def main():
    if not TOKEN:
        raise RuntimeError("Set TRUST_SCORE_TOKEN before running fuzzing")
    fuzz_batch_score(iterations=20)


if __name__ == "__main__":
    main()
