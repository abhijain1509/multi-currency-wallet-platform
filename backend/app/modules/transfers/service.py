from __future__ import annotations

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.money import convert_minor, to_major, to_minor
from app.modules.auth.repository import UserRepository
from app.modules.exchange.service import ExchangeError, ExchangeService
from app.modules.transfers.schemas import TransferRequest, TransferResult
from app.modules.wallet.models import (
    TXN_TRANSFER_IN,
    TXN_TRANSFER_OUT,
    Transaction,
)
from app.modules.wallet.repository import WalletRepository
from app.modules.wallet.service import InsufficientFundsError, WalletError


class TransferError(WalletError):
    pass


class TransferService:
    """Executes a user-to-user, cross-currency transfer as a single atomic unit.

    Consistency controls:
      * both wallets are row-locked (SELECT ... FOR UPDATE) to serialize writes;
      * debit + credit + both ledger rows commit in one DB transaction;
      * an idempotency key makes retries safe (no double-spend).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.wallets = WalletRepository(db)
        self.users = UserRepository(db)
        self.exchange = ExchangeService(db)

    def transfer(self, sender_id: int, req: TransferRequest) -> TransferResult:
        from_ccy = req.from_ccy()
        to_ccy = req.to_ccy()

        if req.idempotency_key:
            existing = self.wallets.find_by_idempotency_key(sender_id, req.idempotency_key)
            if existing is not None:
                return self._result_from_existing(existing)

        recipient = self.users.get_by_email(req.recipient_email)
        if recipient is None:
            raise TransferError("Recipient not found")
        if recipient.id == sender_id:
            raise TransferError("Cannot transfer to yourself")

        # Resolve the FX rate up front so it is recorded identically on both legs.
        snap = self.exchange.get_rate(from_ccy, to_ccy)
        if snap.stale and settings.fx_reject_stale_on_transfer:
            raise ExchangeError(
                "FX rate is stale; transfer rejected to avoid mispricing"
            )
        debit_minor = to_minor(req.amount, from_ccy)
        credit_minor = convert_minor(debit_minor, from_ccy, to_ccy, snap.rate)

        # Ensure both wallets exist before locking them.
        self._ensure_wallet(sender_id, from_ccy)
        self._ensure_wallet(recipient.id, to_ccy)

        # Lock in a stable order (by user id) to avoid deadlocks.
        first, second = sorted([sender_id, recipient.id])
        self.wallets.get_for_update(first, from_ccy if first == sender_id else to_ccy)
        self.wallets.get_for_update(second, from_ccy if second == sender_id else to_ccy)

        sender_wallet = self.wallets.get(sender_id, from_ccy)
        recipient_wallet = self.wallets.get(recipient.id, to_ccy)
        assert sender_wallet is not None and recipient_wallet is not None

        if sender_wallet.balance_minor < debit_minor:
            raise InsufficientFundsError(
                f"Insufficient {from_ccy} balance: have "
                f"{to_major(sender_wallet.balance_minor, from_ccy)}, "
                f"need {req.amount}"
            )

        sender_wallet.balance_minor -= debit_minor
        recipient_wallet.balance_minor += credit_minor

        out_txn = Transaction(
            user_id=sender_id,
            wallet_id=sender_wallet.id,
            type=TXN_TRANSFER_OUT,
            amount_minor=-debit_minor,
            currency=from_ccy,
            fx_rate=snap.rate,
            source_amount_minor=credit_minor,
            source_currency=to_ccy,
            counterparty_user_id=recipient.id,
            reference=req.reference,
            idempotency_key=req.idempotency_key,
        )
        in_txn = Transaction(
            user_id=recipient.id,
            wallet_id=recipient_wallet.id,
            type=TXN_TRANSFER_IN,
            amount_minor=credit_minor,
            currency=to_ccy,
            fx_rate=snap.rate,
            source_amount_minor=debit_minor,
            source_currency=from_ccy,
            counterparty_user_id=sender_id,
            reference=req.reference,
        )
        self.wallets.add_transaction(out_txn)
        self.wallets.add_transaction(in_txn)
        try:
            self.db.commit()
        except IntegrityError:
            # Concurrent retry with the same idempotency key won the race.
            self.db.rollback()
            if req.idempotency_key:
                existing = self.wallets.find_by_idempotency_key(
                    sender_id, req.idempotency_key
                )
                if existing is not None:
                    return self._result_from_existing(existing)
            raise
        self.db.refresh(out_txn)
        self.db.refresh(in_txn)

        return TransferResult(
            transfer_out_id=out_txn.id,
            transfer_in_id=in_txn.id,
            from_currency=from_ccy,
            to_currency=to_ccy,
            debited_minor=debit_minor,
            credited_minor=credit_minor,
            fx_rate=snap.rate,
        )

    def _ensure_wallet(self, user_id: int, currency: str) -> None:
        self.wallets.get_or_create(user_id, currency)

    def _result_from_existing(self, out_txn: Transaction) -> TransferResult:
        return TransferResult(
            transfer_out_id=out_txn.id,
            transfer_in_id=out_txn.id,
            from_currency=out_txn.currency,
            to_currency=out_txn.source_currency or out_txn.currency,
            debited_minor=abs(out_txn.amount_minor),
            credited_minor=out_txn.source_amount_minor or abs(out_txn.amount_minor),
            fx_rate=Decimal(str(out_txn.fx_rate or 1)),
        )
