from __future__ import annotations

from typing import Dict, List

import httpx


class TrustScoreClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.timeout = timeout

    def get_score(self, institution_id: str, agent_headers: Dict[str, str] | None = None) -> Dict:
        url = f"{self.base_url}/score/{institution_id}"
        headers = dict(self.headers)
        if agent_headers:
            headers.update(agent_headers)
        response = httpx.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def batch_score(self, items: List[Dict], agent_headers: Dict[str, str] | None = None) -> Dict:
        url = f"{self.base_url}/batch/score"
        headers = dict(self.headers)
        if agent_headers:
            headers.update(agent_headers)
        response = httpx.post(url, headers=headers, json={"items": items}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    async def batch_score_async(self, items: List[Dict], agent_headers: Dict[str, str] | None = None) -> Dict:
        url = f"{self.base_url}/batch/score"
        headers = dict(self.headers)
        if agent_headers:
            headers.update(agent_headers)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json={"items": items})
            response.raise_for_status()
            return response.json()
