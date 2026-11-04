from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.money import to_major
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.exchange.service import ExchangeError
from app.modules.wallet.models import Wallet
from app.modules.wallet.schemas import MoneyOperation, TransactionOut, WalletOut
from app.modules.wallet.service import (
    InsufficientFundsError,
    WalletError,
    WalletService,
)

router = APIRouter(prefix="/wallets", tags=["wallets"])


def _to_wallet_out(wallet: Wallet) -> WalletOut:
    return WalletOut(
        id=wallet.id,
        currency=wallet.currency,
        balance_minor=wallet.balance_minor,
        balance=to_major(wallet.balance_minor, wallet.currency),
        created_at=wallet.created_at,
    )


@router.get("", response_model=list[WalletOut])
def list_wallets(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WalletOut]:
    wallets = WalletService(db).list_wallets(current.id)
    return [_to_wallet_out(w) for w in wallets]


@router.post("/credit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def credit(
    op: MoneyOperation,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionOut:
    try:
        txn = WalletService(db).credit(current.id, op)
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return TransactionOut.model_validate(txn)


@router.post("/debit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def debit(
    op: MoneyOperation,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionOut:
    try:
        txn = WalletService(db).debit(current.id, op)
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except WalletError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return TransactionOut.model_validate(txn)
