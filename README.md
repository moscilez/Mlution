# Mlution

**From idea to ML solution.** Describe your problem. Upload your data. Let Mlution build, test and improve the solution.

Mlution is a local-first workspace for binary/multiclass classification and regression on tabular CSV data. Eight cooperating agents profile data, plan a task, train a baseline, measure results, critique and improve a model, then produce a leaderboard, report, downloadable preprocessing/model bundle and inference code. An LLM is optional; all metrics and training run in trusted Python.

## Quick start

```sh
docker compose up --build
```

Open http://localhost:3000 and click **Попробовать демо / Try demo**, then **Запустить пайплайн / Run pipeline**. Russian is the default interface language; RU / EN in the header saves your preference. Five services start: frontend, FastAPI backend, PostgreSQL, Redis and RQ worker. Migrations apply before API startup. No cloud account or LLM key is required. PostgreSQL is exposed on localhost:5433 to avoid a native PostgreSQL on 5432; browser/API ports are 3000/8000.

Configuration is optional for local demo. Copy `.env.example` to `.env` when customizing settings; do not overwrite an existing secret file. Development database defaults are strictly local. Production validates JWT_SECRET, secure cookies, disabled demo and Redis jobs.

## Features and architecture

- PostgreSQL + SQLAlchemy 2.x + Alembic, UUID public IDs, timezone timestamps, indexed ownership/run relations.
- Argon2id passwords, login/register/logout, rotating HttpOnly sessions, refresh, CSRF, account/password settings and local password reset.
- Private projects: every dataset, event stream, experiment, report, model, prediction and chat is checked against the project owner.
- Durable RQ runs with history, cancellation, full retry, safe final report retry and persisted SSE cursors. Polling covers outages.
- Safe CSV upload, deterministic splits, missing/category preprocessing, dummy baseline, real metrics, improvement history and model integrity hashes.
- Light white/graphite/blue design with an original Mlution mark, default Russian and persistent English preference, interactive seven-stage explorer, live timeline above the chat, charts, command palette (Ctrl/Cmd+K), skeleton/error/empty states and prediction playground.

Frontend: Next.js 15.5.24, TypeScript strict mode, React Query, Tailwind, Recharts. Backend: Python 3.12, FastAPI/Pydantic Settings, pandas, scikit-learn, SQLAlchemy/psycopg, Alembic, Redis/RQ, joblib and optional narrative LLM.

Request path: browser → FastAPI (session/CSRF/owner validation) → PostgreSQL. ML path: FastAPI → Redis → Linux worker → trusted agents → PostgreSQL/events + private artifact volume. Existing SQLite files are preserved, but the application uses PostgreSQL; no automatic ownerless-data import occurs.

## Documentation

- [Architecture](docs/architecture.md)
- [Local development, Windows/Linux/macOS, troubleshooting](docs/local-development.md)
- [API routes and authentication](docs/api.md)
- [Security and production configuration](docs/security.md)
- [Agent pipeline and cancellation semantics](docs/agent-pipeline.md)
- [Design, branding, localization and browser verification](docs/design-update.md)
- [Organizer specification, AutoResearch, portable solution ZIP and startup](docs/competition.md)

## Hackathon AutoResearch

The organizer entry point is `python solution.py task.md`; the standalone agent
does not need PostgreSQL or Redis. It reads train/test/data dictionary/submission
template, evaluates hypotheses on a training-only holdout, and atomically saves
test predictions. Use `python competition/package_solution.py` to create the
submission ZIP. The web application exposes the same research engine at
`/competition`. See [the competition guide](docs/competition.md) for Qwen-only
configuration, offline smoke tests, resource limits and verification boundaries.

Interactive API: http://localhost:8000/docs. Readiness: http://localhost:8000/api/health.

## Migrations and seed

```sh
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m app.seed
```

Seed is idempotent and creates a development demo user, churn dataset, cached profile and project. A random development-only password is printed only at initial creation. The Try demo flow creates a separate account per visitor and does not require a shared password.

For local backend development, from `backend` create/activate a Python virtualenv, install `requirements-dev.txt`, apply `python -m alembic upgrade head`, then run `python -m uvicorn app.main:app --reload`. Use JOB_MODE=inline for a Windows-native fallback without Redis. Run `python -m app.worker` on Linux/WSL for Redis mode. In frontend use `npm ci` and `npm run dev`; set NEXT_PUBLIC_API_URL via `.env.local`. Full database setup commands are in local-development.md.

## Environment variables

| Variable | Purpose / local default |
| --- | --- |
| DATABASE_URL | Native PostgreSQL SQLAlchemy URL; Compose uses postgres service |
| POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB | Local Compose database identity |
| POSTGRES_PORT | Host database port, 5433 |
| JWT_SECRET | 32+ random characters in production; generated private local key when empty |
| JWT_ALGORITHM | HS256 only |
| ACCESS_TOKEN_EXPIRE_MINUTES / REFRESH_TOKEN_EXPIRE_DAYS | 15 / 7 |
| CORS_ORIGINS / FRONTEND_URL | http://localhost:3000 |
| NEXT_PUBLIC_API_URL | Browser API base URL; build-time for Docker |
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL | Optional narrative provider; empty key keeps ML working |
| MAX_UPLOAD_SIZE_MB | 25 |
| MAX_EXPERIMENTS | 6 maximum; run UI defaults to 4 |
| DEFAULT_TIME_BUDGET_SECONDS | 180 |
| MAX_ROWS / MAX_COLUMNS | 100000 / 200 (native configuration) |
| ENVIRONMENT / COOKIE_SECURE | development / false locally |
| DEMO_ENABLED / SEED_DEMO | true / false |
| REDIS_URL / JOB_MODE | Redis queue URL / redis; inline is development only |
| MLUTION_DATA_DIR | Private datasets/artifacts/runtime key directory |
| DEMO_PASSWORD | Optional development-only seed password; otherwise random |

Do not put real keys or credentials in source control. Root `.env` and runtime data are ignored.

## Tests and formatting

From backend:

```sh
python -m pip install -r requirements-dev.txt
python -m ruff check app tests migrations
python -m ruff format --check app tests migrations
python -m pytest -q
python scripts/e2e_demo.py
```

Default unit tests use disposable SQLite only under ENVIRONMENT=test. Set TEST_DATABASE_URL to an isolated PostgreSQL database ending in `_test` for the same suite against PostgreSQL. Tests clear that database's tables.

From frontend:

```sh
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm test
npm run format
```

Browser tests require the running Compose stack. Unix task aliases: `make dev`, `make test`, `make lint`, `make format`, `make migrate`, `make seed`. `make reset-db` prints the manual destructive reset command.

## Demo in 3–5 minutes

1. Open the landing page, choose Try demo; an isolated session and churn project are created.
2. Inspect profile: rows, types, missing values, imbalance and leakage/ID warnings.
3. Run pipeline and watch stages/events and experiment scores appear.
4. Inspect leaderboard, train/validation metrics, confusion matrix, feature importance and accepted/rejected improvement.
5. Open Results, download model and inference code, then test a customer in Prediction Playground.
6. Register a second account to verify that previous projects are private; sign out through the header.

## Security and current limitations

Uploaded CSV/model text and LLM output never execute as server code. Only generated model files are loaded after a private-path and integrity check. Ownership checks cover all private routes. Production must use HTTPS, a strong JWT secret, secure cookies, exact CORS origins and private PostgreSQL/Redis.

Local reset links are development-only. Production email recovery returns 503 until a real provider is configured. Cancellation waits for in-flight model fits; Redis workers enforce a hard job timeout, while inline mode cannot forcibly kill threads. Current evaluation uses train/validation rather than an independent test set; threshold tuning can overestimate validation performance. Leakage checks are heuristic. Model importance is global, not a per-prediction explanation. Disposable demo accounts and old artifacts currently require manual cleanup. This is a local/hackathon MVP, not a public multi-tenant deployment with quotas and email delivery.

## Screenshots

Capture placeholders: landing, dashboard, workspace timeline, results/leaderboard, mobile layout. Screenshots should come from real runs rather than fabricated metrics.

