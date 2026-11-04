from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Multi-Currency Wallet Platform"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://wallet:wallet@db:5432/wallet"
    redis_url: str = "redis://cache:6379/0"

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Auth cookie: the JWT is delivered as an httpOnly cookie so browser JS can
    # never read it (XSS-resistant). `cookie_secure` must be True in production.
    cookie_name: str = "access_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # Free, keyless FX provider. Override in prod with a paid, SLA-backed source.
    exchange_api_url: str = "https://open.er-api.com/v6/latest"
    exchange_base_currency: str = "USD"
    exchange_refresh_seconds: int = 3600
    # How long a cached rate is considered fresh before we flag it as stale.
    exchange_rate_ttl_seconds: int = 7200
    # Refuse to move money between users on a stale rate (avoids mispricing).
    fx_reject_stale_on_transfer: bool = True

    supported_currencies: list[str] = ["USD", "EUR", "GBP", "INR", "JPY"]

    # Profile photo uploads stored on disk and served as static media.
    upload_dir: str = "uploads"
    media_url_prefix: str = "/api/v1/media"
    max_upload_bytes: int = 2 * 1024 * 1024  # 2 MB

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
