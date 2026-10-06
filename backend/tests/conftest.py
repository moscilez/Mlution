import os
import tempfile
from pathlib import Path
import pytest

os.environ["ENVIRONMENT"] = "test"
os.environ["JOB_MODE"] = "inline"
os.environ["LLM_API_KEY"] = ""
os.environ["MLUTION_DATA_DIR"] = tempfile.mkdtemp(prefix="mlution-tests-", dir="data")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite:///" + (Path(os.environ["MLUTION_DATA_DIR"]).resolve() / "test.db").as_posix(),
)
os.environ["JWT_SECRET"] = "test-only-secret-with-more-than-32-characters"
if os.environ.get("TEST_DATABASE_URL") and not os.environ["TEST_DATABASE_URL"].rsplit("/", 1)[-1].endswith(
    "_test"
):
    raise RuntimeError("TEST_DATABASE_URL must point to a disposable database ending in _test")

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete
from app import db, models as m
from app.main import app
from app.middleware import windows


@pytest.fixture(scope="session", autouse=True)
def migrate():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean(migrate):
    with db.SessionLocal.begin() as session:
        for table in reversed(m.Base.metadata.sorted_tables):
            session.execute(delete(table))
    windows.clear()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def register(client, email="alice@example.com"):
    response = client.post("/api/auth/register", json={"email": email, "password": "safe-password-123"})
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = client.cookies.get("mlution_csrf")
    return response.json()


@pytest.fixture
def signed(client):
    register(client)
    return client
