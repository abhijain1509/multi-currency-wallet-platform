from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.history.schemas import TransactionPage
from app.modules.history.service import HistoryService
from app.modules.wallet.schemas import TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
def list_transactions(
    currency: str | None = Query(default=None),
    type: str | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    cursor: str | None = Query(default=None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionPage:
    rows, total, next_cursor = HistoryService(db).list_transactions(
        current.id,
        currency=currency,
        txn_type=type,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
        cursor=cursor,
    )
    return TransactionPage(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
        next_cursor=next_cursor,
    )
