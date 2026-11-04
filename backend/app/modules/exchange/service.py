from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.exchange.models import ExchangeRate

logger = logging.getLogger(__name__)

try:  # redis is optional — the service degrades gracefully to the DB fallback.
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib = None


@dataclass
class RateSnapshot:
    rate: Decimal
    fetched_at: datetime
    stale: bool


class ExchangeError(Exception):
    pass


# Lazily-initialised, process-wide client backed by redis-py's connection pool.
# Avoids opening a fresh TCP connection on every rate lookup.
_redis_singleton = None
_redis_initialized = False


def _redis_client():
    global _redis_singleton, _redis_initialized
    if redis_lib is None:
        return None
    if not _redis_initialized:
        _redis_initialized = True
        try:
            client = redis_lib.Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1
            )
            client.ping()
            _redis_singleton = client
        except Exception:  # pragma: no cover - cache is best-effort
            logger.warning("Redis unavailable; using DB fallback for FX rates")
            _redis_singleton = None
    return _redis_singleton


class ExchangeService:
    """Resolves FX rates with a cache-first, DB-fallback, provider-last strategy.

    This ordering is what keeps the platform available during provider downtime:
    we never block a transaction on the upstream call at request time.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.base = settings.exchange_base_currency

    # --- public API -----------------------------------------------------

    def get_rate(self, from_currency: str, to_currency: str) -> RateSnapshot:
        if from_currency == to_currency:
            return RateSnapshot(Decimal(1), datetime.now(timezone.utc), stale=False)

        base_from = self._base_rate(from_currency)
        base_to = self._base_rate(to_currency)
        rate = base_to.rate / base_from.rate
        stale = base_from.stale or base_to.stale
        fetched_at = min(base_from.fetched_at, base_to.fetched_at)
        return RateSnapshot(rate=rate, fetched_at=fetched_at, stale=stale)

    def refresh_rates(self) -> int:
        """Fetch fresh rates from the provider and persist them. Returns count."""
        rates = self._fetch_from_provider()
        now = datetime.now(timezone.utc)
        cache = _redis_client()
        count = 0
        for quote, value in rates.items():
            if quote not in settings.supported_currencies:
                continue
            self._upsert_db_rate(self.base, quote, value, now)
            if cache is not None:
                cache.hset(self._key(quote), mapping={"rate": str(value), "ts": now.isoformat()})
                cache.expire(self._key(quote), settings.exchange_rate_ttl_seconds * 2)
            count += 1
        self.db.commit()
        logger.info("Refreshed %d FX rates", count, extra={"extra_fields": {"count": count}})
        return count

    # --- internals ------------------------------------------------------

    def _base_rate(self, currency: str) -> RateSnapshot:
        if currency == self.base:
            return RateSnapshot(Decimal(1), datetime.now(timezone.utc), stale=False)

        cached = self._from_cache(currency)
        if cached is not None:
            return cached

        persisted = self._from_db(currency)
        if persisted is not None:
            return persisted

        raise ExchangeError(
            f"No rate available for {self.base}->{currency}. Trigger a refresh."
        )

    def _from_cache(self, currency: str) -> RateSnapshot | None:
        cache = _redis_client()
        if cache is None:
            return None
        data = cache.hgetall(self._key(currency))
        if not data:
            return None
        fetched_at = datetime.fromisoformat(data["ts"])
        return RateSnapshot(
            rate=Decimal(data["rate"]),
            fetched_at=fetched_at,
            stale=self._is_stale(fetched_at),
        )

    def _from_db(self, currency: str) -> RateSnapshot | None:
        row = self.db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.base == self.base, ExchangeRate.quote == currency
            )
        )
        if row is None:
            return None
        return RateSnapshot(
            rate=Decimal(str(row.rate)),
            fetched_at=self._as_aware(row.fetched_at),
            stale=self._is_stale(row.fetched_at),
        )

    def _upsert_db_rate(self, base: str, quote: str, value: Decimal, now: datetime) -> None:
        row = self.db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.base == base, ExchangeRate.quote == quote
            )
        )
        if row is None:
            self.db.add(ExchangeRate(base=base, quote=quote, rate=value, fetched_at=now))
        else:
            row.rate = value
            row.fetched_at = now

    def _fetch_from_provider(self) -> dict[str, Decimal]:
        url = f"{settings.exchange_api_url}/{self.base}"
        try:
            resp = httpx.get(url, timeout=10.0)
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExchangeError(f"FX provider request failed: {exc}") from exc
        rates = body.get("rates")
        if not isinstance(rates, dict):
            raise ExchangeError("FX provider returned an unexpected payload")
        return {k: Decimal(str(v)) for k, v in rates.items()}

    def _is_stale(self, fetched_at: datetime) -> bool:
        fetched_at = self._as_aware(fetched_at)
        age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        return age > settings.exchange_rate_ttl_seconds

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _key(self, currency: str) -> str:
        return f"fx:{self.base}:{currency}"
