import json
import time
import hashlib
import asyncio
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query, Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, delete
from fastapi.responses import FileResponse, Response, StreamingResponse

from .. import db
from ..agents.data_analyst import profile_dataframe
from ..config import DEMO_CSV, LOWER_IS_BETTER, ARTIFACTS_DIR, UPLOADS_DIR
from ..security import require_authenticated_user, require_project_owner, current_user
from ..settings import get_settings
from .. import models as m
from ..schemas import (
    AgentEvent,
    ChatRequest,
    ChatResponse,
    CreateProjectRequest,
    DatasetProfile,
    Experiment,
    FinalReport,
    PredictionRequest,
    PredictionResponse,
    Project,
    RunRequest,
    RunStatus,
)
from ..services import runner
from ..services.llm import narrate
from ..services.storage import upload_path, remove_project_files

router = APIRouter(dependencies=[Depends(require_authenticated_user)])

_model_cache: dict[str, tuple] = {}


def _get_project_or_404(pid: str) -> dict:
    return require_project_owner(pid)


def _attach_demo_dataset(p: dict) -> dict:
    from ..demo_data import generate_demo_csv

    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
    df = pd.read_csv(DEMO_CSV)
    profile = profile_dataframe(df)
    db.update_project(
        p["id"],
        status="created",
        report_json=None,
        task_json=None,
        best_experiment_id=None,
        best_metric_value=None,
        best_model_type=None,
        dataset_name="churn_demo.csv",
        dataset_path=str(DEMO_CSV),
        profile_json=profile.model_dump(),
    )
    return profile.model_dump()


# ---------------- projects ----------------


@router.get("/projects", response_model=list[Project])
def list_projects(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    return [_project_view(p) for p in db.list_projects(current_user.get()["id"], offset, limit)]


@router.post("/projects", response_model=Project, status_code=201)
def create_project(body: CreateProjectRequest):
    p = db.create_project(body.name, body.description, current_user.get()["id"])
    db.audit(current_user.get()["id"], "create_project", p["id"])
    if body.use_demo_dataset:
        _attach_demo_dataset(p)
    if body.target_column or body.primary_metric:
        db.update_project(
            p["id"],
            status="created",
            report_json=None,
            task_json=None,
            best_experiment_id=None,
            best_metric_value=None,
            best_model_type=None,
            **{
                k: v
                for k, v in {
                    "target_column": body.target_column,
                    "primary_metric": body.primary_metric,
                }.items()
                if v
            },
        )
    return _project_view(db.get_project(p["id"]))


@router.get("/projects/{pid}", response_model=Project)
def get_project(pid: str):
    return _project_view(_get_project_or_404(pid))


def _project_view(p: dict) -> dict:
    return {k: p.get(k) for k in Project.model_fields}


@router.post("/projects/{pid}/dataset", response_model=DatasetProfile)
async def upload_dataset(pid: str, file: Optional[UploadFile] = File(None), demo: bool = Form(False)):
    p = _get_project_or_404(pid)
    if runner.is_running(pid):
        raise HTTPException(409, "Wait for the active run before replacing the dataset")
    if demo:
        return await run_in_threadpool(_attach_demo_dataset, p)
    if file is None:
        raise HTTPException(400, "Provide a CSV file or set demo=true")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")
    if file.content_type not in {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",
        "application/octet-stream",
    }:
        raise HTTPException(400, "Unsupported CSV content type")
    path = upload_path(pid, file.filename or "dataset.csv")
    try:
        size = 0
        with path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > get_settings().max_upload_size_mb * 1024 * 1024:
                    raise HTTPException(413, "CSV exceeds upload size limit")
                if b"\x00" in chunk:
                    raise HTTPException(400, "Binary files are not supported")
                destination.write(chunk)
        try:
            profile = await asyncio.wait_for(run_in_threadpool(_profile_csv, path), timeout=20)
        except TimeoutError:
            raise HTTPException(408, "CSV profiling timed out. Use a smaller dataset.") from None
        db.update_project(
            pid,
            status="created",
            report_json=None,
            task_json=None,
            best_experiment_id=None,
            best_metric_value=None,
            best_model_type=None,
            dataset_name=Path(file.filename).name[:255],
            dataset_path=str(path),
            profile_json=profile.model_dump(),
        )
        db.audit(current_user.get()["id"], "upload_dataset", pid)
        return profile
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def _profile_csv(path):
    try:
        df = pd.read_csv(path, nrows=get_settings().max_rows + 1, encoding="utf-8-sig")
    except (ValueError, UnicodeError, pd.errors.ParserError):
        raise HTTPException(
            400, "Could not parse CSV. Use UTF-8 and a consistent comma-separated header."
        ) from None
    if df.empty or df.shape[1] < 2:
        raise HTTPException(400, "Dataset must have at least 2 columns and 1 row")
    if len(df) > get_settings().max_rows or df.shape[1] > get_settings().max_columns:
        raise HTTPException(413, "Dataset exceeds row or column limit")
    if any(len(str(c)) > 200 for c in df.columns):
        raise HTTPException(400, "Column names must be at most 200 characters")
    return profile_dataframe(df)


@router.post("/projects/{pid}/run")
def run_project(pid: str, body: RunRequest):
    p = _get_project_or_404(pid)
    if not p.get("dataset_path"):
        raise HTTPException(400, "Attach a dataset first")
    if p.get("status") == "running" or runner.is_running(pid):
        raise HTTPException(409, "Run already in progress")
    run_config = body.model_dump()
    run_config["max_experiments"] = min(run_config["max_experiments"], get_settings().max_experiments)
    try:
        rid = runner.start_run(pid, run_config)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    db.audit(current_user.get()["id"], "start_run", pid)
    return {"status": "queued", "project_id": pid, "run_id": rid}


@router.get("/projects/{pid}/status", response_model=RunStatus)
def project_status(pid: str):
    p = _get_project_or_404(pid)
    stages = p.get("stages_json") or []
    done = sum(1 for s in stages if s["status"] in ("completed", "skipped"))
    progress = round(done / len(stages), 3) if stages else 0.0
    if p["status"] == "completed":
        progress = 1.0
    return {
        "project_id": pid,
        "status": p["status"],
        "stage": p.get("stage"),
        "stages": stages,
        "progress": progress,
        "error": p.get("error"),
    }


@router.get("/projects/{pid}/events", response_model=list[AgentEvent])
def project_events(pid: str, after_id: int = 0):
    _get_project_or_404(pid)
    return db.list_events(pid, after_id=after_id)


@router.get("/projects/{pid}/events/stream")
def project_events_stream(pid: str, request: Request, after_id: int = Query(0, ge=0), run_id: str = None):
    _get_project_or_404(pid)

    def gen():
        try:
            last_id = max(after_id, int(request.headers.get("last-event-id", "0")))
        except ValueError:
            last_id = after_id
        last_ping = time.time()
        terminal_since = None
        while True:
            events = db.list_events(pid, after_id=last_id, run_id=run_id)
            for e in events:
                last_id = e["id"]
                yield f"id: {e['id']}\ndata: {json.dumps(e, default=str)}\n\n"
            p = db.get_project(pid)
            status = (p or {}).get("status")
            if status in ("completed", "failed", "cancelled"):
                terminal_since = terminal_since or time.time()
                if time.time() - terminal_since > 2:
                    yield "event: close\ndata: {}\n\n"
                    return
            if time.time() - last_ping > 15:
                yield ": ping\n\n"
                last_ping = time.time()
            time.sleep(1)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/projects/{pid}/profile", response_model=DatasetProfile)
def project_profile(pid: str):
    p = _get_project_or_404(pid)
    if not p.get("profile_json"):
        raise HTTPException(404, "No dataset profile yet")
    return p["profile_json"]


@router.get("/projects/{pid}/experiments", response_model=list[Experiment])
def project_experiments(pid: str, run_id: Optional[str] = None):
    p = _get_project_or_404(pid)
    if run_id:
        _run_or_404(pid, run_id)
    else:
        with db.SessionLocal() as s:
            run_id = s.scalar(
                select(m.AgentRun.id)
                .where(m.AgentRun.project_id == pid)
                .order_by(m.AgentRun.created_at.desc())
                .limit(1)
            )
    experiments = db.list_experiments(pid, run_id=run_id)
    primary = p.get("primary_metric") or "f1"
    lower = primary in LOWER_IS_BETTER

    def key(e):
        if e["status"] != "completed" or e["primary_metric_value"] is None:
            return float("inf")
        return e["primary_metric_value"] if lower else -e["primary_metric_value"]

    return sorted(experiments, key=key)


def _best_experiment(p: dict) -> dict:
    if not p.get("best_experiment_id"):
        raise HTTPException(404, "No best model yet — run the pipeline first")
    exp = next((e for e in db.list_experiments(p["id"]) if e["id"] == p["best_experiment_id"]), None)
    if exp is None or not exp.get("artifact_path"):
        raise HTTPException(404, "Best model artifact not found")
    return exp


@router.get("/projects/{pid}/report", response_model=FinalReport)
def project_report(pid: str):
    p = _get_project_or_404(pid)
    if not p.get("report_json"):
        raise HTTPException(404, "Report is not ready yet")
    return p["report_json"]


@router.get("/projects/{pid}/model")
def download_model(pid: str):
    p = _get_project_or_404(pid)
    exp = _best_experiment(p)
    _verify_artifact(exp)
    db.audit(current_user.get()["id"], "download_model", pid)
    return FileResponse(
        exp["artifact_path"], media_type="application/octet-stream", filename="mlution_model.joblib"
    )


@router.get("/projects/{pid}/model/code")
@router.get("/projects/{pid}/code")
def download_code(pid: str):
    p = _get_project_or_404(pid)
    if not p.get("report_json"):
        raise HTTPException(404, "Code is available after the run completes")
    code = p["report_json"]["usage_code"]
    return Response(
        content=code,
        media_type="text/x-python",
        headers={"Content-Disposition": 'attachment; filename="mlution_inference.py"'},
    )


def _load_best_bundle(p: dict):
    exp = _best_experiment(p)
    _verify_artifact(exp)
    key = f"{p['id']}:{exp['id']}"
    if key not in _model_cache:
        _model_cache.clear()
        _model_cache[key] = (joblib.load(exp["artifact_path"]), exp)
    return _model_cache[key]


def _verify_artifact(exp):
    path = Path(exp["artifact_path"]).resolve()
    if not path.is_relative_to(ARTIFACTS_DIR.resolve()) or not path.is_file():
        raise HTTPException(404, "Model artifact is unavailable")
    if (
        not exp.get("artifact_sha256")
        or hashlib.sha256(path.read_bytes()).hexdigest() != exp["artifact_sha256"]
    ):
        raise HTTPException(409, "Model integrity verification failed; retrain the model")


@router.post("/projects/{pid}/predict", response_model=PredictionResponse)
def predict(pid: str, body: PredictionRequest):
    p = _get_project_or_404(pid)
    bundle, exp = _load_best_bundle(p)
    pipe, meta = bundle["pipeline"], bundle["meta"]

    features = meta["features"]
    if set(body.features) - set(features):
        raise HTTPException(422, "Unknown prediction features")
    if any(isinstance(v, (dict, list)) for v in body.features.values()):
        raise HTTPException(422, "Feature values must be scalar")
    row = {f: body.features.get(f) for f in features}
    df = pd.DataFrame([row])
    for col in meta.get("numeric_features", []):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    for col in df.columns:
        if col not in meta.get("numeric_features", []):
            df[col] = df[col].astype(object).where(df[col].notna(), None)

    probabilities = None
    probability = None
    if meta["task_type"] != "regression" and hasattr(pipe, "predict_proba"):
        proba = pipe.predict_proba(df)[0]
        classes = meta["classes"] or [str(c) for c in pipe.classes_]
        probabilities = {c: round(float(v), 4) for c, v in zip(classes, proba)}
        if len(classes) == 2:
            threshold = meta.get("threshold") or 0.5
            prediction = classes[1] if float(proba[1]) >= threshold else classes[0]
            selected = 1 if prediction == classes[1] else 0
            probability = round(float(proba[selected]), 4)
        else:
            idx = int(np.argmax(proba))
            prediction = classes[idx]
            probability = round(float(proba[idx]), 4)
        try:
            prediction = prediction.item() if hasattr(prediction, "item") else prediction
        except Exception:
            pass
    else:
        prediction = float(pipe.predict(df)[0])

    top = (exp.get("feature_importance") or [])[:5]
    with db.SessionLocal.begin() as s:
        s.add(m.PredictionLog(project_id=pid, experiment_id=exp["id"]))
    top_names = ", ".join(f["feature"] for f in top[:3]) or "n/a"
    if probability is not None:
        explanation = (
            f"Model '{exp['name']}' predicts '{prediction}'; predicted-class probability is {probability:.0%}"
            + (
                f" (decision threshold {meta.get('threshold') or 0.5:.2f})"
                if len(probabilities or {}) == 2
                else ""
            )
            + f". Global feature importance (not a per-prediction explanation): {top_names}."
        )
    else:
        explanation = (
            f"Model '{exp['name']}' predicts {prediction:.4f}. Most influential features: {top_names}."
        )

    return PredictionResponse(
        prediction=prediction,
        probability=probability,
        probabilities=probabilities,
        model_type=exp["model_type"],
        explanation=explanation,
        top_factors=top,
    )


@router.post("/projects/{pid}/chat", response_model=ChatResponse)
def chat(pid: str, body: ChatRequest):
    p = _get_project_or_404(pid)
    status = p["status"]
    if status == "created" and not p.get("dataset_path"):
        fallback = (
            "Attach a CSV dataset (or use the built-in churn demo) and press Run — I'll take it from there."
        )
    elif status == "created":
        fallback = "Dataset is ready. Press Run to start the analysis and training pipeline."
    elif status == "running":
        fallback = f"I'm working on it — current stage: {p.get('stage') or 'starting'}. Watch the pipeline timeline for live progress."
    elif status == "failed":
        fallback = f"The run failed: {p.get('error') or 'unknown error'}. Check the Logs tab for details, then try running again."
    else:
        metric = p.get("primary_metric") or "metric"
        value = p.get("best_metric_value")
        fallback = (
            f"All done. Best model: {p.get('best_model_type')} with validation {metric} = {value:.4f}."
            if value is not None
            else "Run completed."
        ) + " Open Results for the full comparison or the Playground to test predictions."
    reply = narrate(
        f"A user asked: '{body.message}'. Reply as the Mlution agent using only the project facts below.",
        f"Project status: {status}. Stage: {p.get('stage')}. Task: {p.get('task_type')}. "
        f"Target: {p.get('target_column')}. Primary metric: {p.get('primary_metric')} = {p.get('best_metric_value')}. "
        f"Best model: {p.get('best_model_type')}. Error: {p.get('error')}.",
        fallback,
    )
    with db.SessionLocal.begin() as s:
        s.add_all(
            [
                m.ChatMessage(project_id=pid, role="user", message=body.message),
                m.ChatMessage(project_id=pid, role="assistant", message=reply),
            ]
        )
    return ChatResponse(reply=reply, ts=db.utcnow())


@router.get("/projects/{pid}/chat")
def chat_history(pid: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    _get_project_or_404(pid)
    with db.SessionLocal() as s:
        return [
            db.view(row)
            for row in s.scalars(
                select(m.ChatMessage)
                .where(m.ChatMessage.project_id == pid)
                .order_by(m.ChatMessage.created_at)
                .offset(offset)
                .limit(limit)
            )
        ]


@router.patch("/projects/{pid}", response_model=Project)
def patch_project(pid: str, body: CreateProjectRequest):
    _get_project_or_404(pid)
    if runner.is_running(pid):
        raise HTTPException(409, "Wait for the active run")
    db.update_project(
        pid,
        name=body.name,
        description=body.description,
        target_column=body.target_column,
        primary_metric=body.primary_metric,
    )
    return _project_view(db.get_project(pid))


@router.delete("/projects/{pid}")
def delete_project(pid: str):
    _get_project_or_404(pid)
    if runner.is_running(pid):
        raise HTTPException(409, "Cancel the active run before deleting the project")
    db.delete_project(pid)
    remove_project_files(pid)
    db.audit(current_user.get()["id"], "delete_project", pid)
    return {"status": "ok"}


@router.delete("/projects/{pid}/dataset")
def delete_dataset(pid: str):
    p = _get_project_or_404(pid)
    if runner.is_running(pid):
        raise HTTPException(409, "Wait for the active run")
    with db.SessionLocal.begin() as s:
        s.execute(delete(m.Dataset).where(m.Dataset.project_id == pid))
    db.update_project(pid, dataset_name=None, dataset_path=None, profile_json=None)
    if p.get("dataset_path"):
        path = Path(p["dataset_path"]).resolve()
        if path.is_relative_to(UPLOADS_DIR.resolve()):
            path.unlink(missing_ok=True)
    return {"status": "ok"}


def _run_or_404(pid, rid):
    _get_project_or_404(pid)
    with db.SessionLocal() as s:
        run = s.get(m.AgentRun, rid)
        if not run or run.project_id != pid:
            raise HTTPException(404, "Run not found")
        return db.view(run)


@router.get("/projects/{pid}/runs")
def list_runs(pid: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    _get_project_or_404(pid)
    with db.SessionLocal() as s:
        return [
            db.view(run)
            for run in s.scalars(
                select(m.AgentRun)
                .where(m.AgentRun.project_id == pid)
                .order_by(m.AgentRun.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ]


@router.get("/projects/{pid}/runs/{rid}")
def get_run(pid: str, rid: str):
    return _run_or_404(pid, rid)


@router.post("/projects/{pid}/runs/{rid}/cancel")
def cancel_run(pid: str, rid: str):
    _run_or_404(pid, rid)
    return runner.cancel_run(pid, rid)


@router.post("/projects/{pid}/runs/{rid}/retry")
def retry_run(pid: str, rid: str):
    run = _run_or_404(pid, rid)
    return run_project(pid, RunRequest(**json.loads(run["config_json"])))


@router.post("/projects/{pid}/runs/{rid}/stages/{stage}/retry")
def retry_stage(pid: str, rid: str, stage: str):
    _run_or_404(pid, rid)
    if stage != "finalize":
        raise HTTPException(409, "This stage depends on in-memory training state; retry the full run")
    p = _get_project_or_404(pid)
    if runner.is_running(pid) or not p.get("report_json"):
        raise HTTPException(409, "A completed report is required")
    from ..agents.report import ReportAgent
    from ..agents.base import AgentContext

    report = p["report_json"]
    if not any(e["id"] == p["best_experiment_id"] for e in db.list_experiments(pid, rid)):
        raise HTTPException(409, "Only the current model's run can regenerate its report")
    token = db.run_context.set(rid)
    try:
        ReportAgent(AgentContext(pid)).run(
            p["task_json"],
            p["profile_json"],
            db.list_experiments(pid, rid),
            report.get("improvements", []),
            [],
        )
    finally:
        db.run_context.reset(token)
    return db.get_project(pid)["report_json"]


@router.get("/projects/{pid}/runs/{rid}/events")
def run_events(pid: str, rid: str, after_id: int = Query(0, ge=0)):
    _run_or_404(pid, rid)
    return db.list_events(pid, after_id=after_id, run_id=rid)


@router.get("/projects/{pid}/runs/{rid}/events/stream")
def run_stream(pid: str, rid: str, request: Request, after_id: int = Query(0, ge=0)):
    _run_or_404(pid, rid)
    return project_events_stream(pid, request, after_id, rid)


@router.get("/projects/{pid}/experiments/compare")
def compare_experiments(pid: str, first: str, second: str):
    _get_project_or_404(pid)
    selected = [e for e in db.list_experiments(pid) if e["id"] in {first, second}]
    if len(selected) != 2:
        raise HTTPException(404, "Select two distinct experiments from this project")
    return selected


@router.get("/projects/{pid}/experiments/{eid}", response_model=Experiment)
def experiment_detail(pid: str, eid: str):
    _get_project_or_404(pid)
    result = next((e for e in db.list_experiments(pid) if e["id"] == eid), None)
    if not result:
        raise HTTPException(404, "Experiment not found")
    return result
