from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.currencies import validate_currency


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency: str
    balance_minor: int
    balance: Decimal
    created_at: datetime


class MoneyOperation(BaseModel):
    """Credit or debit a wallet. `amount` is in `amount_currency`; it is
    converted into `wallet_currency` if they differ."""

    wallet_currency: str
    amount: Decimal = Field(gt=0)
    amount_currency: str | None = None
    reference: str | None = Field(default=None, max_length=140)
    idempotency_key: str | None = Field(default=None, max_length=80)

    def wallet_ccy(self) -> str:
        return validate_currency(self.wallet_currency)

    def amount_ccy(self) -> str:
        return validate_currency(self.amount_currency or self.wallet_currency)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_id: int
    type: str
    amount_minor: int
    currency: str
    fx_rate: Decimal | None
    source_amount_minor: int | None
    source_currency: str | None
    counterparty_user_id: int | None
    reference: str | None
    created_at: datetime
