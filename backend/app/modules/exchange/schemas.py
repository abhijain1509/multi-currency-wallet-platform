from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RateOut(BaseModel):
    base: str
    quote: str
    rate: Decimal
    fetched_at: datetime
    stale: bool


class ConversionQuote(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal
    fetched_at: datetime
    stale: bool
