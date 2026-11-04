from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Managed Postgres providers (e.g. Render) hand out legacy `postgres://` URLs
# that SQLAlchemy 2.0 rejects; normalise to the psycopg2 driver form.
_database_url = settings.database_url
if _database_url.startswith("postgres://"):
    _database_url = _database_url.replace("postgres://", "postgresql+psycopg2://", 1)

# SQLite (used by tests) needs a special connect arg; Postgres does not.
_connect_args = (
    {"check_same_thread": False} if _database_url.startswith("sqlite") else {}
)

engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
