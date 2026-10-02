import threading

from .. import db
from ..agents.base import AgentContext
from ..agents.supervisor import SupervisorAgent
from ..config import STAGES

_running: dict[str, threading.Thread] = {}
_lock = threading.Lock()


def is_running(project_id: str) -> bool:
    with _lock:
        t = _running.get(project_id)
        return t is not None and t.is_alive()


def start_run(project_id: str, run_config: dict) -> None:
    with _lock:
        t = _running.get(project_id)
        if t is not None and t.is_alive():
            raise RuntimeError("Run already in progress for this project")
        db.update_project(
            project_id,
            run_config_json=run_config,
            stages_json=[{"name": s, "status": "pending", "started_at": None, "finished_at": None} for s in STAGES],
        )
        thread = threading.Thread(target=_run_safe, args=(project_id, run_config), daemon=True)
        _running[project_id] = thread
        thread.start()


def _run_safe(project_id: str, run_config: dict) -> None:
    try:
        SupervisorAgent(AgentContext(project_id, run_config)).run()
    except Exception as exc:  # last-resort guard; supervisor handles its own errors
        db.update_project(project_id, status="failed", error=str(exc)[:500])
        db.add_event(project_id, agent="Supervisor", stage="finalize", level="error",
                     message=f"Unexpected runner failure: {exc}")
    finally:
        with _lock:
            _running.pop(project_id, None)
