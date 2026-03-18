from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
import requests


class OpenBankingClient:
    def __init__(self, token_url: str, base_url: str, client_id: str, client_secret: str, scope: str):
        self.token_url = token_url
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope

    def is_configured(self) -> bool:
        return all([self.token_url, self.base_url, self.client_id, self.client_secret])

    def _token(self) -> str:
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["access_token"]

    def fetch_accounts(self) -> pd.DataFrame:
        if not self.is_configured():
            return pd.DataFrame()
        token = self._token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{self.base_url}/accounts", headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        accounts = payload.get("data", [])
        return pd.DataFrame(accounts)

    def fetch_balances(self, account_id: str) -> pd.DataFrame:
        if not self.is_configured():
            return pd.DataFrame()
        token = self._token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{self.base_url}/accounts/{account_id}/balances", headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        balances = payload.get("data", [])
        return pd.DataFrame(balances)


def normalize_open_banking_accounts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    renamed = df.rename(
        columns={
            "accountId": "account_id",
            "brandName": "brand_name",
            "companyCnpj": "cnpj",
        }
    ).copy()
    return renamed


def normalize_open_banking_balances(df: pd.DataFrame, account_id: str) -> pd.DataFrame:
    if df.empty:
        return df
    renamed = df.rename(
        columns={
            "availableAmount": "available_amount",
            "blockedAmount": "blocked_amount",
        }
    ).copy()
    renamed["account_id"] = account_id
    return renamed
