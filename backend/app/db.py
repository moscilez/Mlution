"""SQLAlchemy repository; dictionaries preserve existing agent contracts."""

import json
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar
from sqlalchemy import create_engine, select, update, delete, text, event
from sqlalchemy.orm import sessionmaker
from .settings import get_settings
from . import models as m

run_context = ContextVar("run_id", default=None)
engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")


JSON_PROJECT_FIELDS = {"profile_json", "task_json", "report_json", "run_config_json", "stages_json"}


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return str(uuid.uuid4())


def init_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def view(obj):
    row = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    return {k: v.isoformat() if isinstance(v, datetime) else v for k, v in row.items()}


def project_view(obj):
    row = view(obj)
    for f in JSON_PROJECT_FIELDS:
        if row.get(f):
            row[f] = json.loads(row[f])
    return row


def create_project(name, description, owner_id):
    with SessionLocal.begin() as s:
        p = m.Project(name=name, description=description, owner_id=owner_id)
        s.add(p)
        s.flush()
        return project_view(p)


def get_project(pid):
    with SessionLocal() as s:
        p = s.get(m.Project, pid)
        return project_view(p) if p else None


def list_projects(owner_id, offset=0, limit=50):
    with SessionLocal() as s:
        return [
            project_view(p)
            for p in s.scalars(
                select(m.Project)
                .where(m.Project.owner_id == owner_id)
                .order_by(m.Project.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ]


def update_project(pid, **fields):
    if set(fields) - set(m.Project.__table__.columns.keys()):
        raise ValueError("Unknown project field")
    for k in JSON_PROJECT_FIELDS & fields.keys():
        if fields[k] is not None and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k], allow_nan=False)
    with SessionLocal.begin() as s:
        s.execute(update(m.Project).where(m.Project.id == pid).values(**fields))
        if fields.get("dataset_path") and fields.get("profile_json"):
            dataset = m.Dataset(
                project_id=pid, name=fields.get("dataset_name", "dataset.csv"), path=fields["dataset_path"]
            )
            s.add(dataset)
            s.flush()
            s.add(m.DatasetProfile(dataset_id=dataset.id, profile_json=fields["profile_json"]))


def create_experiment(pid, name, model_type, stage, hyperparameters):
    with SessionLocal.begin() as s:
        e = m.Experiment(
            project_id=pid,
            run_id=run_context.get(),
            name=name,
            model_type=model_type,
            stage=stage,
            hyperparameters_json=json.dumps(hyperparameters),
        )
        s.add(e)
        s.flush()
        return e.id


def update_experiment(eid, **fields):
    mapping = {
        "hyperparameters": "hyperparameters_json",
        "metrics": "metrics_json",
        "feature_importance": "feature_importance_json",
        "confusion_matrix": "confusion_matrix_json",
    }
    values = {
        mapping.get(k, k): json.dumps(v, allow_nan=False) if k in mapping and v is not None else v
        for k, v in fields.items()
    }
    if set(values) - set(m.Experiment.__table__.columns.keys()):
        raise ValueError("Unknown experiment field")
    with SessionLocal.begin() as s:
        s.execute(update(m.Experiment).where(m.Experiment.id == eid).values(**values))
        if values.get("artifact_path") and values.get("artifact_sha256"):
            s.add(
                m.ModelArtifact(
                    experiment_id=eid, path=values["artifact_path"], sha256=values["artifact_sha256"]
                )
            )


def list_experiments(pid, run_id=None):
    current = run_id or run_context.get()
    stmt = select(m.Experiment).where(m.Experiment.project_id == pid)
    if current:
        stmt = stmt.where(m.Experiment.run_id == current)
    with SessionLocal() as s:
        rows = [view(e) for e in s.scalars(stmt.order_by(m.Experiment.created_at))]
    for r in rows:
        for src, dst, default in [
            ("hyperparameters_json", "hyperparameters", {}),
            ("metrics_json", "metrics", []),
            ("feature_importance_json", "feature_importance", []),
            ("confusion_matrix_json", "confusion_matrix", None),
        ]:
            raw = r.pop(src)
            r[dst] = json.loads(raw) if raw else default
    return rows


def add_event(pid, agent, stage, level, message, data=None, event_type="agent_message"):
    rid = run_context.get()
    with SessionLocal.begin() as s:
        e = m.AgentEvent(
            project_id=pid,
            run_id=rid,
            agent=agent,
            stage=stage,
            level=level,
            message=message[:4000],
            type=event_type,
            data_json=json.dumps(data) if data is not None else None,
        )
        s.add(e)
        if rid and isinstance(data, dict) and "hypothesis" in data and "decision" in data:
            s.add(m.ImprovementStep(run_id=rid, details_json=json.dumps(data)))
        s.flush()
        return e.id


def list_events(pid, after_id=0, limit=500, run_id=None):
    stmt = select(m.AgentEvent).where(m.AgentEvent.project_id == pid, m.AgentEvent.id > after_id)
    if run_id:
        stmt = stmt.where(m.AgentEvent.run_id == run_id)
    with SessionLocal() as s:
        rows = [view(e) for e in s.scalars(stmt.order_by(m.AgentEvent.id).limit(limit))]
    for r in rows:
        r["data"] = json.loads(r.pop("data_json") or "null")
        from .config import STAGES

        progress = (STAGES.index(r["stage"]) / len(STAGES)) if r["stage"] in STAGES else 0
        if r["type"] == "run_completed":
            progress = 1
        r.update(
            event_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"mlution:{pid}:{r['id']}")),
            correlation_id=r["run_id"],
            created_at=r["ts"],
            progress=round(progress, 3),
        )
    return rows


def audit(user_id, action, resource_id=None):
    with SessionLocal.begin() as s:
        s.add(m.AuditLog(user_id=user_id, action=action, resource_id=resource_id))


def delete_project(pid):
    with SessionLocal.begin() as s:
        s.execute(delete(m.Project).where(m.Project.id == pid))
