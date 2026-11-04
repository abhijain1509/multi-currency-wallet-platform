def test_credit_and_balance(client, auth_headers):
    headers = auth_headers("w1@example.com")
    resp = client.post(
        "/api/v1/wallets/credit",
        json={"wallet_currency": "USD", "amount": "100.00"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["amount_minor"] == 10000

    wallets = client.get("/api/v1/wallets", headers=headers).json()
    usd = next(w for w in wallets if w["currency"] == "USD")
    assert usd["balance_minor"] == 10000
    assert usd["balance"] == "100.00"


def test_credit_with_conversion(client, auth_headers):
    headers = auth_headers("w2@example.com")
    # Deposit 10 EUR worth into a USD wallet. EUR->USD = 1/0.5 = 2.0 -> 20 USD.
    resp = client.post(
        "/api/v1/wallets/credit",
        json={"wallet_currency": "USD", "amount": "10.00", "amount_currency": "EUR"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["amount_minor"] == 2000
    assert body["source_currency"] == "EUR"


def test_debit_insufficient_funds(client, auth_headers):
    headers = auth_headers("w3@example.com")
    resp = client.post(
        "/api/v1/wallets/debit",
        json={"wallet_currency": "USD", "amount": "50.00"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_credit_idempotency(client, auth_headers):
    headers = auth_headers("w4@example.com")
    payload = {"wallet_currency": "USD", "amount": "25.00", "idempotency_key": "abc-123"}
    first = client.post("/api/v1/wallets/credit", json=payload, headers=headers)
    second = client.post("/api/v1/wallets/credit", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    wallets = client.get("/api/v1/wallets", headers=headers).json()
    usd = next(w for w in wallets if w["currency"] == "USD")
    assert usd["balance_minor"] == 2500  # applied once, not twice
