import time
from typing import Any, Optional

import pandas as pd

from .. import db


class AgentContext:
    """Shared state passed through the agent pipeline."""

    def __init__(self, project_id: str, run_config: Optional[dict] = None, run_id: str = None):
        self.project_id = project_id
        self.run_config = run_config or {}
        self.started_at = time.time()
        self.run_id = run_id

    def check_cancelled(self):
        if self.run_id:
            from ..models import AgentRun

            with db.SessionLocal() as s:
                run = s.get(AgentRun, self.run_id)
                if not run or run.cancel_requested:
                    raise RunCancelled()
        if self.time_left() <= 0:
            raise TimeoutError("Run time budget reached")

    def emit(self, agent: str, stage: str, message: str, level: str = "info", data: Any = None) -> None:
        self.check_cancelled()
        event_type = "warning" if level == "warning" else "agent_message"
        if agent == "Supervisor" and message.startswith("Run started"):
            event_type = "run_started"
        elif agent == "Experiment":
            event_type = (
                "experiment_started"
                if message.startswith("Training")
                else "experiment_completed"
                if level == "success"
                else event_type
            )
        elif stage == "improve" and agent == "Supervisor":
            event_type = (
                "improvement_completed"
                if isinstance(data, dict) and "decision" in data
                else "improvement_started"
            )
        db.add_event(
            self.project_id,
            agent=agent,
            stage=stage,
            level=level,
            message=message,
            data=data,
            event_type=event_type,
        )

    @property
    def project(self) -> dict:
        p = db.get_project(self.project_id)
        if p is None:
            raise RuntimeError(f"Project {self.project_id} not found")
        return p

    def load_df(self) -> pd.DataFrame:
        path = self.project.get("dataset_path")
        if not path:
            raise RuntimeError("Project has no dataset attached")
        return pd.read_csv(path)

    @property
    def profile(self) -> Optional[dict]:
        return self.project.get("profile_json")

    @property
    def task(self) -> Optional[dict]:
        return self.project.get("task_json")

    def time_left(self) -> float:
        budget = float(self.run_config.get("time_budget_seconds", 180))
        return budget - (time.time() - self.started_at)

    def experiments_used(self) -> int:
        return len(db.list_experiments(self.project_id))

    def experiment_slots_left(self) -> int:
        return int(self.run_config.get("max_experiments", 4)) - self.experiments_used()


class RunCancelled(Exception):
    pass
