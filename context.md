# Project Context — Multi-Currency Wallet Platform

A single, start-to-end record of what was built, why, and every review/fix round.
Use this as the onboarding brief for the repository.

---

## 1. The challenge

Build a **production-minded Multi-Currency Wallet Platform** demonstrating
architecture, backend, frontend, testing, delivery/DevOps, and scalability.

Functional scope:
- **Authentication:** signup / login / profile (photo + editable default currency)
- **Wallet:** credit / debit in any currency with conversion
- **Currency exchange:** third-party integration with automated refresh + conversion traceability
- **Transfers:** user-to-user, cross-currency, with consistency controls
- **Transaction history:** filtering + pagination

Technical expectations: clean architecture + domain modelling, API/data design,
security + validation, unit + integration tests, error handling/reliability,
Dockerized delivery, CI/CD, logging/monitoring/health checks, and a design note on
scaling to 500k users / 20k DAU / 100 TPS with FX-provider downtime.

Evaluation weighting: Architecture 25%, Backend 20%, Frontend 15%, Testing 15%,
Delivery & DevOps 10%, Scalability 10%, Communication 5%. Target effort 6–10h.

---

## 2. The key architectural decision — modular monolith, not microservices

The initial idea was "separate microservices for frontend, backend, and DB." That
was reframed and rejected:

- "Frontend / backend / DB as microservices" is just a **3-tier deployment**, not
  microservices. Real microservices split the backend *by domain*, each with its
  own DB.
- A cross-currency **transfer must debit one wallet and credit another atomically**.
  In a monolith this is one ACID transaction with row locks. Split across services
  it becomes a distributed transaction (sagas/outbox/idempotency) — far more code
  and the biggest source of money-correctness bugs.
- At 100 TPS the scaling benefit of microservices is unnecessary; the cost
  (network failure modes, gateway, inter-service auth, data duplication) is real.

**Chosen design:** a **modular monolith** — one FastAPI app partitioned into
independent domain modules that talk through service interfaces and never reach
into each other's tables, so a hot module (e.g. exchange) can be extracted into a
service later with minimal change. The microservices *thinking* is demonstrated in
the Scale Exercise without paying to build it.

---

## 3. Tech stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (sync), Pydantic v2,
  python-jose (JWT), passlib/bcrypt, httpx, redis, prometheus-client.
- **Frontend:** React 18 + Vite, react-router-dom; Vitest + React Testing Library.
- **Data:** PostgreSQL (balances + ledger), Redis (FX rate cache).
- **Delivery:** Docker, docker-compose, nginx (SPA + `/api` proxy), GitHub Actions CI.

---

## 4. Repository structure

```
abhi-test/
├── backend/
│   ├── app/
│   │   ├── core/        config, database, security, money, currencies, logging
│   │   ├── modules/
│   │   │   ├── auth/      users, signup/login/profile, JWT cookie dependency
│   │   │   ├── wallet/    balances, credit/debit, ledger, idempotency, locking
│   │   │   ├── exchange/  FX rates: cache → DB → provider, refresh
│   │   │   ├── transfers/ atomic cross-currency user-to-user transfer
│   │   │   └── history/   filtering + offset/keyset pagination
│   │   ├── models.py     registers all ORM models
│   │   └── main.py       app wiring, middleware, health/ready/metrics
│   ├── tests/            29 unit + integration tests
│   ├── Dockerfile · requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js        fetch wrapper (cookie auth), api object
│   │   ├── lib/money.js         currencies + Intl money formatting (+ test)
│   │   ├── components/ErrorBoundary.jsx
│   │   ├── pages/               Login, Dashboard, Transfer, History (+ Login test)
│   │   ├── App.jsx · main.jsx · styles.css
│   ├── Dockerfile · nginx.conf · vite.config.js · package.json · .env.example
├── infra/               prod compose overlay + deploy notes
├── .github/workflows/   CI: backend tests+cov, frontend test+build, docker build
├── docker-compose.yml   db · cache · backend · frontend (only frontend published)
├── README.md · ARCHITECTURE.md · AI_USAGE.md · context.md · .env.example
```

Each backend module follows **router → service → repository → model** layering;
Pydantic schemas (API boundary) are kept separate from SQLAlchemy models
(persistence).

---

## 5. Domain & data model

- **User** — email (unique), bcrypt password hash, full name, photo URL, default currency.
- **Wallet** — `UNIQUE(user_id, currency)`, `balance_minor` as integer minor units,
  `CHECK(balance_minor >= 0)`.
- **Transaction** — immutable ledger row per balance change: signed `amount_minor`,
  `currency`, applied `fx_rate`, source amount/currency, counterparty, and
  `UNIQUE(user_id, idempotency_key)`. Indexed on `(user_id, created_at)`.
- **ExchangeRate** — last-known rate per `(base, quote)` pair, used as the durable
  fallback.

Every balance mutation writes exactly one ledger row → balances are reconstructable
and conversions are fully traceable.

---

## 6. Correctness foundations

- **Money as integer minor units** (cents/paise/yen); `Decimal` only for major↔minor
  and FX math; banker's rounding (`ROUND_HALF_EVEN`).
- **Idempotency keys** on credit/debit/transfer; retries return the original result.
- **Atomic transfers:** both wallets row-locked (`SELECT ... FOR UPDATE`) in stable
  order (by user id) to avoid deadlocks; debit + credit + both ledger rows commit in
  one transaction.
- **Exchange resilience:** request-time rate resolution is **Redis cache → DB
  last-known → error**; the provider is never called synchronously on the money
  path; stale rates are flagged and transfers are rejected beyond the TTL.

---

## 7. Review & fix history (chronological)

### Round A — System-architect review (concurrency & locking)
- **Lost update despite `FOR UPDATE` (critical):** code did an unlocked `get()`
  (populating SQLAlchemy's identity map) before the locked read, so the lock
  protected a stale in-memory balance. **Fixed** with
  `.execution_options(populate_existing=True)`.
- **Idempotency check-then-act race:** concurrent duplicates hit the unique
  constraint → unhandled 500. **Fixed** by catching `IntegrityError`, rolling back,
  returning the original.
- **Negative balance only in app code:** **added** DB-level `CHECK(balance_minor >= 0)`.

### Round B — Hardening wins
- **Stale-FX transfer guard** — reject transfers on a rate stale beyond the TTL.
- **Keyset pagination** — history accepts an opaque `cursor` + returns `next_cursor`
  (offset still supported).
- **Prod secret guard** — app refuses to boot in production with the default `JWT_SECRET`.
- **Regression tests** — locked-read refresh, stale-rate rejection, keyset no-overlap.

### Round C — Backend-engineer review
- **B1 Concurrent first-use wallet creation → 500:** `get()`→`create()` race at
  flush time. **Fixed** with `WalletRepository.get_or_create` using a SAVEPOINT and
  conflict re-read.
- **I1 Redis connect-per-call:** **replaced** with a process-wide pooled client.
- **I2 Metrics label cardinality:** label now uses the matched route template
  (post-routing) and buckets unmatched paths as `<unmatched>`.
- **I3 Unhandled exceptions uncounted:** middleware now counts them as `5xx`.
- **M1 Duplicated currency validation:** centralized in `core/currencies.py`.

### Round D — Frontend-engineer review
- **U1** 401 handling → clear session + redirect to login.
- **U2** No double-submit: buttons disabled while in-flight.
- **U3** Human-readable money via `Intl.NumberFormat` (no raw minor units in UI).
- **U4** Loading states.
- **R1** Tables in `overflow-x` wrappers + a mobile media query.
- **R2** 16px form controls (stop iOS zoom-on-focus).
- **A1–A4** Label associations, real `<button>` toggle, `role="alert"`,
  `ErrorBoundary`, crash-safe `getUser()`.
- **Env + DRY:** `frontend/.env.example`, centralized currency list.
- **Tests:** Vitest + RTL (money formatting + Login smoke).

### Round E — Security hardening (credentials & surface area)
- **JWT in an `HttpOnly`/`SameSite` (+`Secure` in prod) cookie** — never in JS
  storage; SPA keeps only non-sensitive display info. Auth reads cookie or
  `Authorization` header (header wins). Added `POST /auth/logout`.
- **No directly public API** — Docker publishes only the frontend; backend/DB/cache
  have no host ports; browser reaches the API via the nginx `/api` proxy.
- **OpenAPI/docs disabled in production**; baseline proxy security headers; no
  client-side logging.

---

## 8. Test status

- **Backend:** 29 pytest unit + integration tests — money math, auth (incl. cookie
  auth), wallet credit/debit (conversion + idempotency), transfers (cross-currency,
  insufficient funds, self-transfer, idempotency, stale-rate), locking/concurrency,
  history pagination/filtering, health/metrics.
- **Frontend:** 7 Vitest tests — money formatting + Login form smoke tests.
- **CI:** backend tests+coverage, frontend test+build, docker image build.

---

## 9. How to run

```bash
# Docker (recommended) — only the frontend is exposed
cp .env.example .env            # set a strong JWT_SECRET for non-local
docker compose up --build
# Frontend: http://localhost:8080   API via proxy: http://localhost:8080/api/v1

# Local dev
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev

# Tests
cd backend && source .venv/bin/activate && pytest -q --cov=app
cd frontend && npm test
```

---

## 10. Known limitations (intentional, scope-appropriate)

- `create_all()` on startup instead of Alembic migrations (unsafe with multiple
  replicas).
- No app-layer login rate limiting or JWT revocation (short-lived tokens only).
- `/metrics` has no auth; it is network-isolated (unpublished) and should stay
  behind ingress.
- Passwords are capped at bcrypt's 72-byte effective limit.
- Login/signup still return the token in the response body for programmatic API
  clients; the browser flow ignores it and relies on the cookie.
- Profile photo accepts a URL rather than binary upload to object storage.
- FX refresh is startup + on-demand; a scheduled worker is designed but not wired.

---

## 11. Deliverables mapped to the brief

| Requirement | Where |
|---|---|
| Clean architecture / domain modelling | `backend/app/modules/*` (layered), ARCHITECTURE.md |
| API & data design | module routers + schemas; ER model in ARCHITECTURE.md |
| Security & validation | cookie auth, Pydantic, parameterised SQL, Security section |
| Unit + integration tests | `backend/tests/` (29), `frontend/src/**/*.test.*` (7) |
| Error handling & reliability | domain errors → status codes, locking, idempotency |
| Dockerized + CI/CD | Dockerfiles, docker-compose.yml, `.github/workflows/ci.yml` |
| Logging / monitoring / health | JSON logs + request IDs, `/health` `/ready` `/metrics` |
| 4XX/5XX detection | `http_requests_total{status_class}` + alert rule (ARCHITECTURE.md) |
| Scale exercise | ARCHITECTURE.md → Scale exercise (design-only) |
| AI usage | AI_USAGE.md |
