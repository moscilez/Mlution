import pandas as pd

from ..schemas import MLTask
from .base import AgentContext

ALLOWED_METRICS = {
    "binary_classification": ["f1", "recall", "precision", "roc_auc", "accuracy"],
    "multiclass_classification": ["f1_macro", "f1_weighted", "accuracy"],
    "regression": ["rmse", "mae", "r2"],
}
DEFAULT_METRIC = {
    "binary_classification": "f1",
    "multiclass_classification": "f1_macro",
    "regression": "rmse",
}
RECALL_KEYWORDS = ["recall", "churn", "fraud", "churners", "уход", "отток", "полнот"]


def infer_task_type(df: pd.DataFrame, target: str) -> str:
    s = df[target]
    n_unique = s.nunique(dropna=True)
    if pd.api.types.is_numeric_dtype(s) and n_unique > 20:
        return "regression"
    if n_unique <= 2:
        return "binary_classification"
    if n_unique <= 20:
        return "multiclass_classification"
    if pd.api.types.is_numeric_dtype(s):
        return "regression"
    raise ValueError(
        f"Target column '{target}' has {n_unique} unique values and is not numeric — cannot infer a supported task type."
    )


class TaskPlannerAgent:
    name = "TaskPlanner"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self, df: pd.DataFrame, profile: dict) -> dict:
        ctx = self.ctx
        rc = ctx.run_config
        target = rc.get("target_column") or profile.get("target_column")
        if not target:
            raise ValueError("No target column. Select one explicitly when starting the run.")
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found in dataset.")

        task_type = infer_task_type(df, target)
        allowed = ALLOWED_METRICS[task_type]
        primary = rc.get("primary_metric")
        business_priority = rc.get("business_priority")

        if primary not in allowed:
            primary = None
        if primary is None and business_priority and task_type == "binary_classification":
            if any(k in business_priority.lower() for k in RECALL_KEYWORDS):
                primary = "recall"
        if primary is None:
            primary = DEFAULT_METRIC[task_type]

        secondary = [m for m in allowed if m != primary][:3]
        rationale = (
            f"Target '{target}' has {int(df[target].nunique(dropna=True))} unique values "
            f"({'numeric' if pd.api.types.is_numeric_dtype(df[target]) else 'categorical'}) → {task_type}. "
            f"Primary metric '{primary}'"
            + (
                f" chosen from business priority '{business_priority}'."
                if business_priority and primary in business_priority.lower()
                else "."
            )
        )

        task = MLTask(
            task_type=task_type,
            target_column=target,
            primary_metric=primary,
            secondary_metrics=secondary,
            business_priority=business_priority,
            rationale=rationale,
        )
        from .. import db as _db

        _db.update_project(
            ctx.project_id,
            task_json=task.model_dump(),
            task_type=task_type,
            target_column=target,
            primary_metric=primary,
        )
        ctx.emit(
            self.name,
            "plan",
            f"Task plan: {task_type} on '{target}', primary metric: {primary}.",
            "success",
            task.model_dump(),
        )
        return task.model_dump()
