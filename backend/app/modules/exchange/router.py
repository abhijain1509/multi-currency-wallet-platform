from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.exchange.schemas import ConversionQuote, RateOut
from app.modules.exchange.service import ExchangeError, ExchangeService

router = APIRouter(prefix="/exchange", tags=["exchange"])


@router.get("/rates", response_model=list[RateOut])
def list_rates(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[RateOut]:
    service = ExchangeService(db)
    base = settings.exchange_base_currency
    out: list[RateOut] = []
    for quote in settings.supported_currencies:
        try:
            snap = service.get_rate(base, quote)
        except ExchangeError:
            continue
        out.append(
            RateOut(
                base=base,
                quote=quote,
                rate=snap.rate,
                fetched_at=snap.fetched_at,
                stale=snap.stale,
            )
        )
    return out


@router.get("/quote", response_model=ConversionQuote)
def quote(
    from_currency: str = Query(alias="from"),
    to_currency: str = Query(alias="to"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversionQuote:
    try:
        snap = ExchangeService(db).get_rate(from_currency.upper(), to_currency.upper())
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ConversionQuote(
        from_currency=from_currency.upper(),
        to_currency=to_currency.upper(),
        rate=snap.rate,
        fetched_at=snap.fetched_at,
        stale=snap.stale,
    )


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        count = ExchangeService(db).refresh_rates()
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return {"refreshed": count}
