import time
from typing import Any, Optional

import pandas as pd

from .. import db


class AgentContext:
    """Shared state passed through the agent pipeline."""

    def __init__(self, project_id: str, run_config: Optional[dict] = None):
        self.project_id = project_id
        self.run_config = run_config or {}
        self.started_at = time.time()

    def emit(self, agent: str, stage: str, message: str, level: str = "info", data: Any = None) -> None:
        db.add_event(self.project_id, agent=agent, stage=stage, level=level, message=message, data=data)

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
