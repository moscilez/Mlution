# Architecture

Mlution is a local-first tabular ML workspace. Next.js talks to FastAPI using credentialed requests. PostgreSQL owns users, sessions, projects, datasets/profiles, runs/events, experiments/artifacts, improvement steps, chat, prediction metadata and audit records. Public entity IDs are UUID strings; event sequences are monotonic integers used only as SSE cursors, with a UUID event_id.

FastAPI validates and dispatches runs to Redis/RQ. The Linux worker trains only a curated model zoo and persists real metrics. Shared storage holds private CSVs and generated models. PostgreSQL stores SHA-256 provenance; model files are checked before deserialization. Uploaded model files are never accepted.

The existing agent repository interface remains dictionary based for compatibility; DatasetProfile, MLTask, RunRequest, FinalReport and API outputs are Pydantic contracts. Stages record start/finish timestamps. Agent events carry project/run/correlation IDs. Retry starts a new run; experiments remain tied to their original run. Only final report regeneration supports an isolated stage retry; other stages require a full run because fitted state lives in memory.

SQLAlchemy provides pooling and parameterized statements. Alembic owns schema creation. Startup verifies DB connectivity; the backend bootstrap applies migrations before Uvicorn. Workers can start before migrations, but receive no jobs until backend startup succeeds. PostgreSQL and Redis health checks gate service startup. Backend readiness verifies registered workers.

Development without Redis uses JOB_MODE=inline and two executor threads. This is single-process development only: cooperative cancellation and stage-level time checks apply; RQ additionally enforces a hard job timeout in a separate process. Use Redis jobs for production-like execution.

Current limits: one active run per user, six experiments per run, 600-second request budget maximum, 25 MB uploads by default, 100,000 rows, 200 columns, bounded categorical expansion. Local deployment binds ports to loopback. PostgreSQL is exposed on 5433 to coexist with a native PostgreSQL on 5432.

SQLite is restricted to disposable unit tests. Existing SQLite files are preserved but not automatically imported into PostgreSQL. Their projects did not have owners, so an automatic import would require an explicit owner mapping.

