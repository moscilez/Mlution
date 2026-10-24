"""Bridge portable research events into the existing owned project/run model."""

import json
from pathlib import Path

from .. import db
from ..config import STAGES


def execute(project_id, config, run_id):
    from .engine import research
    from ..agents.base import RunCancelled
    from ..models import AgentRun

    project = db.get_project(project_id)
    root = Path(project["dataset_path"]).parent
    completed = set()
    current_stage = None

    def check_cancelled():
        with db.SessionLocal() as session:
            run = session.get(AgentRun, run_id)
            if not run or run.cancel_requested:
                raise RunCancelled()

    def emit(stage, message, data=None):
        nonlocal current_stage
        check_cancelled()
        if current_stage and current_stage != stage:
            completed.add(current_stage)
        current_stage = stage
        db.update_project(
            project_id,
            stage=stage,
            stages_json=[
                {
                    "name": name,
                    "status": "running" if name == stage else "completed" if name in completed else "pending",
                    "started_at": None,
                    "finished_at": None,
                }
                for name in STAGES
            ],
        )
        db.add_event(project_id, "AutoResearch", stage, "info", message, data=data)

    db.update_project(project_id, status="running", error=None)
    try:
        result = research(
            root / "task.md",
            seconds=config["time_budget_seconds"],
            max_experiments=config["max_experiments"],
            trial_seconds=config["trial_timeout_seconds"],
            threads=config["threads"],
            offline=config["offline"],
            max_llm_calls=config["max_llm_calls"],
            max_llm_tokens=config["max_llm_tokens"],
            emit=emit,
            check_cancelled=check_cancelled,
        )
        best = result.get("best") or {}
        db.update_project(
            project_id,
            status="completed",
            task_type=result["profile"]["task_type"],
            target_column=result["profile"]["target"],
            primary_metric=result["profile"]["metric"],
            best_model_type="dummy"
            if best.get("dummy")
            else (best.get("plan") or {}).get("algorithm", "emergency_constant"),
            best_metric_value=best.get("score"),
            stages_json=[
                {"name": name, "status": "completed", "started_at": None, "finished_at": None}
                for name in STAGES
            ],
        )
    except RunCancelled:
        db.update_project(project_id, status="cancelled", error=None)
    except Exception:
        import logging

        logging.exception("Competition run failed: %s", project_id)
        db.update_project(
            project_id,
            status="failed",
            error="AutoResearch failed. Review input materials and provider settings. Any saved prediction checkpoint remains available.",
        )


def report(project):
    path = Path(project["dataset_path"]).parent / "research.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
