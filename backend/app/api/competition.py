import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .. import db
from ..competition.data import load_task, task_summary
from ..competition.web import report
from ..config import UPLOADS_DIR
from ..security import current_user, require_authenticated_user, require_project_owner
from ..services import runner
from ..settings import get_settings

router = APIRouter(prefix="/competition", dependencies=[Depends(require_authenticated_user)])


class CompetitionRun(BaseModel):
    time_budget_seconds: int = Field(default=10800, ge=30, le=10800)
    max_experiments: int = Field(default=24, ge=2, le=64)
    trial_timeout_seconds: int = Field(default=1200, ge=5, le=1800)
    threads: int = Field(default=8, ge=1, le=8)
    max_llm_calls: int = Field(default=16, ge=0, le=32)
    max_llm_tokens: int = Field(default=24000, ge=0, le=100000)
    offline: bool = False


def owned_project(pid):
    project = require_project_owner(pid)
    if not project.get("dataset_path") or not (Path(project["dataset_path"]).parent / "task.md").exists():
        raise HTTPException(404, "Competition task not found")
    return project


@router.post("/projects", status_code=201)
async def create_competition(
    name: str = Form(..., min_length=1, max_length=120),
    description: str = Form(..., min_length=1, max_length=40000),
    train: UploadFile = File(...),
    test: UploadFile = File(...),
    dictionary: UploadFile = File(...),
    sample: UploadFile = File(...),
):
    # Stage files before creating the project; a bad bundle never leaves a DB record.
    staging = UPLOADS_DIR / ("competition-" + str(uuid.uuid4()))
    staging.mkdir(parents=True)
    try:
        for upload, filename in (
            (train, "train.csv"),
            (test, "test.csv"),
            (dictionary, "data_dictionary.csv"),
            (sample, "sample_submission.csv"),
        ):
            if not (upload.filename or "").lower().endswith(".csv"):
                raise HTTPException(400, "Each task material must be a CSV file")
            size = 0
            with (staging / filename).open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if b"\x00" in chunk:
                        raise HTTPException(400, "Binary files are not valid CSV")
                    if size > get_settings().competition_max_upload_mb * 1024 * 1024:
                        raise HTTPException(413, "Competition CSV exceeds upload limit")
                    destination.write(chunk)
        (staging / "task.md").write_text(description, encoding="utf-8")
        try:
            task = await run_in_threadpool(load_task, staging / "task.md")
        except (ValueError, KeyError, UnicodeError) as error:
            raise HTTPException(400, str(error)) from None
        summary = task_summary(task)
        project = db.create_project(name, description, current_user.get()["id"])
        directory = UPLOADS_DIR / project["id"]
        directory.mkdir(exist_ok=True)
        materials = directory / "competition"
        shutil.move(str(staging), str(materials))
        db.update_project(
            project["id"],
            dataset_name="train.csv + test.csv",
            dataset_path=str(materials / "train.csv"),
            target_column=task.target,
            primary_metric=task.metric,
            task_type=task.kind,
        )
        db.audit(current_user.get()["id"], "competition_upload", project["id"])
        return {"project": {"id": project["id"], "name": name}, "profile": summary}
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        for upload in (train, test, dictionary, sample):
            await upload.close()


@router.get("/projects/{pid}")
def get_competition(pid: str):
    project = owned_project(pid)
    return {
        "project": {
            key: project.get(key)
            for key in (
                "id",
                "name",
                "status",
                "stage",
                "error",
                "target_column",
                "primary_metric",
                "best_model_type",
                "best_metric_value",
            )
        },
        "research": report(project),
    }


@router.post("/projects/{pid}/run", status_code=202)
def start_competition(pid: str, body: CompetitionRun):
    owned_project(pid)
    if not body.offline:
        from ..competition.planner import ResearchPlanner

        try:
            ResearchPlanner(body.max_llm_calls, body.max_llm_tokens)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None
    try:
        rid = runner.start_run(pid, {**body.model_dump(), "mode": "competition"})
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from None
    return {"run_id": rid, "status": "queued"}


@router.get("/projects/{pid}/submission")
def download_submission(pid: str):
    project = owned_project(pid)
    details = report(project)
    if not details:
        raise HTTPException(409, "Prediction checkpoint is not ready")
    root = Path(project["dataset_path"]).parent.resolve()
    output = Path(details["output"]).resolve()
    if not output.is_relative_to(root) or not output.is_file():
        raise HTTPException(404, "Prediction file not found")
    db.audit(current_user.get()["id"], "competition_download", pid)
    return FileResponse(output, media_type="text/csv", filename=output.name)


@router.get("/projects/{pid}/research")
def download_research(pid: str):
    project = owned_project(pid)
    path = Path(project["dataset_path"]).parent / "research.json"
    if not path.exists():
        raise HTTPException(409, "Research history is not ready")
    return FileResponse(path, media_type="application/json", filename="research.json")
