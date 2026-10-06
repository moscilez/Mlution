from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, Index
from sqlalchemy.orm import DeclarativeBase


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=uid)
    email = Column(String(254), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(16), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=uid)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, default="")
    status = Column(String(32), default="created")
    stage = Column(Text)
    task_type = Column(Text)
    target_column = Column(Text)
    primary_metric = Column(Text)
    best_experiment_id = Column(String(36))
    best_metric_value = Column(Float)
    best_model_type = Column(Text)
    dataset_name = Column(Text)
    dataset_path = Column(Text)
    error = Column(Text)
    profile_json = Column(Text)
    task_json = Column(Text)
    report_json = Column(Text)
    business_priority = Column(Text)
    run_config_json = Column(Text)
    stages_json = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(String(36), primary_key=True, default=uid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="queued", nullable=False)
    config_json = Column(Text, nullable=False)
    cancel_requested = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)
    __table_args__ = (
        Index(
            "one_active_run_per_project",
            "project_id",
            unique=True,
            postgresql_where=status.in_(["queued", "running"]),
            sqlite_where=status.in_(["queued", "running"]),
        ),
    )


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String(36), primary_key=True, default=uid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    name = Column(Text)
    model_type = Column(Text)
    status = Column(String(32), default="pending")
    stage = Column(Text, default="baseline")
    hyperparameters_json = Column(Text, default="{}")
    metrics_json = Column(Text, default="[]")
    primary_metric_name = Column(Text)
    primary_metric_value = Column(Float)
    train_seconds = Column(Float)
    error = Column(Text)
    feature_importance_json = Column(Text, default="[]")
    confusion_matrix_json = Column(Text)
    artifact_path = Column(Text)
    artifact_sha256 = Column(String(64))
    threshold = Column(Float)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class AgentEvent(Base):
    __tablename__ = "agent_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    ts = Column(DateTime(timezone=True), default=now, nullable=False)
    agent = Column(Text)
    stage = Column(Text)
    level = Column(Text, default="info")
    type = Column(String(40), default="agent_message")
    message = Column(Text)
    data_json = Column(Text)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    csrf_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(64), nullable=False)
    resource_id = Column(String(36))
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String(36), primary_key=True, default=uid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String(36), primary_key=True, default=uid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"
    id = Column(String(36), primary_key=True, default=uid)
    dataset_id = Column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    profile_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"
    id = Column(String(36), primary_key=True, default=uid)
    experiment_id = Column(
        String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=False)
    origin = Column(String(32), nullable=False, default="mlution-worker")
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class ImprovementStep(Base):
    __tablename__ = "improvement_steps"
    id = Column(String(36), primary_key=True, default=uid)
    run_id = Column(String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    details_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    id = Column(String(36), primary_key=True, default=uid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    experiment_id = Column(String(36), ForeignKey("experiments.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
