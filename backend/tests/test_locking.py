from datetime import datetime, timezone

from sqlalchemy import update

from app.modules.exchange.models import ExchangeRate
from app.modules.wallet.models import Wallet
from app.modules.wallet.repository import WalletRepository


def test_locked_read_refreshes_stale_instance(TestingSession):
    """Regression test for the lost-update bug: a row already loaded (unlocked)
    into the identity map must be refreshed by the locked read, otherwise the
    FOR UPDATE lock protects a stale in-memory balance."""
    db = TestingSession()
    repo = WalletRepository(db)
    wallet = repo.create(user_id=1, currency="USD")
    wallet.balance_minor = 1000
    db.commit()

    # Simulate the pre-lock read that populates the identity map.
    loaded = repo.get(1, "USD")
    assert loaded.balance_minor == 1000

    # Change the underlying row without touching the ORM instance.
    db.execute(update(Wallet).where(Wallet.id == wallet.id).values(balance_minor=250))

    # The locked read must reflect the current value, not the stale 1000.
    relocked = repo.get_for_update(1, "USD")
    assert relocked is loaded
    assert relocked.balance_minor == 250
    db.close()


def test_get_or_create_is_idempotent(TestingSession):
    db = TestingSession()
    repo = WalletRepository(db)
    first = repo.get_or_create(user_id=7, currency="EUR")
    db.commit()
    second = repo.get_or_create(user_id=7, currency="EUR")
    assert first.id == second.id
    db.close()


def _fund(client, headers, currency="USD", amount="100.00"):
    client.post(
        "/api/v1/wallets/credit",
        json={"wallet_currency": currency, "amount": amount},
        headers=headers,
    )


def test_transfer_rejected_on_stale_rate(client, auth_headers, TestingSession):
    sender = auth_headers("stale_s@example.com")
    auth_headers("stale_r@example.com")
    _fund(client, sender, "USD", "100.00")

    db = TestingSession()
    db.execute(
        update(ExchangeRate)
        .where(ExchangeRate.quote == "EUR")
        .values(fetched_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    )
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/transfers",
        json={
            "recipient_email": "stale_r@example.com",
            "amount": "10.00",
            "from_currency": "USD",
            "to_currency": "EUR",
        },
        headers=sender,
    )
    assert resp.status_code == 503


def test_keyset_pagination_no_overlap(client, auth_headers):
    headers = auth_headers("ks@example.com")
    for _ in range(5):
        _fund(client, headers, "USD", "10.00")

    page1 = client.get(
        "/api/v1/transactions", params={"limit": 2}, headers=headers
    ).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"]

    page2 = client.get(
        "/api/v1/transactions",
        params={"limit": 2, "cursor": page1["next_cursor"]},
        headers=headers,
    ).json()
    assert len(page2["items"]) == 2

    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)
