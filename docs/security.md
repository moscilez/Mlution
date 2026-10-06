# Security

- Passwords use Argon2id. Password/hash fields never appear in user responses.
- Access JWT lifetime is 15 minutes; its server session must still exist. Refresh secrets are hashed, rotated and revoked on logout/reset/password change. Cookies use HttpOnly for credentials, SameSite=Lax, and Secure when configured.
- Mutations validate X-CSRF-Token against the session's hashed token. Credentialed CORS permits configured origins only; unauthenticated login/register/demo/reset also check Origin.
- All project API routes require a session and compare owner_id. Other users receive 404, including event streams, model downloads, prediction, chat and run history. Prepared admin dependency exists; no public privilege-escalation route exists.
- Uploads accept CSV extensions and known CSV/text MIME types, stream to random private filenames, reject binary/NUL input, cap bytes/rows/columns and parse UTF-8. User filenames do not determine storage paths. Categorical expansion is bounded and constants/IDs/leakage suspects are excluded. CSV formula strings are ordinary text, never executed or exported as spreadsheets.
- LLM is narrative only. It never executes code or supplies trusted numeric metrics. It receives project facts, not paths, credentials or raw CSV. No key is necessary for training or demo.
- Only locally generated model artifacts are loaded, after path containment and SHA-256 checks. A hash protects against corruption or file substitution without DB access; it is not a defense against an attacker controlling the database and filesystem together.
- Redis shares rate limits for login/register/upload/chat/run/demo/reset. Mutations fail closed if Redis is unavailable. Inline mode uses a process-local limiter. Request bodies are bounded; unexpected errors and SSE never include traceback.
- Audit actions include register/login/logout, project creation/deletion, dataset upload, run launch, model download and password changes. Prediction logs retain IDs and timestamp, not input feature values. Server logs may contain stack traces; restrict their access.

For production set ENVIRONMENT=production, COOKIE_SECURE=true, DEMO_ENABLED=false and a randomly generated JWT_SECRET of at least 32 characters. Use HTTPS and an exact CORS allowlist; keep database/Redis private. Rotate development database credentials. Local generated signing keys reside in private runtime storage and are excluded from the repository.

Local password recovery returns a one-time development reset link. Production recovery returns 503 until a trusted email delivery provider is implemented; it never exposes reset tokens. Demo creates an isolated disposable account per visitor. These accounts are not automatically expired yet.

Cancellation is cooperative during model fit. RQ's process timeout bounds the full run; inline mode cannot forcibly kill a Python thread. Validation is a reproducible 80/20 split; threshold tuning reuses validation data. Add a separate untouched test set before making deployment claims. Leakage checks are heuristics and do not replace domain review.
