def _fund(client, headers, currency="USD", amount="100.00"):
    resp = client.post(
        "/api/v1/wallets/credit",
        json={"wallet_currency": currency, "amount": amount},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


def test_same_currency_transfer(client, auth_headers):
    sender = auth_headers("s1@example.com")
    auth_headers("r1@example.com")
    _fund(client, sender, "USD", "100.00")

    resp = client.post(
        "/api/v1/transfers",
        json={
            "recipient_email": "r1@example.com",
            "amount": "40.00",
            "from_currency": "USD",
            "to_currency": "USD",
        },
        headers=sender,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["debited_minor"] == 4000
    assert body["credited_minor"] == 4000


def test_cross_currency_transfer_conserves_value(client, auth_headers):
    sender = auth_headers("s2@example.com")
    recipient = auth_headers("r2@example.com")
    _fund(client, sender, "USD", "100.00")

    # USD->EUR at 0.5: debit 10 USD -> credit 5 EUR.
    resp = client.post(
        "/api/v1/transfers",
        json={
            "recipient_email": "r2@example.com",
            "amount": "10.00",
            "from_currency": "USD",
            "to_currency": "EUR",
        },
        headers=sender,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["credited_minor"] == 500

    sender_usd = next(
        w for w in client.get("/api/v1/wallets", headers=sender).json() if w["currency"] == "USD"
    )
    recipient_eur = next(
        w for w in client.get("/api/v1/wallets", headers=recipient).json() if w["currency"] == "EUR"
    )
    assert sender_usd["balance_minor"] == 9000
    assert recipient_eur["balance_minor"] == 500


def test_transfer_insufficient_funds(client, auth_headers):
    sender = auth_headers("s3@example.com")
    auth_headers("r3@example.com")
    resp = client.post(
        "/api/v1/transfers",
        json={
            "recipient_email": "r3@example.com",
            "amount": "10.00",
            "from_currency": "USD",
            "to_currency": "USD",
        },
        headers=sender,
    )
    assert resp.status_code == 422


def test_transfer_to_self_rejected(client, auth_headers):
    sender = auth_headers("self@example.com")
    _fund(client, sender, "USD", "100.00")
    resp = client.post(
        "/api/v1/transfers",
        json={
            "recipient_email": "self@example.com",
            "amount": "10.00",
            "from_currency": "USD",
            "to_currency": "USD",
        },
        headers=sender,
    )
    assert resp.status_code == 400


def test_transfer_idempotency(client, auth_headers):
    sender = auth_headers("s4@example.com")
    auth_headers("r4@example.com")
    _fund(client, sender, "USD", "100.00")
    payload = {
        "recipient_email": "r4@example.com",
        "amount": "30.00",
        "from_currency": "USD",
        "to_currency": "USD",
        "idempotency_key": "transfer-key-1",
    }
    first = client.post("/api/v1/transfers", json=payload, headers=sender)
    second = client.post("/api/v1/transfers", json=payload, headers=sender)
    assert first.status_code == 201
    assert second.status_code == 201

    sender_usd = next(
        w for w in client.get("/api/v1/wallets", headers=sender).json() if w["currency"] == "USD"
    )
    assert sender_usd["balance_minor"] == 7000  # debited once
