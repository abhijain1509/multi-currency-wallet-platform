from app.modules.wallet.schemas import TransactionOut
from pydantic import BaseModel


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int
    # Opaque cursor for keyset pagination; null when there is no further page.
    next_cursor: str | None = None
