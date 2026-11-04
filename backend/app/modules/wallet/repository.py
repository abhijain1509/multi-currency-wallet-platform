from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.wallet.models import Transaction, Wallet


class WalletRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: int) -> list[Wallet]:
        return list(
            self.db.scalars(select(Wallet).where(Wallet.user_id == user_id)).all()
        )

    def get(self, user_id: int, currency: str) -> Wallet | None:
        return self.db.scalar(
            select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == currency)
        )

    def get_for_update(self, user_id: int, currency: str) -> Wallet | None:
        """Row-locked read used inside transfer/credit/debit transactions to
        serialize concurrent balance changes (skipped on SQLite in tests).

        `populate_existing` forces SQLAlchemy to overwrite any value already in
        the identity map with the row read *under the lock* — without it a
        pre-lock read would leave a stale balance in memory and cause lost
        updates under concurrency.
        """
        stmt = (
            select(Wallet)
            .where(Wallet.user_id == user_id, Wallet.currency == currency)
            .execution_options(populate_existing=True)
        )
        if self.db.bind and self.db.bind.dialect.name != "sqlite":
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def create(self, user_id: int, currency: str) -> Wallet:
        wallet = Wallet(user_id=user_id, currency=currency, balance_minor=0)
        self.db.add(wallet)
        self.db.flush()
        return wallet

    def get_or_create(self, user_id: int, currency: str) -> Wallet:
        """Return the user's wallet for a currency, creating it if missing.

        The insert runs inside a SAVEPOINT so that a concurrent creator losing
        the `UNIQUE(user_id, currency)` race is handled by re-reading the row
        the winner committed, instead of failing the whole transaction.
        """
        existing = self.get(user_id, currency)
        if existing is not None:
            return existing
        try:
            with self.db.begin_nested():
                wallet = Wallet(user_id=user_id, currency=currency, balance_minor=0)
                self.db.add(wallet)
                self.db.flush()
            return wallet
        except IntegrityError:
            created = self.get(user_id, currency)
            if created is None:
                raise
            return created

    def add_transaction(self, txn: Transaction) -> Transaction:
        self.db.add(txn)
        self.db.flush()
        return txn

    def find_by_idempotency_key(self, user_id: int, key: str) -> Transaction | None:
        return self.db.scalar(
            select(Transaction).where(
                Transaction.user_id == user_id, Transaction.idempotency_key == key
            )
        )
