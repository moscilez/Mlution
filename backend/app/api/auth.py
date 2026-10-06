import secrets
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from .. import db, models as m
from ..security import digest, signing_key, get_current_user, check_origin, aware
from ..settings import get_settings
from ..services.storage import remove_project_files

router = APIRouter(prefix="/auth")
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1] or any(c.isspace() for c in value):
            raise ValueError("Enter a valid email address")
        return value


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ResetRequest(BaseModel):
    email: str = Field(max_length=254)


class ResetConfirm(BaseModel):
    token: str = Field(max_length=128)
    password: str = Field(min_length=10, max_length=128)


def verify(hash_value, password):
    try:
        return hasher.verify(hash_value, password)
    except (VerificationError, InvalidHashError):
        return False


def session_response(response, user, old_session_id=None):
    settings = get_settings()
    refresh, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    with db.SessionLocal.begin() as s:
        if old_session_id:
            s.execute(delete(m.Session).where(m.Session.id == old_session_id))
        session = m.Session(
            user_id=user["id"], token_hash=digest(refresh), csrf_hash=digest(csrf), expires_at=expires
        )
        s.add(session)
        s.flush()
        access = jwt.encode(
            {
                "sub": user["id"],
                "sid": session.id,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
            },
            signing_key(),
            algorithm="HS256",
        )
    cookie = dict(secure=settings.cookie_secure, samesite="lax", path="/")
    response.set_cookie(
        "mlution_access", access, httponly=True, max_age=settings.access_token_expire_minutes * 60, **cookie
    )
    response.set_cookie(
        "mlution_refresh",
        refresh,
        httponly=True,
        max_age=settings.refresh_token_expire_days * 86400,
        **cookie,
    )
    response.set_cookie(
        "mlution_csrf", csrf, httponly=False, max_age=settings.refresh_token_expire_days * 86400, **cookie
    )
    return user


@router.post("/register", status_code=201)
def register(body: Credentials, request: Request, response: Response):
    check_origin(request)
    try:
        with db.SessionLocal.begin() as s:
            user = m.User(email=body.email, password_hash=hasher.hash(body.password))
            s.add(user)
            s.flush()
            result = {"id": user.id, "email": user.email, "role": user.role}
    except IntegrityError:
        raise HTTPException(409, "Email is already registered") from None
    db.audit(result["id"], "register")
    return session_response(response, result)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    check_origin(request)
    with db.SessionLocal() as s:
        user = s.scalar(select(m.User).where(m.User.email == body.email))
        valid = verify(user.password_hash if user else dummy_hash, body.password)
        if not user or not valid:
            raise HTTPException(401, "Incorrect email or password")
        result = {"id": user.id, "email": user.email, "role": user.role}
    db.audit(result["id"], "login")
    return session_response(response, result)


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/refresh")
def refresh(request: Request, response: Response):
    check_origin(request)
    with db.SessionLocal.begin() as s:
        session = s.scalar(
            select(m.Session)
            .where(m.Session.token_hash == digest(request.cookies.get("mlution_refresh", "")))
            .with_for_update()
        )
        if not session or aware(session.expires_at) <= datetime.now(timezone.utc):
            raise HTTPException(401, "Session expired")
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(session.csrf_hash, digest(csrf)):
            raise HTTPException(403, "Invalid CSRF token")
        user = s.get(m.User, session.user_id)
        result = {"id": user.id, "email": user.email, "role": user.role}
        s.delete(session)
    return session_response(response, result)


def clear_cookies(response):
    for name in ("mlution_access", "mlution_refresh", "mlution_csrf"):
        response.delete_cookie(name, path="/")


@router.post("/logout")
def logout(request: Request, response: Response, user=Depends(get_current_user)):
    with db.SessionLocal.begin() as s:
        s.execute(
            delete(m.Session).where(
                m.Session.token_hash == digest(request.cookies.get("mlution_refresh", ""))
            )
        )
    clear_cookies(response)
    db.audit(user["id"], "logout")
    return {"status": "ok"}


@router.post("/change-password")
def change_password(body: PasswordChange, response: Response, user=Depends(get_current_user)):
    with db.SessionLocal.begin() as s:
        record = s.get(m.User, user["id"])
        if not verify(record.password_hash, body.current_password):
            raise HTTPException(400, "Current password is incorrect")
        record.password_hash = hasher.hash(body.new_password)
        s.execute(delete(m.Session).where(m.Session.user_id == record.id))
    clear_cookies(response)
    db.audit(user["id"], "change_password")
    return {"status": "ok"}


@router.delete("/account")
def delete_account(response: Response, user=Depends(get_current_user)):
    with db.SessionLocal.begin() as s:
        active = s.scalar(
            select(m.AgentRun.id)
            .join(m.Project)
            .where(m.Project.owner_id == user["id"], m.AgentRun.status.in_(["queued", "running"]))
        )
        if active:
            raise HTTPException(409, "Cancel active runs before deleting your account")
        project_ids = list(s.scalars(select(m.Project.id).where(m.Project.owner_id == user["id"])))
        s.execute(delete(m.User).where(m.User.id == user["id"]))
    for pid in project_ids:
        remove_project_files(pid)
    clear_cookies(response)
    return {"status": "ok"}


@router.post("/forgot-password")
def forgot_password(body: ResetRequest, request: Request):
    check_origin(request)
    if get_settings().environment == "production":
        raise HTTPException(503, "Email password recovery is not configured. Contact your administrator.")
    result = {
        "message": "If the account exists, reset instructions are available through your configured delivery channel."
    }
    # A local-only delivery channel; production requires an email provider.
    if get_settings().environment != "production":
        with db.SessionLocal.begin() as s:
            user = s.scalar(select(m.User).where(m.User.email == body.email.strip().lower()))
            if user:
                token = secrets.token_urlsafe(32)
                s.add(
                    m.PasswordReset(
                        user_id=user.id,
                        token_hash=digest(token),
                        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                    )
                )
                result["reset_url"] = f"{get_settings().frontend_url}/reset-password?token={token}"
    return result


@router.post("/reset-password")
def reset_password(body: ResetConfirm, request: Request, response: Response):
    check_origin(request)
    with db.SessionLocal.begin() as s:
        reset = s.scalar(
            select(m.PasswordReset).where(m.PasswordReset.token_hash == digest(body.token)).with_for_update()
        )
        if not reset or aware(reset.expires_at) <= datetime.now(timezone.utc):
            raise HTTPException(400, "Reset link is invalid or expired")
        user = s.get(m.User, reset.user_id)
        user.password_hash = hasher.hash(body.password)
        s.execute(delete(m.Session).where(m.Session.user_id == user.id))
        s.execute(delete(m.PasswordReset).where(m.PasswordReset.user_id == user.id))
    clear_cookies(response)
    return {"status": "ok"}


@router.post("/demo")
def demo(request: Request, response: Response):
    check_origin(request)
    if not get_settings().demo_enabled:
        raise HTTPException(404, "Demo is disabled")
    # Each visitor receives a private demo account rather than sharing credentials.
    with db.SessionLocal.begin() as s:
        user = m.User(
            email=f"demo-{secrets.token_hex(12)}@mlution.local",
            password_hash=hasher.hash(secrets.token_urlsafe(32)),
        )
        s.add(user)
        s.flush()
        result = {"id": user.id, "email": user.email, "role": user.role}
    return session_response(response, result)
