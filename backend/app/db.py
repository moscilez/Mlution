import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .config import DB_PATH

_write_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'created',
    stage TEXT,
    task_type TEXT,
    target_column TEXT,
    primary_metric TEXT,
    best_experiment_id TEXT,
    best_metric_value REAL,
    best_model_type TEXT,
    dataset_name TEXT,
    dataset_path TEXT,
    error TEXT,
    profile_json TEXT,
    task_json TEXT,
    report_json TEXT,
    business_priority TEXT,
    run_config_json TEXT,
    stages_json TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT,
    model_type TEXT,
    status TEXT DEFAULT 'pending',
    stage TEXT DEFAULT 'baseline',
    hyperparameters_json TEXT DEFAULT '{}',
    metrics_json TEXT DEFAULT '[]',
    primary_metric_name TEXT,
    primary_metric_value REAL,
    train_seconds REAL,
    error TEXT,
    feature_importance_json TEXT DEFAULT '[]',
    confusion_matrix_json TEXT,
    artifact_path TEXT,
    threshold REAL,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_experiments_project ON experiments(project_id);
CREATE TABLE IF NOT EXISTS agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    ts TEXT,
    agent TEXT,
    stage TEXT,
    level TEXT DEFAULT 'info',
    message TEXT,
    data_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_project ON agent_events(project_id, id);
"""

JSON_PROJECT_FIELDS = {"profile_json", "task_json", "report_json", "run_config_json", "stages_json"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _run(sql: str, params: tuple = ()) -> int:
    with _write_lock:
        with connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid or 0


# ---------------- projects ----------------

def create_project(name: str, description: str) -> dict:
    pid = new_id()
    now = utcnow()
    _run(
        "INSERT INTO projects (id, name, description, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        (pid, name, description, "created", now, now),
    )
    return get_project(pid)


def get_project(pid: str) -> Optional[dict]:
    rows = _rows("SELECT * FROM projects WHERE id = ?", (pid,))
    if not rows:
        return None
    row = rows[0]
    for f in JSON_PROJECT_FIELDS:
        if row.get(f):
            try:
                row[f] = json.loads(row[f])
            except Exception:
                pass
    return row


def list_projects() -> list[dict]:
    rows = _rows("SELECT * FROM projects ORDER BY created_at DESC")
    for row in rows:
        for f in JSON_PROJECT_FIELDS:
            if row.get(f):
                try:
                    row[f] = json.loads(row[f])
                except Exception:
                    pass
    return rows


def update_project(pid: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = utcnow()
    sets, params = [], []
    for k, v in fields.items():
        if k in JSON_PROJECT_FIELDS and not isinstance(v, str) and v is not None:
            v = json.dumps(v)
        sets.append(f"{k} = ?")
        params.append(v)
    params.append(pid)
    _run(f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", tuple(params))


# ---------------- experiments ----------------

def create_experiment(pid: str, name: str, model_type: str, stage: str, hyperparameters: dict) -> str:
    eid = new_id()
    _run(
        "INSERT INTO experiments (id, project_id, name, model_type, status, stage, hyperparameters_json, created_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (eid, pid, name, model_type, "pending", stage, json.dumps(hyperparameters), utcnow()),
    )
    return eid


def update_experiment(eid: str, **fields: Any) -> None:
    json_fields = {"hyperparameters": "hyperparameters_json", "metrics": "metrics_json",
                   "feature_importance": "feature_importance_json", "confusion_matrix": "confusion_matrix_json"}
    sets, params = [], []
    for k, v in fields.items():
        col = json_fields.get(k, k)
        if k in json_fields and not isinstance(v, str) and v is not None:
            v = json.dumps(v)
        sets.append(f"{col} = ?")
        params.append(v)
    if not sets:
        return
    params.append(eid)
    _run(f"UPDATE experiments SET {', '.join(sets)} WHERE id = ?", tuple(params))


def list_experiments(pid: str) -> list[dict]:
    rows = _rows("SELECT * FROM experiments WHERE project_id = ? ORDER BY created_at ASC", (pid,))
    for r in rows:
        for src, dst in [("hyperparameters_json", "hyperparameters"), ("metrics_json", "metrics"),
                         ("feature_importance_json", "feature_importance"), ("confusion_matrix_json", "confusion_matrix")]:
            raw = r.pop(src, None)
            try:
                r[dst] = json.loads(raw) if raw else ([] if dst != "confusion_matrix" and dst != "hyperparameters" else ({} if dst == "hyperparameters" else None))
            except Exception:
                r[dst] = [] if dst in ("metrics", "feature_importance") else None
        if r.get("hyperparameters") is None:
            r["hyperparameters"] = {}
    return rows


# ---------------- agent events ----------------

def add_event(pid: str, agent: str, stage: str, level: str, message: str, data: Any = None) -> int:
    return _run(
        "INSERT INTO agent_events (project_id, ts, agent, stage, level, message, data_json) VALUES (?,?,?,?,?,?,?)",
        (pid, utcnow(), agent, stage, level, message, json.dumps(data) if data is not None else None),
    )


def list_events(pid: str, after_id: int = 0, limit: int = 500) -> list[dict]:
    rows = _rows(
        "SELECT * FROM agent_events WHERE project_id = ? AND id > ? ORDER BY id ASC LIMIT ?",
        (pid, after_id, limit),
    )
    for r in rows:
        raw = r.pop("data_json", None)
        try:
            r["data"] = json.loads(raw) if raw else None
        except Exception:
            r["data"] = None
    return rows
