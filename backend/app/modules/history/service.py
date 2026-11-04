from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.wallet.models import Transaction


def _encode_cursor(txn: Transaction) -> str:
    return f"{txn.created_at.isoformat()}|{txn.id}"


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    ts_str, _, id_str = cursor.rpartition("|")
    return datetime.fromisoformat(ts_str), int(id_str)


class HistoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_transactions(
        self,
        user_id: int,
        *,
        currency: str | None = None,
        txn_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
        cursor: str | None = None,
    ) -> tuple[list[Transaction], int, str | None]:
        filters = [Transaction.user_id == user_id]
        if currency:
            filters.append(Transaction.currency == currency.upper())
        if txn_type:
            filters.append(Transaction.type == txn_type)
        if start:
            filters.append(Transaction.created_at >= start)
        if end:
            filters.append(Transaction.created_at <= end)

        total = self.db.scalar(
            select(func.count()).select_from(Transaction).where(*filters)
        )

        query = (
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        )
        if cursor:
            # Keyset pagination: fetch rows strictly "older" than the cursor,
            # which stays fast regardless of how deep the user pages.
            c_ts, c_id = _decode_cursor(cursor)
            query = query.where(
                or_(
                    Transaction.created_at < c_ts,
                    and_(Transaction.created_at == c_ts, Transaction.id < c_id),
                )
            ).limit(limit)
        else:
            query = query.limit(limit).offset(offset)

        rows = list(self.db.scalars(query).all())
        next_cursor = _encode_cursor(rows[-1]) if len(rows) == limit else None
        return rows, int(total or 0), next_cursor
