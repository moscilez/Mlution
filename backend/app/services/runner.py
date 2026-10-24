"""Durable RQ jobs, with a single-process development fallback."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from redis import Redis
from rq import Queue
from .. import db, models as m
from ..agents.base import AgentContext
from ..agents.supervisor import SupervisorAgent
from ..config import STAGES
from ..settings import get_settings

executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mlution")


def is_running(project_id):
    with db.SessionLocal() as s:
        return (
            s.scalar(
                select(m.AgentRun.id).where(
                    m.AgentRun.project_id == project_id, m.AgentRun.status.in_(["queued", "running"])
                )
            )
            is not None
        )


def start_run(project_id, run_config):
    with db.SessionLocal.begin() as s:
        p = s.scalar(select(m.Project).where(m.Project.id == project_id).with_for_update())
        # Serialize all launches by the same owner, including different projects.
        s.scalar(select(m.User).where(m.User.id == p.owner_id).with_for_update())
        if s.scalar(
            select(m.AgentRun.id)
            .join(m.Project)
            .where(m.Project.owner_id == p.owner_id, m.AgentRun.status.in_(["queued", "running"]))
        ):
            raise RuntimeError("Only one active run per user is allowed")
        run = m.AgentRun(project_id=project_id, config_json=json.dumps(run_config))
        s.add(run)
        s.flush()
        rid = run.id
        p.status = "queued"
        p.error = None
        p.run_config_json = json.dumps(run_config)
        p.stages_json = json.dumps(
            [
                {"name": stage, "status": "pending", "started_at": None, "finished_at": None}
                for stage in STAGES
            ]
        )
    try:
        if get_settings().job_mode == "redis":
            Queue("mlution", connection=Redis.from_url(get_settings().redis_url)).enqueue(
                execute_run,
                rid,
                job_id=rid,
                job_timeout=run_config["time_budget_seconds"] + 30,
                on_failure=job_failed,
                result_ttl=3600,
                failure_ttl=86400,
            )
        else:
            executor.submit(execute_run, rid)
    except Exception:
        logging.exception("Cannot dispatch run %s", rid)
        mark_failed(rid, "Worker queue unavailable. Please retry.")
        raise RuntimeError("Worker queue unavailable. Please retry.") from None
    return rid


def mark_failed(rid, message):
    with db.SessionLocal.begin() as s:
        run = s.get(m.AgentRun, rid)
        if run and run.status in {"queued", "running"}:
            run.status = "cancelled" if run.cancel_requested else "failed"
            p = s.get(m.Project, run.project_id)
            if p:
                p.status = run.status
                p.error = None if run.cancel_requested else message


def job_failed(job, connection, exc_type, exc_value, traceback):
    mark_failed(job.id, "Run exceeded its time budget or worker stopped. Please retry.")


def execute_run(rid):
    token = db.run_context.set(rid)
    try:
        with db.SessionLocal.begin() as s:
            run = s.get(m.AgentRun, rid)
            if not run or run.status != "queued":
                return
            if run.cancel_requested:
                run.status = "cancelled"
                s.get(m.Project, run.project_id).status = "cancelled"
                return
            run.status = "running"
            pid, config = run.project_id, json.loads(run.config_json)
        if config.get("mode") == "competition":
            from ..competition.web import execute

            execute(pid, config, rid)
        else:
            SupervisorAgent(AgentContext(pid, config, rid)).run()
        with db.SessionLocal.begin() as s:
            run = s.get(m.AgentRun, rid)
            p = s.get(m.Project, pid)
            if run.cancel_requested:
                p.status = "cancelled"
                p.error = None
            run.status = p.status
        db.add_event(
            pid, "Supervisor", "finalize", "info", f"Run {run.status}.", event_type=f"run_{run.status}"
        )
    except Exception:
        logging.exception("Runner failure %s", rid)
        mark_failed(rid, "Run failed. Review dataset and retry.")
    finally:
        db.run_context.reset(token)


def cancel_run(pid, rid):
    with db.SessionLocal.begin() as s:
        run = s.get(m.AgentRun, rid)
        if not run or run.project_id != pid:
            return None
        if run.status in {"queued", "running"}:
            run.cancel_requested = True
            if run.status == "queued":
                run.status = "cancelled"
                s.get(m.Project, pid).status = "cancelled"
        result = db.view(run)
    token = db.run_context.set(rid)
    try:
        db.add_event(
            pid,
            "Supervisor",
            "finalize",
            "info",
            "Cancellation requested.",
            event_type="run_cancelled" if result["status"] == "cancelled" else "agent_message",
        )
    finally:
        db.run_context.reset(token)
    return result
