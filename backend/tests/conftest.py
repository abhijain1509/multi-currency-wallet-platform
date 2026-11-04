from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app
from app.modules.exchange.models import ExchangeRate
from app.modules.exchange.service import ExchangeService

# Fixed USD-based rates so tests never touch the network.
_FIXTURE_RATES = {"USD": "1.0", "EUR": "0.5", "GBP": "0.8", "INR": "80.0", "JPY": "100.0"}


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def TestingSession(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _seed_rates(TestingSession):
    db = TestingSession()
    now = datetime.now(timezone.utc)
    for quote, rate in _FIXTURE_RATES.items():
        db.add(ExchangeRate(base="USD", quote=quote, rate=rate, fetched_at=now))
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(
        ExchangeService,
        "_fetch_from_provider",
        lambda self: {k: __import__("decimal").Decimal(v) for k, v in _FIXTURE_RATES.items()},
    )


@pytest.fixture
def client(TestingSession):
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Instantiated without a `with` block so the network-touching lifespan is skipped.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    def _register(email: str, currency: str = "USD") -> dict[str, str]:
        resp = client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": "supersecret1",
                "full_name": "Test User",
                "default_currency": currency,
            },
        )
        assert resp.status_code == 201, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _register
