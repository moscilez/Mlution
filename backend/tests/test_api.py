import time
import io
import ast
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db, models as m
from app.settings import get_settings
from app.agents.experiment import compute_metrics
from conftest import register


def project(client, demo=False):
    response = client.post("/api/projects", json={"name": "Test", "use_demo_dataset": demo})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_register_login_logout(client):
    user = register(client)
    assert "password_hash" not in user
    assert client.get("/api/auth/me").json()["email"] == "alice@example.com"
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/projects").status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": "safe-password-123"}
        ).status_code
        == 200
    )


def test_anonymous_and_csrf(client):
    assert client.get("/api/projects").status_code == 401
    register(client)
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/projects", json={"name": "Blocked"}).status_code == 403


def test_project_isolation(signed):
    pid = project(signed, True)
    with TestClient(app) as other:
        register(other, "bob@example.com")
        assert other.get("/api/projects").json() == []
        for path in [
            "",
            "/profile",
            "/experiments",
            "/report",
            "/model",
            "/code",
            "/status",
            "/events",
            "/events/stream",
            "/runs",
            "/chat",
        ]:
            assert other.get(f"/api/projects/{pid}{path}").status_code == 404
        assert other.post(f"/api/projects/{pid}/predict", json={"features": {}}).status_code == 404
        assert other.delete(f"/api/projects/{pid}").status_code == 404


def test_csv_profile_and_bad_files(signed):
    pid = project(signed)
    data = b"age,income,target\n20,40,yes\n30,,no\n20,40,yes\n"
    r = signed.post(f"/api/projects/{pid}/dataset", files={"file": ("../../data.csv", data, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["n_rows"] == 3 and r.json()["n_duplicates"] == 1
    assert signed.get(f"/api/projects/{pid}/profile").status_code == 200
    for filename, data, mime in [
        ("bad.exe", b"xx", "text/csv"),
        ("bad.csv", b"\x00\xff", "text/csv"),
        ("bad.csv", b"one\n1", "text/csv"),
        ("bad.csv", b"a,b\n1,2", "image/png"),
    ]:
        assert (
            signed.post(f"/api/projects/{pid}/dataset", files={"file": (filename, data, mime)}).status_code
            == 400
        )


def test_upload_limit(signed, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_size_mb", 1)
    pid = project(signed)
    assert (
        signed.post(
            f"/api/projects/{pid}/dataset",
            files={"file": ("large.csv", b"x" * (1024 * 1024 + 1), "text/csv")},
        ).status_code
        == 413
    )


def test_refresh_rotation(signed):
    old_refresh = signed.cookies.get("mlution_refresh")
    assert signed.post("/api/auth/refresh").status_code == 200
    assert signed.cookies.get("mlution_refresh") != old_refresh
    signed.headers["X-CSRF-Token"] = signed.cookies.get("mlution_csrf")
    assert signed.get("/api/auth/me").status_code == 200


def test_change_password_revokes_sessions(signed):
    assert (
        signed.post(
            "/api/auth/change-password",
            json={"current_password": "safe-password-123", "new_password": "a-new-password-123"},
        ).status_code
        == 200
    )
    assert signed.get("/api/auth/me").status_code == 401
    assert (
        signed.post(
            "/api/auth/login", json={"email": "alice@example.com", "password": "safe-password-123"}
        ).status_code
        == 401
    )


def test_cancel_queued_run(signed):
    pid = project(signed, True)
    with db.SessionLocal.begin() as s:
        run = m.AgentRun(project_id=pid, config_json="{}")
        s.add(run)
        s.flush()
        rid = run.id
    r = signed.post(f"/api/projects/{pid}/runs/{rid}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"


def test_real_demo_pipeline(signed):
    pid = project(signed, True)
    r = signed.post(f"/api/projects/{pid}/run", json={"max_experiments": 3, "time_budget_seconds": 90})
    assert r.status_code == 200, r.text
    rid = r.json()["run_id"]
    for _ in range(180):
        state = signed.get(f"/api/projects/{pid}/status").json()
        if state["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.5)
    assert state["status"] == "completed", state
    exps = signed.get(f"/api/projects/{pid}/experiments").json()
    assert len([e for e in exps if e["status"] == "completed"]) >= 2
    assert signed.get(f"/api/projects/{pid}/report").status_code == 200
    assert len(signed.get(f"/api/projects/{pid}/model").content) > 1000
    assert "joblib" in signed.get(f"/api/projects/{pid}/model/code").text
    r = signed.post(f"/api/projects/{pid}/predict", json={"features": {}})
    assert r.status_code == 200, r.text
    assert 0 <= r.json()["probability"] <= 1
    assert signed.post(f"/api/projects/{pid}/predict", json={"features": {"unknown": 1}}).status_code == 422
    events = signed.get(f"/api/projects/{pid}/runs/{rid}/events").json()
    assert events and all(
        {"event_id", "run_id", "project_id", "type", "created_at", "progress"} <= e.keys() for e in events
    )
    assert not any("traceback" in str(e) for e in events)
    with signed.stream(
        "GET", f"/api/projects/{pid}/events/stream", headers={"Last-Event-ID": str(events[-2]["id"])}
    ) as r:
        assert "id:" in r.read().decode()
    from pathlib import Path

    artifact = Path(
        next(e for e in db.list_experiments(pid) if e["id"] == db.get_project(pid)["best_experiment_id"])[
            "artifact_path"
        ]
    )
    artifact.write_bytes(b"tampered artifact")
    assert signed.get(f"/api/projects/{pid}/model").status_code == 409


@pytest.mark.parametrize(
    "task,truth,pred",
    [
        ("regression", [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]),
        ("binary_classification", [0, 1], [0, 1]),
        ("multiclass_classification", [0, 1, 2], [0, 1, 2]),
    ],
)
def test_real_metrics(task, truth, pred):
    values = {x["name"]: x["value"] for x in compute_metrics(task, truth, pred)}
    assert values["rmse" if task == "regression" else "accuracy"] == (0 if task == "regression" else 1)


def test_local_reset(signed):
    r = signed.post("/api/auth/forgot-password", json={"email": "alice@example.com"})
    token = r.json()["reset_url"].split("token=")[1]
    assert (
        signed.post(
            "/api/auth/reset-password", json={"token": token, "password": "reset-password-123"}
        ).status_code
        == 200
    )
    assert (
        signed.post(
            "/api/auth/reset-password", json={"token": token, "password": "reset-password-123"}
        ).status_code
        == 400
    )


@pytest.mark.parametrize("task", ["regression", "text_classification"])
def test_non_demo_training(signed, task):
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        {
            "feature": rng.normal(size=120),
            "category": rng.choice(["a", "b", "c"], 120),
            "enabled": rng.choice([True, False], 120),
        }
    )
    frame["target"] = (
        np.sin(frame["feature"]) + rng.normal(size=120)
        if task == "regression"
        else rng.choice(["red", "green", "blue"], 120)
    )
    pid = project(signed)
    raw = io.BytesIO(frame.to_csv(index=False).encode())
    assert (
        signed.post(
            f"/api/projects/{pid}/dataset", files={"file": ("train.csv", raw, "text/csv")}
        ).status_code
        == 200
    )
    launch = signed.post(
        f"/api/projects/{pid}/run",
        json={"target_column": "target", "max_experiments": 2, "time_budget_seconds": 60},
    )
    assert launch.status_code == 200, launch.text
    for _ in range(120):
        status = signed.get(f"/api/projects/{pid}/status").json()["status"]
        if status in {"completed", "failed"}:
            break
        time.sleep(0.25)
    assert status == "completed"
    response = signed.post(
        f"/api/projects/{pid}/predict",
        json={"features": {"feature": 0.4, "category": "unseen", "enabled": True}},
    )
    assert response.status_code == 200, response.text
    if task != "regression":
        assert response.json()["prediction"] in {"red", "green", "blue"}
    ast.parse(signed.get(f"/api/projects/{pid}/code").text)


def test_delete_account_removes_owned_resources(signed):
    pid = project(signed, True)
    assert signed.delete("/api/auth/account").status_code == 200
    assert db.get_project(pid) is None
    assert signed.get("/api/auth/me").status_code == 401


def test_login_rate_limit(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/auth/login", json={"email": "missing@example.com", "password": "wrong-password"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"email": "missing@example.com", "password": "wrong-password"}
        ).status_code
        == 429
    )


def test_generated_code_escapes_user_metadata():
    from app.agents.report import generate_usage_code

    code = generate_usage_code(
        {"name": '"""\nraise RuntimeError("injected")\n'},
        {"model_type": "dummy", "primary_metric_name": "f1", "primary_metric_value": 0.5},
        {"columns": []},
        {"target_column": '"""\nimport os', "task_type": "binary_classification"},
    )
    ast.parse(code)


def test_replacing_dataset_invalidates_results(signed):
    pid = project(signed, True)
    db.update_project(
        pid,
        status="completed",
        best_experiment_id="old-model",
        best_metric_value=0.99,
        report_json={"old": True},
    )
    r = signed.post(f"/api/projects/{pid}/dataset", data={"demo": "true"})
    assert r.status_code == 200
    record = db.get_project(pid)
    assert (
        record["status"] == "created"
        and record["best_experiment_id"] is None
        and record["report_json"] is None
    )


def test_size_limit_response_has_cors_headers(signed):
    r = signed.post("/api/projects", content=b"x" * 70000, headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 413
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
