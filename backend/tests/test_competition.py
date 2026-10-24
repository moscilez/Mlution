import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.competition.data import load_task
from app.competition.engine import research
from app.competition.planner import ResearchPlanner
from app.competition.plans import Plan
from app.competition.scoring import combined_score, normalized_score


def task_files(directory, classification=False):
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    n = 150
    x = rng.normal(size=n)
    train = pd.DataFrame(
        {
            "id": [f"{i:05}" for i in range(n)],
            "sensor": x,
            "segment": np.where(x > 0, "A", "B"),
            "empty": np.nan,
        }
    )
    train["answer"] = (
        np.where(x > 0.5, "red", np.where(x < -0.5, "blue", "green"))
        if classification
        else 3 * x + rng.normal(0, 0.1, n)
    )
    test = train.drop(columns="answer").iloc[:17].copy()
    test["id"] = [f"{i + 900:05}" for i in range(len(test))]
    test.loc[test.index[0], "segment"] = "previously-unseen"
    train.to_csv(directory / "train.csv", index=False)
    test.to_csv(directory / "test.csv", index=False)
    sample = pd.DataFrame({"id": test.id.iloc[::-1], "answer": "placeholder"})
    sample.to_csv(directory / "sample_submission.csv", index=False)
    pd.DataFrame(
        {"feature": train.columns, "role": ["id", "feature", "feature", "feature", "target"]}
    ).to_csv(directory / "data_dictionary.csv", index=False)
    path = directory / "task.md"
    path.write_text(
        "Predict answer. Metric: Macro F1. Write submission.csv."
        if classification
        else "Predict answer. Metric: RMSE. Write submission.csv.",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("classification", [False, True])
def test_research_predictions_and_holdout(tmp_path, classification):
    task = task_files(tmp_path, classification)
    state = research(task, seconds=90, max_experiments=3, trial_seconds=35, threads=1, offline=True)
    assert state["status"] == "completed"
    assert state["mode"] == "offline_heuristic"
    assert len(state["experiments"]) >= 2
    assert state["best"]["score"] is not None
    assert any(item["status"] == "completed" and not item["dummy"] for item in state["experiments"])
    expected = pd.read_csv(tmp_path / "sample_submission.csv", dtype=str)
    actual = pd.read_csv(tmp_path / "submission.csv", dtype=str)
    assert list(actual) == list(expected)
    assert actual.id.tolist() == expected.id.tolist()
    assert actual.answer.notna().all()
    if classification:
        assert set(actual.answer) <= {"red", "blue", "green"}
    else:
        assert np.isfinite(actual.answer.astype(float)).all()
    reports = [item for item in state["experiments"] if item["status"] == "completed"]
    assert len({(item["train_rows"], item["validation_rows"]) for item in reports}) == 1
    assert reports[0]["validation_rows"] < len(pd.read_csv(tmp_path / "train.csv"))
    assert (tmp_path / ".mlution" / state["run_id"] / "trial-001" / "experiment.py").exists()
    assert json.loads((tmp_path / "research.json").read_text())["best"]["score"] == state["best"]["score"]


def test_target_and_identifier_order_are_generic(tmp_path):
    task = task_files(tmp_path)
    spec = load_task(task)
    assert spec.target == "answer"
    assert "id" not in spec.features
    assert spec.sample.id.iloc[0].startswith("00")
    assert spec.test.sensor.iloc[0] == pytest.approx(pd.read_csv(tmp_path / "test.csv").sensor.iloc[-1])


def test_invalid_submission_rejected(tmp_path):
    task = task_files(tmp_path)
    pd.DataFrame({"id": ["bad"], "answer": [0]}).to_csv(tmp_path / "sample_submission.csv", index=False)
    with pytest.raises(ValueError, match="one row"):
        load_task(task)


def test_no_output_escape_or_input_overwrite(tmp_path):
    task = task_files(tmp_path)
    for output in (Path("../escaped.csv"), Path("train.csv")):
        with pytest.raises(ValueError, match="new CSV"):
            load_task(task, output)


def test_generated_config_cannot_become_arbitrary_code():
    with pytest.raises(ValueError):
        Plan.parse({"algorithm": "linear", "code": "import os"})
    with pytest.raises(ValueError):
        Plan.parse({"algorithm": "__import__('os')"})
    with pytest.raises(ValueError):
        Plan.parse({"algorithm": "hist_gradient", "parameters": {"iterations": 10**9}})


def test_emergency_checkpoint_survives_failed_trials(tmp_path, monkeypatch):
    task = task_files(tmp_path)

    def fail(*args, **kwargs):
        raise TimeoutError("test")

    monkeypatch.setattr("app.competition.engine.run_trial", fail)
    state = research(task, seconds=30, max_experiments=2, threads=1, offline=True)
    assert state["checkpoint"] == "emergency_constant"
    assert "best" not in state
    assert len(pd.read_csv(tmp_path / "submission.csv")) == 17
    assert all(item["decision"] == "reject" for item in state["experiments"])


def test_official_scores():
    assert normalized_score("rmse", 5, 10) == 50
    assert normalized_score("rmse", 11, 10) == 0
    assert normalized_score("f1_macro", 0.7, 0.4) == pytest.approx(50)
    assert normalized_score("f1_macro", 1, 0.4) == 100
    assert combined_score(50, 100) == 75
    with pytest.raises(ValueError):
        normalized_score("rmse", 1, 0)


def test_only_organizer_model_is_allowed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://organizer.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "another-provider-model")
    with pytest.raises(ValueError, match="Qwen"):
        ResearchPlanner()
    monkeypatch.setenv("OPENAI_MODEL", "Qwen3.8-27B")
    assert ResearchPlanner().model == "Qwen3.8-27B"


def test_competition_api_lifecycle_and_ownership(signed, tmp_path, monkeypatch):
    from app.services import runner
    from fastapi.testclient import TestClient
    from app.main import app
    from conftest import register

    task = task_files(tmp_path)
    files = {
        key: (filename, (tmp_path / filename).read_bytes(), "text/csv")
        for key, filename in (
            ("train", "train.csv"),
            ("test", "test.csv"),
            ("dictionary", "data_dictionary.csv"),
            ("sample", "sample_submission.csv"),
        )
    }
    response = signed.post(
        "/api/competition/projects", data={"name": "Research", "description": task.read_text()}, files=files
    )
    assert response.status_code == 201, response.text
    pid = response.json()["project"]["id"]
    assert signed.get(f"/api/projects/{pid}").json()["mode"] == "competition"
    assert signed.get(f"/api/competition/projects/{pid}/submission").status_code == 409
    monkeypatch.setattr(runner.executor, "submit", lambda *args: None)
    response = signed.post(
        f"/api/competition/projects/{pid}/run",
        json={
            "offline": True,
            "time_budget_seconds": 60,
            "max_experiments": 2,
            "trial_timeout_seconds": 20,
            "threads": 1,
        },
    )
    assert response.status_code == 202, response.text
    runner.execute_run(response.json()["run_id"])
    state = signed.get(f"/api/competition/projects/{pid}").json()
    assert state["project"]["status"] == "completed", state
    assert state["research"]["best"]
    assert signed.get(f"/api/competition/projects/{pid}/submission").status_code == 200
    assert signed.get(f"/api/competition/projects/{pid}/research").status_code == 200
    other = TestClient(app)
    register(other, "bob@example.com")
    assert other.get(f"/api/competition/projects/{pid}").status_code == 404
    assert other.get(f"/api/competition/projects/{pid}/submission").status_code == 404
    assert other.post(f"/api/competition/projects/{pid}/run", json={"offline": True}).status_code == 404


def test_invalid_competition_bundle_leaves_no_project(signed, tmp_path):
    task = task_files(tmp_path)
    files = {
        key: (filename, (tmp_path / filename).read_bytes(), "text/csv")
        for key, filename in (
            ("train", "train.csv"),
            ("test", "test.csv"),
            ("dictionary", "data_dictionary.csv"),
            ("sample", "sample_submission.csv"),
        )
    }
    files["sample"] = ("sample_submission.csv", b"id,answer\nwrong,0\n", "text/csv")
    response = signed.post(
        "/api/competition/projects", data={"name": "Invalid", "description": task.read_text()}, files=files
    )
    assert response.status_code == 400
    assert signed.get("/api/projects").json() == []


def test_qwen_planner_uses_feedback_and_bounded_contract(monkeypatch):
    import httpx

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_MODEL", "Qwen3.8-27B")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://organizer.invalid/v1")
    real_client = httpx.Client
    seen = []

    def respond(request):
        body = json.loads(request.content)
        seen.append(body)
        assert request.headers["Authorization"] == "Bearer test-only-key"
        assert body["model"] == "Qwen3.8-27B"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "algorithm": "hist_gradient",
                                    "parameters": {"iterations": 100},
                                    "hypothesis": "Nonlinear effects may reduce validation error",
                                    "rationale": "The linear baseline underfits",
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 500},
            },
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(respond), **kwargs)
    )
    planner = ResearchPlanner(max_calls=1, max_tokens=10000)
    plan = planner.propose(
        "RMSE task", {"task_type": "regression"}, [{"score": 2.0, "train_score": 1.9}], {"hist_gradient"}, 50
    )
    assert plan.algorithm == "hist_gradient"
    assert plan.source == "llm"
    assert planner.calls == 1 and planner.tokens == 500
    assert "2.0" in seen[0]["messages"][1]["content"]
    assert planner.propose("ignored", {}, [], {"hist_gradient"}, 50) is None


def test_raw_class_labels_are_preserved(tmp_path):
    task = task_files(tmp_path, classification=True)
    train = pd.read_csv(tmp_path / "train.csv")
    train["answer"] = train.answer.map({"red": "01", "blue": "02", "green": "NA"})
    train.to_csv(tmp_path / "train.csv", index=False)
    loaded = load_task(task)
    assert set(loaded.train.answer) == {"01", "02", "NA"}


def test_trial_cancellation_kills_process_and_strips_credentials(tmp_path, monkeypatch):
    import subprocess
    from app.competition.engine import run_trial

    processes = []
    real_popen = subprocess.Popen
    monkeypatch.setenv("OPENAI_API_KEY", "test-never-forward-to-trial")
    monkeypatch.setenv("DATABASE_URL", "test-never-forward-to-trial")

    def spawn(*args, **kwargs):
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert "DATABASE_URL" not in kwargs["env"]
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    def cancelled():
        raise RuntimeError("test cancellation")

    monkeypatch.setattr(subprocess, "Popen", spawn)
    with pytest.raises(RuntimeError, match="test cancellation"):
        run_trial(
            tmp_path / "unused.joblib", tmp_path / "cancelled", Plan(), 20, 42, 1, check_cancelled=cancelled
        )
    assert processes and processes[0].poll() is not None


def test_auc_emergency_predictions_are_probabilities(tmp_path, monkeypatch):
    task = task_files(tmp_path, classification=True)
    train = pd.read_csv(tmp_path / "train.csv")
    train["answer"] = train.answer.map({"red": "yes", "blue": "no", "green": "no"})
    train.to_csv(tmp_path / "train.csv", index=False)
    task.write_text("Metric: ROC AUC\nWrite submission.csv", encoding="utf-8")

    def fail(*args, **kwargs):
        raise TimeoutError("test")

    monkeypatch.setattr("app.competition.engine.run_trial", fail)
    research(task, offline=True, seconds=30, max_experiments=1, threads=1)
    output = pd.read_csv(tmp_path / "submission.csv")
    assert output.answer.between(0, 1).all()
    assert output.answer.iloc[0] == pytest.approx((train.answer == "yes").mean())
