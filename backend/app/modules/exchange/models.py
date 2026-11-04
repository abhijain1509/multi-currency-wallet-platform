from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExchangeRate(Base):
    """Last-known rate per currency pair, used as a durable fallback when the
    cache or the upstream provider is unavailable (conversion traceability)."""

    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("base", "quote", name="uq_rate_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    base: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    quote: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    rate: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
