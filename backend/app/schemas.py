from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from .settings import get_settings

TaskType = Literal["binary_classification", "multiclass_classification", "regression"]
ProjectStatus = Literal["created", "queued", "running", "completed", "failed", "cancelled"]
Level = Literal["info", "warning", "critical"]


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    kind: Literal["numeric", "categorical", "id_like"]
    n_missing: int
    missing_pct: float
    n_unique: int
    examples: list[str] = Field(default_factory=list)


class Warning(BaseModel):
    level: Level
    code: str
    message: str


class LeakageCandidate(BaseModel):
    column: str
    reason: str


class DatasetProfile(BaseModel):
    quality_score: Optional[float] = None
    n_rows: int
    n_columns: int
    columns: list[ColumnProfile]
    n_duplicates: int
    duplicate_pct: float
    numeric_columns: list[str]
    categorical_columns: list[str]
    id_columns: list[str]
    leakage_candidates: list[LeakageCandidate]
    target_column: Optional[str] = None
    task_hint: Optional[str] = None
    class_balance: Optional[dict[str, int]] = None
    imbalance_warning: bool = False
    warnings: list[Warning] = Field(default_factory=list)


class MLTask(BaseModel):
    task_type: str
    target_column: str
    primary_metric: str
    secondary_metrics: list[str]
    business_priority: Optional[str] = None
    rationale: str


class MetricResult(BaseModel):
    name: str
    value: float
    split: Literal["train", "validation"]


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ConfusionMatrix(BaseModel):
    labels: list[str]
    matrix: list[list[int]]
    support: list[int] = Field(default_factory=list)


class Experiment(BaseModel):
    id: str
    project_id: str
    name: str
    model_type: str
    status: Literal["pending", "running", "completed", "failed"]
    stage: Literal["baseline", "improvement"]
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    metrics: list[MetricResult] = Field(default_factory=list)
    primary_metric_name: Optional[str] = None
    primary_metric_value: Optional[float] = None
    train_seconds: Optional[float] = None
    error: Optional[str] = None
    feature_importance: list[FeatureImportance] = Field(default_factory=list)
    confusion_matrix: Optional[ConfusionMatrix] = None
    created_at: Optional[str] = None


class AgentEvent(BaseModel):
    event_id: Optional[str] = None
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    type: str = "agent_message"
    created_at: Optional[str] = None
    progress: float = 0
    id: int
    project_id: str
    ts: str
    agent: str
    stage: str
    level: Literal["info", "success", "warning", "error"]
    message: str
    data: Optional[dict[str, Any]] = None


class ImprovementStep(BaseModel):
    hypothesis: str
    reason: str
    action: str
    before: dict[str, float]
    after: dict[str, float]
    decision: Literal["accept_improvement", "reject_improvement"]
    details: Optional[str] = None


class Project(BaseModel):
    mode: Literal["workspace", "competition"] = "workspace"
    id: str
    name: str
    description: str = ""
    status: ProjectStatus
    stage: Optional[str] = None
    task_type: Optional[str] = None
    target_column: Optional[str] = None
    primary_metric: Optional[str] = None
    best_experiment_id: Optional[str] = None
    best_metric_value: Optional[float] = None
    best_model_type: Optional[str] = None
    dataset_name: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PredictionRequest(BaseModel):
    features: dict[str, Any]


class PredictionResponse(BaseModel):
    prediction: Any
    probability: Optional[float] = None
    probabilities: Optional[dict[str, float]] = None
    model_type: str
    explanation: str
    top_factors: list[FeatureImportance] = Field(default_factory=list)


class LeaderboardEntry(BaseModel):
    experiment_id: str
    model_type: str
    stage: str
    primary_metric_value: float


class FinalReport(BaseModel):
    summary: str
    task: MLTask
    best_experiment_id: str
    best_model_type: str
    metrics: list[MetricResult]
    leaderboard: list[LeaderboardEntry]
    improvements: list[ImprovementStep]
    warnings: list[Warning]
    limitations: list[str]
    next_steps: list[str]
    explanation: str
    usage_code: str
    generated_at: str


class StageInfo(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None


class RunStatus(BaseModel):
    project_id: str
    status: str
    stage: Optional[str] = None
    stages: list[StageInfo]
    progress: float
    error: Optional[str] = None


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    use_demo_dataset: bool = False
    target_column: Optional[str] = None
    primary_metric: Optional[str] = None


class RunRequest(BaseModel):
    target_column: Optional[str] = None
    primary_metric: Optional[str] = None
    business_priority: Optional[str] = None
    time_budget_seconds: int = Field(
        default_factory=lambda: get_settings().default_time_budget_seconds, ge=30, le=600
    )
    max_experiments: int = Field(default=4, ge=1, le=6)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    ts: str
