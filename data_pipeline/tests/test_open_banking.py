import responses

from etl.sources.open_banking import OpenBankingClient


@responses.activate
def test_open_banking_fetch_accounts_and_balances():
    token_url = "https://provider.example.com/oauth2/token"
    base_url = "https://provider.example.com/open-banking/v1"

    responses.add(
        responses.POST,
        token_url,
        json={"access_token": "abc123"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{base_url}/accounts",
        json={"data": [{"accountId": "acc-1", "companyCnpj": "00000000000191"}]},
        status=200,
    )
    responses.add(
        responses.POST,
        token_url,
        json={"access_token": "abc123"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{base_url}/accounts/acc-1/balances",
        json={"data": [{"availableAmount": 100.0, "blockedAmount": 10.0}]},
        status=200,
    )

    client = OpenBankingClient(token_url, base_url, "id", "secret", "accounts")
    accounts = client.fetch_accounts()
    balances = client.fetch_balances("acc-1")

    assert not accounts.empty
    assert accounts.loc[0, "accountId"] == "acc-1"
    assert not balances.empty
    assert float(balances.loc[0, "availableAmount"]) == 100.0
