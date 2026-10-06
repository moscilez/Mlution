import hashlib
import secrets
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
import jwt
from fastapi import HTTPException, Request
from . import db, models as m
from .settings import get_settings
from .config import DATA_DIR

current_user = ContextVar("current_user", default=None)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def signing_key():
    configured = get_settings().jwt_secret
    if configured:
        return configured
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(DATA_DIR) / ".session-key"
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8")


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def get_current_user(request: Request):
    token = request.cookies.get("mlution_access", "")
    try:
        payload = jwt.decode(
            token, signing_key(), algorithms=["HS256"], options={"require": ["exp", "sub", "sid"]}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Please sign in") from None
    with db.SessionLocal() as s:
        session = s.get(m.Session, payload["sid"])
        if (
            not session
            or session.user_id != payload["sub"]
            or aware(session.expires_at) <= datetime.now(timezone.utc)
        ):
            raise HTTPException(401, "Session expired")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            csrf = request.headers.get("x-csrf-token", "")
            if not csrf or not secrets.compare_digest(session.csrf_hash, digest(csrf)):
                raise HTTPException(403, "Invalid CSRF token")
        user = s.get(m.User, payload["sub"])
        if not user:
            raise HTTPException(401, "Session expired")
        return {"id": user.id, "email": user.email, "role": user.role}


async def require_authenticated_user(request: Request):
    user = get_current_user(request)
    token = current_user.set(user)
    try:
        yield user
    finally:
        current_user.reset(token)


def require_project_owner(pid):
    p = db.get_project(pid)
    user = current_user.get()
    if not user:
        raise HTTPException(401, "Please sign in")
    if not p or p["owner_id"] != user["id"]:
        raise HTTPException(404, "Project not found")
    return p


def require_admin(request: Request):
    user = get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def check_origin(request):
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().cors_origins.split(","):
        raise HTTPException(403, "Origin not allowed")
