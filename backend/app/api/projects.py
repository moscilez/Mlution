import json
import time
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

from .. import db
from ..agents.data_analyst import profile_dataframe
from ..config import DEMO_CSV, LOWER_IS_BETTER
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
from ..services.storage import upload_path

router = APIRouter()

_model_cache: dict[str, tuple] = {}


def _get_project_or_404(pid: str) -> dict:
    p = db.get_project(pid)
    if p is None:
        raise HTTPException(404, "Project not found")
    return p


def _attach_demo_dataset(p: dict) -> dict:
    from ..demo_data import generate_demo_csv

    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
    df = pd.read_csv(DEMO_CSV)
    profile = profile_dataframe(df)
    db.update_project(p["id"], dataset_name="churn_demo.csv", dataset_path=str(DEMO_CSV),
                      profile_json=profile.model_dump())
    return profile.model_dump()


# ---------------- projects ----------------

@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/projects", response_model=list[Project])
def list_projects():
    return [_project_view(p) for p in db.list_projects()]


@router.post("/projects", response_model=Project, status_code=201)
def create_project(body: CreateProjectRequest):
    p = db.create_project(body.name, body.description)
    if body.use_demo_dataset:
        _attach_demo_dataset(p)
    if body.target_column or body.primary_metric:
        db.update_project(p["id"], **{k: v for k, v in {
            "target_column": body.target_column, "primary_metric": body.primary_metric}.items() if v})
    return _project_view(db.get_project(p["id"]))


@router.get("/projects/{pid}", response_model=Project)
def get_project(pid: str):
    return _project_view(_get_project_or_404(pid))


def _project_view(p: dict) -> dict:
    return {k: p.get(k) for k in Project.model_fields}


@router.post("/projects/{pid}/dataset", response_model=DatasetProfile)
async def upload_dataset(pid: str, file: Optional[UploadFile] = File(None), demo: bool = Form(False)):
    p = _get_project_or_404(pid)
    if demo:
        return _attach_demo_dataset(p)
    if file is None:
        raise HTTPException(400, "Provide a CSV file or set demo=true")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")
    raw = await file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large (50 MB limit)")
    path = upload_path(pid, file.filename or "dataset.csv")
    path.write_bytes(raw)
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}")
    if df.empty or df.shape[1] < 2:
        raise HTTPException(400, "Dataset must have at least 2 columns and 1 row")
    profile = profile_dataframe(df)
    db.update_project(pid, dataset_name=file.filename, dataset_path=str(path), profile_json=profile.model_dump())
    return profile


@router.post("/projects/{pid}/run")
def run_project(pid: str, body: RunRequest):
    p = _get_project_or_404(pid)
    if not p.get("dataset_path"):
        raise HTTPException(400, "Attach a dataset first")
    if p.get("status") == "running" or runner.is_running(pid):
        raise HTTPException(409, "Run already in progress")
    run_config = body.model_dump()
    try:
        runner.start_run(pid, run_config)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    return {"status": "running", "project_id": pid}


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
def project_events_stream(pid: str):
    _get_project_or_404(pid)

    def gen():
        last_id = 0
        last_ping = time.time()
        terminal_since = None
        while True:
            events = db.list_events(pid, after_id=last_id)
            for e in events:
                last_id = e["id"]
                yield f"data: {json.dumps(e, default=str)}\n\n"
            p = db.get_project(pid)
            status = (p or {}).get("status")
            if status in ("completed", "failed"):
                terminal_since = terminal_since or time.time()
                if time.time() - terminal_since > 2:
                    yield "event: close\ndata: {}\n\n"
                    return
            if time.time() - last_ping > 15:
                yield ": ping\n\n"
                last_ping = time.time()
            time.sleep(1)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/projects/{pid}/profile", response_model=DatasetProfile)
def project_profile(pid: str):
    p = _get_project_or_404(pid)
    if not p.get("profile_json"):
        raise HTTPException(404, "No dataset profile yet")
    return p["profile_json"]


@router.get("/projects/{pid}/experiments", response_model=list[Experiment])
def project_experiments(pid: str):
    p = _get_project_or_404(pid)
    experiments = db.list_experiments(pid)
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
    return FileResponse(exp["artifact_path"], media_type="application/octet-stream", filename="mlution_model.joblib")


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
    key = f"{p['id']}:{exp['id']}"
    if key not in _model_cache:
        _model_cache.clear()
        _model_cache[key] = (joblib.load(exp["artifact_path"]), exp)
    return _model_cache[key]


@router.post("/projects/{pid}/predict", response_model=PredictionResponse)
def predict(pid: str, body: PredictionRequest):
    p = _get_project_or_404(pid)
    bundle, exp = _load_best_bundle(p)
    pipe, meta = bundle["pipeline"], bundle["meta"]

    features = meta["features"]
    row = {f: body.features.get(f) for f in features}
    df = pd.DataFrame([row])
    for col in meta.get("numeric_features", []):
        df[col] = pd.to_numeric(df[col], errors="coerce")
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
            probability = round(float(proba[1]), 4)
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
    top_names = ", ".join(f["feature"] for f in top[:3]) or "n/a"
    if probability is not None:
        explanation = (
            f"Model '{exp['name']}' predicts '{prediction}' with {probability:.0%} confidence"
            + (f" (decision threshold {meta.get('threshold') or 0.5:.2f})" if len(probabilities or {}) == 2 else "")
            + f". Most influential features: {top_names}."
        )
    else:
        explanation = f"Model '{exp['name']}' predicts {prediction:.4f}. Most influential features: {top_names}."

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
        fallback = "Attach a CSV dataset (or use the built-in churn demo) and press Run — I'll take it from there."
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
            f"All done. Best model: {p.get('best_model_type')} with validation {metric} = "
            f"{value:.4f}." if value is not None else "Run completed."
        ) + " Open Results for the full comparison or the Playground to test predictions."
    reply = narrate(
        f"A user asked: '{body.message}'. Reply as the Mlution agent using only the project facts below.",
        f"Project status: {status}. Stage: {p.get('stage')}. Task: {p.get('task_type')}. "
        f"Target: {p.get('target_column')}. Primary metric: {p.get('primary_metric')} = {p.get('best_metric_value')}. "
        f"Best model: {p.get('best_model_type')}. Error: {p.get('error')}.",
        fallback,
    )
    return ChatResponse(reply=reply, ts=db.utcnow())
