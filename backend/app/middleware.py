import json
import logging
import time
import uuid
import threading
from collections import defaultdict, deque
from redis import Redis
from starlette.responses import JSONResponse
from .settings import get_settings

logger = logging.getLogger("mlution.requests")
windows = defaultdict(deque)
lock = threading.Lock()


class ApiMiddleware:
    def __init__(self, app):
        self.app = app
        self.redis = Redis.from_url(get_settings().redis_url, socket_connect_timeout=1, socket_timeout=1)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        path = scope["path"]
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        cap = get_settings().max_upload_size_mb * 1024 * 1024 + 65536 if path.endswith("/dataset") else 65536
        if path == "/api/competition/projects":
            cap = get_settings().competition_max_upload_mb * 4 * 1024 * 1024 + 65536
        try:
            declared_size = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(
                scope, receive, send
            )
        if declared_size > cap:
            return await JSONResponse({"detail": "Request body exceeds limit"}, status_code=413)(
                scope, receive, send
            )
        if scope["method"] == "POST":
            suffix = path.rsplit("/", 1)[-1]
            limits = {
                "login": 10,
                "register": 5,
                "demo": 5,
                "forgot-password": 5,
                "reset-password": 5,
                "dataset": 10,
                "chat": 30,
                "run": 10,
                "retry": 10,
                "projects": 10,
            }
            if suffix in limits:
                client = scope.get("client") or ("unknown", 0)
                bucket = f"mlution:rate:{client[0]}:{suffix}:{int(time.time()) // 60}"
                from starlette.concurrency import run_in_threadpool

                allowed = await run_in_threadpool(self.allow, bucket, limits[suffix])
                if not allowed:
                    return await JSONResponse(
                        {"detail": "Too many requests. Try again in a minute."},
                        status_code=429,
                        headers={"Retry-After": "60"},
                    )(scope, receive, send)
        # Bound streamed request bodies even when Content-Length is absent.
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > cap:
                raise BodyTooLarge()
            return message

        status = 500
        user_id = None

        async def wrapped_send(message):
            nonlocal status, user_id
            if message["type"] == "http.response.start":
                from .security import current_user

                user_id = (current_user.get() or {}).get("id")
                status = message["status"]
                message["headers"] += [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        try:
            await self.app(scope, bounded_receive, wrapped_send)
        except BodyTooLarge:
            await JSONResponse({"detail": "Request body exceeds limit"}, status_code=413)(
                scope, receive, send
            )
        finally:
            logger.info(
                json.dumps(
                    {
                        "timestamp": time.time(),
                        "level": "info",
                        "request_id": request_id,
                        "user_id": user_id,
                        "project_id": path.split("/")[3] if path.startswith("/api/projects/") else None,
                        "run_id": path.split("/runs/")[1].split("/")[0] if "/runs/" in path else None,
                        "endpoint": path,
                        "duration": round(time.monotonic() - started, 3),
                        "status_code": status,
                    }
                )
            )

    def allow(self, key, limit):
        if get_settings().job_mode == "redis":
            try:
                count = self.redis.incr(key)
                if count == 1:
                    self.redis.expire(key, 120)
                return count <= limit
            except Exception:
                # Fail closed for mutations if the shared limiter is unavailable.
                return False
        with lock:
            if len(windows) > 5000:
                windows.clear()
            entries = windows[key]
            now = time.monotonic()
            while entries and entries[0] < now - 60:
                entries.popleft()
            if len(entries) >= limit:
                return False
            entries.append(now)
            return True


class BodyTooLarge(Exception):
    pass
