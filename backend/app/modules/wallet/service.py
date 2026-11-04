from __future__ import annotations

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.money import convert_minor, to_major, to_minor
from app.modules.exchange.service import ExchangeService
from app.modules.wallet.models import (
    TXN_CREDIT,
    TXN_DEBIT,
    Transaction,
    Wallet,
)
from app.modules.wallet.repository import WalletRepository
from app.modules.wallet.schemas import MoneyOperation


class WalletError(Exception):
    pass


class InsufficientFundsError(WalletError):
    pass


class WalletService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WalletRepository(db)
        self.exchange = ExchangeService(db)

    def list_wallets(self, user_id: int) -> list[Wallet]:
        return self.repo.list_for_user(user_id)

    def get_or_create_wallet(self, user_id: int, currency: str) -> Wallet:
        return self.repo.get_or_create(user_id, currency)

    def credit(self, user_id: int, op: MoneyOperation) -> Transaction:
        return self._apply(user_id, op, sign=1, txn_type=TXN_CREDIT)

    def debit(self, user_id: int, op: MoneyOperation) -> Transaction:
        return self._apply(user_id, op, sign=-1, txn_type=TXN_DEBIT)

    # --- internals ------------------------------------------------------

    def _apply(
        self, user_id: int, op: MoneyOperation, sign: int, txn_type: str
    ) -> Transaction:
        wallet_ccy = op.wallet_ccy()
        amount_ccy = op.amount_ccy()

        if op.idempotency_key:
            existing = self.repo.find_by_idempotency_key(user_id, op.idempotency_key)
            if existing is not None:
                return existing

        # Ensure the wallet exists, then lock it for the balance mutation.
        self.get_or_create_wallet(user_id, wallet_ccy)
        wallet = self.repo.get_for_update(user_id, wallet_ccy)
        assert wallet is not None

        fx_rate: Decimal | None = None
        source_amount_minor: int | None = None
        source_currency: str | None = None

        if amount_ccy == wallet_ccy:
            amount_minor = to_minor(op.amount, wallet_ccy)
        else:
            snap = self.exchange.get_rate(amount_ccy, wallet_ccy)
            fx_rate = snap.rate
            source_currency = amount_ccy
            source_amount_minor = to_minor(op.amount, amount_ccy)
            amount_minor = convert_minor(source_amount_minor, amount_ccy, wallet_ccy, snap.rate)

        if sign < 0 and wallet.balance_minor < amount_minor:
            raise InsufficientFundsError(
                f"Insufficient {wallet_ccy} balance: have "
                f"{to_major(wallet.balance_minor, wallet_ccy)}, "
                f"need {to_major(amount_minor, wallet_ccy)}"
            )

        wallet.balance_minor += sign * amount_minor

        txn = Transaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=txn_type,
            amount_minor=sign * amount_minor,
            currency=wallet_ccy,
            fx_rate=fx_rate,
            source_amount_minor=source_amount_minor,
            source_currency=source_currency,
            reference=op.reference,
            idempotency_key=op.idempotency_key,
        )
        self.repo.add_transaction(txn)
        try:
            self.db.commit()
        except IntegrityError:
            # A concurrent request with the same idempotency key won the race;
            # return its committed result instead of applying twice.
            self.db.rollback()
            if op.idempotency_key:
                existing = self.repo.find_by_idempotency_key(user_id, op.idempotency_key)
                if existing is not None:
                    return existing
            raise
        self.db.refresh(txn)
        return txn
