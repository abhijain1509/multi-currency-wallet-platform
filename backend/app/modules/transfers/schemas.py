from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.core.currencies import validate_currency


class TransferRequest(BaseModel):
    recipient_email: EmailStr
    amount: Decimal = Field(gt=0)
    # Currency debited from the sender.
    from_currency: str
    # Currency credited to the recipient (converted if different).
    to_currency: str
    reference: str | None = Field(default=None, max_length=140)
    idempotency_key: str | None = Field(default=None, max_length=80)

    def from_ccy(self) -> str:
        return validate_currency(self.from_currency)

    def to_ccy(self) -> str:
        return validate_currency(self.to_currency)


class TransferResult(BaseModel):
    transfer_out_id: int
    transfer_in_id: int
    from_currency: str
    to_currency: str
    debited_minor: int
    credited_minor: int
    fx_rate: Decimal
