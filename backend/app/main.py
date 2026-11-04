from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

import app.models  # noqa: F401  (register all ORM models)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging import configure_logging, new_request_id, request_id_ctx
from app.modules.auth.router import router as auth_router
from app.modules.exchange.router import router as exchange_router
from app.modules.exchange.service import ExchangeError, ExchangeService
from app.modules.history.router import router as history_router
from app.modules.transfers.router import router as transfers_router
from app.modules.wallet.router import router as wallet_router

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_class"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    # Fail fast rather than booting production with the insecure default secret.
    if settings.environment == "production" and settings.jwt_secret == "change-me-in-prod":
        raise RuntimeError("JWT_SECRET must be overridden in production")
    # Dev convenience: create tables and seed FX rates. Use Alembic in prod.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ExchangeService(db).refresh_rates()
    except ExchangeError as exc:
        logger.warning("Initial FX refresh failed: %s", exc)
    finally:
        db.close()
    yield


# Expose interactive docs / OpenAPI schema only outside production.
_docs_enabled = settings.environment != "production"
app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or new_request_id()
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # An unhandled exception becomes a 500 downstream; count it here so the
        # 5xx we most want to alert on is never missed.
        _record(request, "5xx", start)
        raise
    _record(request, f"{response.status_code // 100}xx", start)
    response.headers["x-request-id"] = request_id
    if response.status_code >= 400:
        logger.warning(
            "Request completed with error status",
            extra={"extra_fields": {"status": response.status_code}},
        )
    return response


def _record(request: Request, status_class: str, start: float) -> None:
    # Use the matched route template (resolved after routing) to keep metric
    # label cardinality bounded; unmatched paths are bucketed together.
    route = request.scope.get("route")
    path = getattr(route, "path", None) or "<unmatched>"
    REQUEST_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    REQUEST_COUNT.labels(request.method, path, status_class).inc()


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready() -> Response:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        return JSONResponse(status_code=503, content={"status": "unavailable", "detail": str(exc)})
    return JSONResponse(status_code=200, content={"status": "ready"})


@app.get("/metrics", tags=["ops"])
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


api_routers = [
    auth_router,
    wallet_router,
    exchange_router,
    transfers_router,
    history_router,
]
for r in api_routers:
    app.include_router(r, prefix="/api/v1")

# Serve uploaded profile photos as static media (created if missing).
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.media_url_prefix,
    StaticFiles(directory=settings.upload_dir),
    name="media",
)
