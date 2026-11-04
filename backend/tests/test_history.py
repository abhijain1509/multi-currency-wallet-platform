def _fund(client, headers, currency="USD", amount="100.00"):
    client.post(
        "/api/v1/wallets/credit",
        json={"wallet_currency": currency, "amount": amount},
        headers=headers,
    )


def test_history_pagination_and_filter(client, auth_headers):
    headers = auth_headers("h1@example.com")
    for amount in ("10.00", "20.00", "30.00"):
        _fund(client, headers, "USD", amount)
    client.post(
        "/api/v1/wallets/debit",
        json={"wallet_currency": "USD", "amount": "5.00"},
        headers=headers,
    )

    page = client.get("/api/v1/transactions?limit=2&offset=0", headers=headers).json()
    assert page["total"] == 4
    assert len(page["items"]) == 2
    assert page["limit"] == 2

    credits = client.get("/api/v1/transactions?type=credit", headers=headers).json()
    assert credits["total"] == 3
    assert all(item["type"] == "credit" for item in credits["items"])


def test_health_and_metrics(client):
    assert client.get("/health").json() == {"status": "ok"}
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text


def test_unmatched_path_does_not_inflate_metric_labels(client):
    # A 404 to an arbitrary URL must be bucketed, not create a per-URL label.
    client.get("/api/v1/this-route-does-not-exist-123")
    metrics = client.get("/metrics").text
    assert "<unmatched>" in metrics
    assert "this-route-does-not-exist-123" not in metrics
