from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.exchange.service import ExchangeError
from app.modules.transfers.schemas import TransferRequest, TransferResult
from app.modules.transfers.service import TransferError, TransferService
from app.modules.wallet.service import InsufficientFundsError

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferResult, status_code=status.HTTP_201_CREATED)
def create_transfer(
    req: TransferRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransferResult:
    try:
        return TransferService(db).transfer(current.id, req)
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except TransferError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
