"""Imports every ORM model so that `Base.metadata` is fully populated before
`create_all` / Alembic autogeneration runs."""

from app.modules.auth.models import User  # noqa: F401
from app.modules.exchange.models import ExchangeRate  # noqa: F401
from app.modules.wallet.models import Transaction, Wallet  # noqa: F401
