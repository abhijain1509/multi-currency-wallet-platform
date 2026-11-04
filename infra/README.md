# Infrastructure & Delivery

## Contents

- `docker-compose.prod.yml` — production overlay (uses pre-built images,
  externally-managed Postgres/Redis, multiple backend replicas).
- CI/CD lives in [`../.github/workflows/ci.yml`](../.github/workflows/ci.yml):
  backend tests + coverage, frontend build, and a Docker image build gate.

## Deploy model

The app is container-native and portable to any Docker host (Render, Railway,
Fly.io, ECS, or a plain VM).

```bash
# Build & push images (CI does this on push to main)
docker compose build
docker compose push        # after tagging to your registry

# On the host, with env configured:
docker compose -f infra/docker-compose.prod.yml up -d
```

### Required environment

| Var | Notes |
|---|---|
| `DATABASE_URL` | Managed Postgres connection string |
| `REDIS_URL` | Managed Redis connection string |
| `JWT_SECRET` | Strong random secret (rotate periodically) |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |

### Migrations

Dev auto-creates tables. In production, run Alembic migrations as a pre-deploy
step before starting the new backend version.

## Health & monitoring

- Liveness: `GET /health` · Readiness (DB check): `GET /ready`
- Metrics: `GET /metrics` (Prometheus) — scrape and alert on 5xx ratio and
  latency (see ARCHITECTURE.md for the alert rule).
- Logs are structured JSON with per-request `x-request-id` for tracing.
