# API

Interactive schema: http://localhost:8000/docs. All project endpoints require cookies. Send `credentials: include` in the browser. For POST/PATCH/DELETE send `X-CSRF-Token` from the readable `mlution_csrf` cookie. Anonymous requests get 401; invalid CSRF gets 403; another user's resource gets 404. Pagination uses `offset` and `limit` on projects, runs and chat.

| Area | Routes |
| --- | --- |
| Auth | POST `/api/auth/register`, `/login`, `/logout`, `/refresh`, `/change-password`, `/forgot-password`, `/reset-password`, `/demo`; GET `/api/auth/me`; DELETE `/api/auth/account` |
| Projects | GET/POST `/api/projects`; GET/PATCH/DELETE `/api/projects/{id}` |
| Datasets | POST/DELETE `/api/projects/{id}/dataset`; GET `/api/projects/{id}/profile` |
| Runs | POST `/api/projects/{id}/run`; GET `/api/projects/{id}/runs`, `/runs/{run_id}`; POST `/runs/{run_id}/cancel`, `/retry`, `/stages/{stage}/retry` |
| Events | GET `/api/projects/{id}/events`, `/events/stream`, `/runs/{run_id}/events`, `/runs/{run_id}/events/stream` |
| Experiments | GET `/api/projects/{id}/experiments`, `/experiments/{experiment_id}`, `/experiments/compare?first=UUID&second=UUID` |
| Export | GET `/api/projects/{id}/model`, `/model/code` (also `/code`), `/report` |
| Inference | POST `/api/projects/{id}/predict` with `{"features": {"age": 35}}` |
| Chat | GET/POST `/api/projects/{id}/chat` |
| Readiness | GET `/api/health` (public, 503 when dependencies unavailable) |

Registration/login body: `{"email":"you@example.com","password":"at-least-ten-characters"}`. Project creation: `{"name":"Churn","description":"Predict churn","use_demo_dataset":true}`. Run: `{"target_column":"churn","primary_metric":"f1","max_experiments":4,"time_budget_seconds":180}`. Dataset upload is multipart with `file`, or `demo=true`.

Run launch returns `{status: "queued", project_id, run_id}`. Run states: queued/running/completed/failed/cancelled. Cancel sets a persisted flag; an in-flight fit may finish before cancellation is observed. Retry returns a new run_id. Only finalization supports isolated stage retry after a completed report; dependent stages return 409 with instructions to retry the full run.

SSE events contain event_id, sequence id, project_id, run_id, correlation_id, type, stage, message, progress (0–1), created_at and backwards-compatible agent/ts/level/data fields. Streams emit `id:` and accept `Last-Event-ID` or `after_id`. A `close` event indicates terminal state. Frontend reconnects during outages and polls every 2.5 seconds for a stable fallback.
