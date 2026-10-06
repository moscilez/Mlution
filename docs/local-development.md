# Local development

Use Python 3.12+, Node 20+ and PostgreSQL 16+. Redis worker uses Linux process isolation; on Windows run the worker in Docker/WSL, or use JOB_MODE=inline for local development.

## Docker (Windows, Linux, macOS)

From the repository root:

```sh
docker compose up --build
```

No `.env` is necessary for the local demo. Frontend: http://localhost:3000; API/docs: http://localhost:8000/docs. The five services are PostgreSQL, Redis, backend, worker and frontend. Database is bound on localhost:5433; Redis on localhost:6379. Backend applies Alembic migrations before serving. Persistent named volumes store DB, Redis queue and private datasets/models. For backend reload use `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`.

Optional configuration: copy `.env.example` to `.env` (`Copy-Item .env.example .env` in PowerShell; `cp .env.example .env` on Unix). Preserve existing `.env` secrets; never commit it. Compose explicitly forwards documented settings. In containers PostgreSQL/Redis URLs use service names; browser API URL uses localhost.

Seed: `docker compose exec backend python -m app.seed`. It creates a demo user/project/profile idempotently. A generated development-only password is printed only when creating the user. The UI Try demo button does not require this password; each visitor gets a private demo account.

## Without Docker

Install PostgreSQL using the Windows installer, Homebrew on macOS, or your Linux package manager. In `psql` as a database administrator:

```sql
CREATE USER mlution WITH PASSWORD 'replace-with-your-local-password';
CREATE DATABASE mlution OWNER mlution;
```

Copy `.env.example` to root `.env`. Set DATABASE_URL to your actual credentials/port (native PostgreSQL typically 5432) and JOB_MODE=inline if you will not run Redis. In `backend`:

```sh
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --port 8000
```

With JOB_MODE=redis, start Redis locally or `docker compose up -d postgres redis`, then in a second backend shell on Linux/WSL: `python -m app.worker`. A Windows-native inline server does not need a worker. Root `.env` is loaded when running from the backend directory. LLM_API_KEY may be empty.

In `frontend`, create `.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`, then:

```sh
npm ci
npm run dev
```

Use localhost consistently in both browser and API URLs; mixing 127.0.0.1 and localhost changes cookie scope.

## Checks

Backend: `python -m ruff check app tests migrations`, `python -m ruff format --check app tests migrations`, `python -m pytest -q`. Default tests create disposable SQLite files only in test mode. PostgreSQL integration: create a disposable database named `mlution_test`, set TEST_DATABASE_URL to that database, then run pytest. Tests refuse PostgreSQL URLs whose database name does not end in `_test`; all tables in that test DB are cleared.

Frontend: `npm run lint`, `npm run typecheck`, `npm run build`. Browser checks against the running full stack: `npx playwright install chromium`, `npm test`. Browser tests create disposable accounts/projects. API demo: `python scripts/e2e_demo.py` from backend; set E2E_BASE_URL if using another API port.

Unix task aliases are in Makefile. On Windows use the equivalent commands above. `make reset-db` prints the destructive volume-reset command for deliberate manual execution.

## Troubleshooting

- Port conflict: set POSTGRES_PORT (default 5433) and adjust the native DATABASE_URL; stop an existing 3000/8000 listener before starting Compose.
- API 503: `docker compose ps`, then `docker compose logs backend worker`; verify postgres/redis and worker health.
- Login/cookie errors: use localhost throughout; check CORS_ORIGINS and COOKIE_SECURE=false for local HTTP. Passwords require at least ten characters.
- File rejected: export a UTF-8 comma-separated CSV with a header, at least two columns and one row; respect upload/row/column limits.
- Failed training: choose a target with enough examples per class and usable nonconstant features. Try another metric/run budget. Server logs contain diagnostics without exposing them in UI.
- Docker npm ci mismatch: update lockfile consistently after package changes; do not use the former npm-ci-or-install fallback.
- Old SQLite projects: not automatically imported because their ownership is unknown. Existing files remain available for a separately reviewed migration.

