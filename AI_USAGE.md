# AI Usage

AI tooling was used throughout, as encouraged by the challenge. This documents
what it accelerated and where its suggestions were rejected.

## Tools used

- **GitHub Copilot (agent mode)** — scaffolding modules, generating boilerplate
  (routers, schemas, repositories), drafting tests and documentation.

## Where AI accelerated delivery

- **Boilerplate generation:** the repetitive `router → service → repository →
  schema` layering across five modules was generated quickly, letting effort
  focus on domain logic.
- **Test coverage:** draft unit/integration tests for money math, auth, wallet,
  transfers, and history were produced fast, then reviewed and tightened.
- **Infra & docs:** Dockerfiles, docker-compose, the CI workflow, and the first
  drafts of README/ARCHITECTURE were AI-drafted and then edited.
- **Debugging:** quickly diagnosed two test failures (Decimal trailing-zero
  formatting and a naive-vs-aware datetime comparison in FX rate resolution).

## Challenges found during review (and fixes)

An AI-assisted architecture review of the concurrency and locking paths surfaced
real issues that were then fixed (details in ARCHITECTURE.md → Challenges & Fixes):

- **Lost update despite `FOR UPDATE` (critical).** The locked read reused a
  stale instance from SQLAlchemy's identity map, so the row lock did not protect
  the balance. Fixed with `populate_existing=True` to re-read under the lock.
- **Idempotency check-then-act race.** Concurrent identical requests hit the
  unique constraint and returned HTTP 500. Fixed by catching `IntegrityError`
  and returning the original transaction.
- **Negative-balance protection only in app code.** Added a DB-level
  `CHECK(balance_minor >= 0)` as defense-in-depth.

AI was useful for *spotting* the identity-map/locking interaction quickly, but
the diagnosis and the fix were verified by hand and by re-running the full test
suite — not taken on trust.

## Security hardening (review-driven)

A frontend/security review drove these changes (details in ARCHITECTURE.md →
Security and Challenges & Fixes #7):

- **JWT moved out of `localStorage` into an `HttpOnly`/`SameSite` cookie**, so the
  token is no longer readable by JS (XSS-resistant); the SPA stores only
  non-sensitive display info.
- **No directly public API** — Docker publishes only the frontend; the backend,
  Postgres, and Redis are internal-only and reached via the nginx `/api` proxy.
- **OpenAPI schema/docs disabled in production**; baseline security headers at the
  proxy; no client-side logging of requests/credentials.

AI helped scaffold the cookie plumbing and proxy config; the auth precedence rule
(header over cookie, to keep API clients and tests working) and the decision to
keep returning the token in the body for programmatic clients were human calls.

## Where AI suggestions were rejected / corrected

- **Microservices framing.** The initial prompt leaned toward splitting
  frontend/backend/DB as "microservices." That was rejected in favour of a
  modular monolith because atomic cross-currency transfers are far safer in a
  single ACID transaction. (Rationale captured in ARCHITECTURE.md.)
- **Floating-point money.** Any suggestion to store balances as floats/decimals
  columns directly was rejected; balances are integer minor units with `Decimal`
  used only for conversion math.
- **Single model for API + DB.** Suggestions to reuse one class as both the
  Pydantic schema and the ORM model were rejected to keep the API contract
  decoupled from persistence.
- **Synchronous provider calls.** Early drafts called the FX provider inline on
  the transaction path; this was replaced with cache-first → DB-fallback so the
  platform stays available during provider downtime.
- **Over-eager error handling.** Speculative try/except blocks around paths that
  cannot fail were removed to keep the code honest and readable.
- **Token in browser storage.** The initial SPA kept the JWT in `localStorage`;
  this was rejected in favour of an httpOnly cookie after review.

## Human-owned decisions

Architecture choice, data model, consistency/locking strategy, idempotency
design, and the exchange-resilience approach were decided by the engineer; AI
executed and accelerated within those decisions.
