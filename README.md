# Multi-Currency Wallet Platform

A production-minded wallet platform supporting account creation, multi-currency
wallets, currency conversion, user-to-user transfers, and transaction history.

- **Backend:** Python / FastAPI (modular monolith, clean architecture)
- **Frontend:** React (Vite)
- **Data:** PostgreSQL (ledger + balances), Redis (FX rate cache)
- **Delivery:** Docker, docker-compose, GitHub Actions CI

## Features

- Auth: signup / login (JWT), profile with editable photo + default currency
- Wallets: credit / debit in any supported currency, with conversion
- Currency exchange: third-party provider with cache-first refresh and per-transaction rate traceability
- Transfers: user-to-user, cross-currency, atomic with consistency controls
- Transaction history: filtering (type, currency, date) + pagination
- Ops: `/health`, `/ready`, `/metrics` (Prometheus), structured JSON logs, request IDs

## Setup

Prerequisites: Docker + Docker Compose. (For local dev without Docker: Python 3.11, Node 20.)

### Run with Docker (recommended)

```bash
cp .env.example .env     # adjust JWT_SECRET for anything non-local
docker compose up --build
```

- Frontend: http://localhost:8080
- API: reached only through the frontend proxy at http://localhost:8080/api/v1
  (the backend, DB, and cache are **not** published to the host).
- Swagger UI is available in dev only (disabled when `ENVIRONMENT=production`).
  To explore it, run the backend locally (below) and open http://localhost:8000/docs.

### Run locally (without Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Defaults expect Postgres+Redis; for a quick start use SQLite:
export DATABASE_URL="sqlite:///./dev.db"
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev     # proxies /api -> http://localhost:8000
```

## Tests

```bash
# Backend
cd backend && source .venv/bin/activate
pytest -q --cov=app

# Frontend
cd frontend && npm test
```

26 backend unit + integration tests cover money math, auth, wallet credit/debit
(incl. conversion + idempotency), transfers (incl. cross-currency, insufficient
funds, self-transfer, idempotency), locking/concurrency, history
pagination/filtering, and health/metrics. The frontend has Vitest + React Testing
Library smoke tests for money formatting and the auth form.

## Deployment

The project is fully containerized and portable to any container host
(Render / Railway / Fly.io / ECS / a VM running `docker compose`).

### One-click-ish on Render (free tier)

A [`render.yaml`](render.yaml) blueprint provisions managed **Postgres** + the
**backend** + the **frontend**:

1. Push this repo to GitHub.
2. In Render: **New → Blueprint** → select the repo → **Apply**. This creates the
   database and both services; `JWT_SECRET` is generated, `DATABASE_URL` is wired
   from the DB, and `ENVIRONMENT=production` (which disables the API docs).
3. When the **backend** finishes deploying, copy its URL
   (e.g. `https://wallet-backend.onrender.com`) and set the **frontend** service's
   `BACKEND_ORIGIN` env var to it, then redeploy the frontend.
4. The **frontend URL** is your public deployment URL — the browser only ever
   talks to it; nginx reverse-proxies `/api` to the backend (same-origin cookies,
   no CORS). Redis is optional (the app degrades to the DB-backed FX fallback).

The images honour `$PORT` and `BACKEND_ORIGIN`, so the exact same containers run
locally (`docker compose`) and in the cloud with no code changes.

### Generic container host / VM

1. Provision managed Postgres (and optionally Redis); set `DATABASE_URL`,
   `JWT_SECRET`, `COOKIE_SECURE=true` (and `REDIS_URL` if used).
2. `docker compose build` and push images (CI builds them on every push to `main`).
3. Run the stack, e.g. `docker compose -f infra/docker-compose.prod.yml up -d`.
4. Expose only the frontend (port 80/443) behind TLS; it proxies `/api` to the
   backend, which stays on the internal network.

> The app auto-creates tables on first boot; use Alembic migrations for a real
> production rollout.

## API overview

All under `/api/v1`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/signup` | Register + receive JWT |
| POST | `/auth/login` | Login + receive JWT |
| GET/PATCH | `/auth/profile` | View / update profile |
| GET | `/wallets` | List wallets + balances |
| POST | `/wallets/credit` · `/wallets/debit` | Credit / debit (with conversion) |
| GET | `/exchange/rates` · `/exchange/quote` | Rates / conversion quote |
| POST | `/exchange/refresh` | Force an FX refresh |
| POST | `/transfers` | Cross-currency user-to-user transfer |
| GET | `/transactions` | History (filter + offset or keyset `cursor`) |

## Assumptions

- Supported currencies: USD, EUR, GBP, INR, JPY (easily extended in `core/money.py` + config).
- FX source is the free, keyless `open.er-api.com`; swap for an SLA-backed provider in prod.
- One wallet per user per currency, created lazily on first use.
- A user may only transact on their own wallets; JWT subject = user id.

## Security

- **Auth token in an httpOnly cookie** — the JWT is set as an `HttpOnly`,
  `SameSite`, (optionally `Secure`) cookie and is never stored in or readable
  from browser JS, so it can't be exfiltrated via XSS. The SPA persists only
  non-sensitive display info; passwords are only ever bcrypt-hashed, never stored
  in plaintext.
- **No directly public API** — in Docker only the frontend (port 80) is
  published; the backend, PostgreSQL, and Redis have no host port mapping and are
  reachable solely over the internal network. The browser talks to the API
  through the nginx `/api` reverse proxy (same-origin, so cookies flow without
  cross-site exposure).
- **API schema off in production** — Swagger / ReDoc / `openapi.json` are disabled
  when `ENVIRONMENT=production`.
- **No client-side logging** of requests, responses, or credentials; baseline
  response headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
  are set at the proxy.

## Trade-offs

- **Modular monolith over microservices** — money correctness (atomic cross-currency transfer) is far simpler and safer in one ACID transaction. Module boundaries are drawn so a hot module could be extracted later. See [ARCHITECTURE.md](ARCHITECTURE.md).
- **Dev auto-`create_all`** for fast startup; production should use Alembic migrations.
- **Sync SQLAlchemy** for clarity/reliability over async throughput at this scale.

## Known limitations

- No refresh-token rotation / token revocation (short-lived access tokens only).
- Photo upload accepts a URL rather than handling binary upload to object storage.
- FX refresh runs on startup + on-demand; a scheduled worker is described in ARCHITECTURE but not wired.
- No rate limiting at the app layer (expected at the gateway/ingress).

Hardening already applied (see [ARCHITECTURE.md](ARCHITECTURE.md) → Challenges & Fixes):
locked reads refresh under the lock (no lost updates), idempotency races return the
original result, DB-level non-negative balance check, stale-FX transfers are rejected,
and history supports keyset pagination.
