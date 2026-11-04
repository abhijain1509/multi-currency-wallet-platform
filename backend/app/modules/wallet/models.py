from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Ledger entry types.
TXN_CREDIT = "credit"
TXN_DEBIT = "debit"
TXN_TRANSFER_IN = "transfer_in"
TXN_TRANSFER_OUT = "transfer_out"


class Wallet(Base):
    """A single-currency balance held by a user. A user holds one wallet per
    currency they transact in."""

    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "currency", name="uq_wallet_user_currency"),
        CheckConstraint("balance_minor >= 0", name="ck_wallet_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Balance stored in integer minor units (cents/paise/yen) — never floats.
    balance_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Transaction(Base):
    """Immutable ledger entry. Every balance change produces exactly one row,
    carrying the FX rate used so conversions are fully traceable."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_txn_idempotency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Signed amount in the wallet's currency minor units (+credit / -debit).
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # FX rate applied when the source amount differed from the wallet currency.
    fx_rate: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    source_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    counterparty_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    reference: Mapped[str | None] = mapped_column(String(140), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc)
    )
