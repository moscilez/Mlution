import logging
from typing import Optional

import pandas as pd

from .. import db
from ..config import LOWER_IS_BETTER, STAGES
from .base import AgentContext, RunCancelled
from .critic import CriticAgent
from .data_analyst import DataAnalystAgent
from .experiment import ExperimentAgent
from .feature_engineering import FeatureEngineeringAgent
from .model_builder import ModelBuilderAgent
from .report import ReportAgent
from .task_planner import TaskPlannerAgent

AGENT = "Supervisor"


def _set_stage(project_id: str, name: str, status: str) -> None:
    rid = db.run_context.get()
    if rid and status == "running":
        from ..models import AgentRun

        with db.SessionLocal() as session:
            run = session.get(AgentRun, rid)
            if run.cancel_requested:
                raise RunCancelled()
    p = db.get_project(project_id)
    stages = (p or {}).get("stages_json") or [
        {"name": s, "status": "pending", "started_at": None, "finished_at": None} for s in STAGES
    ]
    now = db.utcnow()
    for s in stages:
        if s["name"] == name:
            s["status"] = status
            if status == "running":
                s["started_at"] = now
            if status in ("completed", "failed", "skipped"):
                s["finished_at"] = now
                if s.get("started_at"):
                    from datetime import datetime

                    s["duration_seconds"] = round(
                        (
                            datetime.fromisoformat(now) - datetime.fromisoformat(s["started_at"])
                        ).total_seconds(),
                        3,
                    )
    db.update_project(project_id, stages_json=stages, stage=name)
    if status == "running":
        db.add_event(project_id, "Supervisor", name, "info", f"Starting {name}.", event_type="stage_started")


class SupervisorAgent:
    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self) -> None:
        ctx = self.ctx
        pid = ctx.project_id
        db.update_project(pid, status="running", error=None)
        ctx.emit(
            AGENT,
            "analyze",
            "Run started. Mlution agent is taking over.",
            "info",
            {"run_config": ctx.run_config},
        )
        try:
            # ANALYZE
            _set_stage(pid, "analyze", "running")
            profile = DataAnalystAgent(ctx).run()
            _set_stage(pid, "analyze", "completed")

            # PLAN
            _set_stage(pid, "plan", "running")
            df = ctx.load_df().drop_duplicates()
            task = TaskPlannerAgent(ctx).run(df, profile)
            fe = FeatureEngineeringAgent(ctx)
            fe_plan = fe.plan(df, task["target_column"], profile)
            preprocessor = fe.build_preprocessor(fe_plan["numeric"], fe_plan["categorical"])
            X = df[fe_plan["features"]].copy()
            for column in fe_plan["numeric"]:
                X[column] = pd.to_numeric(X[column], errors="coerce").astype(float)
            y = df[task["target_column"]]
            valid = y.notna()
            X, y = X.loc[valid], y.loc[valid]
            if task["task_type"] != "regression":
                from sklearn.preprocessing import LabelEncoder

                encoder = LabelEncoder()
                y = pd.Series(encoder.fit_transform(y.astype(str)), index=y.index)
                ctx.class_labels = [str(v) for v in encoder.classes_]
                if len(ctx.class_labels) < 2 or y.value_counts().min() < 2:
                    raise ValueError("Classification needs at least two classes and two rows per class")
            _set_stage(pid, "plan", "completed")

            # BUILD BASELINE
            _set_stage(pid, "build_baseline", "running")
            zoo = ModelBuilderAgent(ctx).run(task["task_type"])
            exp_agent = ExperimentAgent(ctx)
            experiments: list[dict] = []
            max_exp = int(ctx.run_config.get("max_experiments", 4))
            baseline_slots = max_exp if max_exp <= 2 else max_exp - 1
            for spec in zoo[:baseline_slots]:
                if ctx.time_left() <= 20:
                    ctx.emit(
                        AGENT,
                        "build_baseline",
                        "Time budget reached — stopping baseline scheduling.",
                        "warning",
                    )
                    break
                experiments.append(
                    exp_agent.run(
                        name=spec["name"],
                        model_type=spec["model_type"],
                        estimator=spec["factory"](),
                        preprocessor=preprocessor,
                        X=X,
                        y=y,
                        task_type=task["task_type"],
                        primary_metric=task["primary_metric"],
                        stage="baseline",
                        hyperparameters=spec["hyperparameters"],
                    )
                )
            _set_stage(pid, "build_baseline", "completed")

            # EVALUATE
            _set_stage(pid, "evaluate", "running")
            experiments = db.list_experiments(pid)
            completed = [e for e in experiments if e["status"] == "completed"]
            if not completed:
                raise RuntimeError("All experiments failed — nothing to evaluate.")
            for e in completed:
                ctx.emit(
                    AGENT,
                    "evaluate",
                    f"{e['name']}: validation {task['primary_metric']} = {e['primary_metric_value']:.4f}",
                    data={"experiment_id": e["id"]},
                )
            _set_stage(pid, "evaluate", "completed")

            # CRITIQUE
            _set_stage(pid, "critique", "running")
            critic = CriticAgent(ctx)
            critic_warnings, proposal = critic.run(task, experiments, profile)
            _set_stage(pid, "critique", "completed")

            # IMPROVE
            _set_stage(pid, "improve", "running")
            improvements: list[dict] = []
            if proposal and ctx.experiment_slots_left() > 0 and ctx.time_left() > 20:
                step = self._run_improvement(proposal, task, profile, exp_agent, preprocessor, X, y)
                if step:
                    improvements.append(step)
            else:
                ctx.emit(AGENT, "improve", "No improvement proposal — skipping.")
            _set_stage(pid, "improve", "completed" if proposal else "skipped")

            # FINALIZE
            _set_stage(pid, "finalize", "running")
            experiments = db.list_experiments(pid)
            completed = [e for e in experiments if e["status"] == "completed"]
            higher_better = task["primary_metric"] not in LOWER_IS_BETTER
            best = max(
                completed,
                key=lambda e: e["primary_metric_value"] if higher_better else -e["primary_metric_value"],
            )
            ReportAgent(ctx).run(task, profile, experiments, improvements, critic_warnings)
            db.update_project(
                pid,
                status="completed",
                best_experiment_id=best["id"],
                best_metric_value=best["primary_metric_value"],
                best_model_type=best["model_type"],
            )
            _set_stage(pid, "finalize", "completed")
            ctx.emit(
                AGENT,
                "finalize",
                f"Done. Best model: {best['name']} ({task['primary_metric']} = {best['primary_metric_value']:.4f}).",
                "success",
                {"best_experiment_id": best["id"]},
            )
        except RunCancelled:
            db.update_project(pid, status="cancelled", error=None)
        except Exception:
            logging.exception("Pipeline failed: %s", pid)
            current = (db.get_project(pid) or {}).get("stage") or "analyze"
            _set_stage(pid, current, "failed")
            db.update_project(
                pid,
                status="failed",
                error="Training failed. Check the target, class counts and dataset quality, then retry.",
            )
            db.add_event(
                pid,
                AGENT,
                current,
                "error",
                "Training failed. Check dataset quality and retry.",
                event_type="run_failed",
            )

    # ------------------------------------------------------------------

    def _run_improvement(
        self,
        proposal: dict,
        task: dict,
        profile: dict,
        exp_agent: ExperimentAgent,
        preprocessor,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> Optional[dict]:
        ctx = self.ctx
        experiments = db.list_experiments(ctx.project_id)
        base = next((e for e in experiments if e["id"] == proposal["base_experiment_id"]), None)
        if base is None:
            return None
        primary = task["primary_metric"]
        higher_better = primary not in LOWER_IS_BETTER

        estimator, fit_params, tune, balance, action_detail = self._improvement_variant(
            proposal["kind"], base["model_type"], task["task_type"]
        )
        if estimator is None:
            ctx.emit(
                AGENT, "improve", f"No improvement variant available for {base['model_type']} — skipping."
            )
            return None

        ctx.emit(AGENT, "improve", f"Applying: {proposal['action']}")
        result = exp_agent.run(
            name=f"{base['name']} (improved)",
            model_type=base["model_type"],
            estimator=estimator,
            preprocessor=preprocessor,
            X=X,
            y=y,
            task_type=task["task_type"],
            primary_metric=primary,
            stage="improvement",
            hyperparameters={
                "base": base["model_type"],
                **(base.get("hyperparameters") or {}),
                "strategy": proposal["kind"],
            },
            fit_params=fit_params,
            tune=tune,
            balance=balance,
        )
        if result["status"] != "completed":
            return None

        before_v = base["primary_metric_value"]
        after_v = result["primary_metric_value"]
        improved = (after_v > before_v) if higher_better else (after_v < before_v)
        step = {
            "hypothesis": proposal["hypothesis"],
            "reason": proposal["reason"],
            "action": proposal["action"] + (f" — {action_detail}" if action_detail else ""),
            "before": {primary: before_v},
            "after": {primary: after_v},
            "decision": "accept_improvement" if improved else "reject_improvement",
            "details": f"{base['name']}: {primary} {before_v:.4f} → {after_v:.4f}",
        }
        ctx.emit(
            AGENT,
            "improve",
            f"Improvement {'accepted' if improved else 'rejected'}: {primary} {before_v:.4f} → {after_v:.4f}.",
            "success" if improved else "warning",
            step,
        )
        return step

    def _improvement_variant(self, kind: str, model_type: str, task_type: str):
        """Return (estimator, fit_params, tune_threshold, balance_sample_weight, action_detail)."""
        from sklearn.ensemble import (
            HistGradientBoostingClassifier,
            HistGradientBoostingRegressor,
            RandomForestClassifier,
            RandomForestRegressor,
        )
        from sklearn.linear_model import LogisticRegression, Ridge

        if kind == "imbalance":
            if model_type == "logistic_regression":
                return (
                    LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced"),
                    None,
                    True,
                    False,
                    "class_weight='balanced'",
                )
            if model_type == "random_forest":
                return (
                    RandomForestClassifier(
                        n_estimators=300, random_state=42, n_jobs=-1, class_weight="balanced"
                    ),
                    None,
                    True,
                    False,
                    "class_weight='balanced'",
                )
            if model_type == "hist_gradient_boosting":
                return (
                    HistGradientBoostingClassifier(random_state=42),
                    None,
                    True,
                    True,
                    "balanced sample weights",
                )
            if model_type == "catboost":
                try:
                    from catboost import CatBoostClassifier

                    return (
                        CatBoostClassifier(
                            verbose=0, random_state=42, iterations=400, auto_class_weights="Balanced"
                        ),
                        None,
                        True,
                        False,
                        "auto_class_weights='Balanced'",
                    )
                except Exception:
                    return None, None, False, False, None
            return None, None, False, False, None

        if kind == "threshold":
            from .model_builder import build_model_zoo

            zoo = {m["model_type"]: m for m in build_model_zoo(task_type)}
            spec = zoo.get(model_type)
            if spec is None:
                return None, None, False, False, None
            return spec["factory"](), None, True, False, "validation-tuned decision threshold"

        # hpo: tuned variant of the best family
        if model_type == "random_forest":
            cls = RandomForestClassifier if task_type != "regression" else RandomForestRegressor
            return (
                cls(n_estimators=500, max_depth=12, min_samples_leaf=2, random_state=42, n_jobs=-1),
                None,
                False,
                False,
                "n_estimators=500, max_depth=12",
            )
        if model_type == "hist_gradient_boosting":
            cls = (
                HistGradientBoostingClassifier if task_type != "regression" else HistGradientBoostingRegressor
            )
            return (
                cls(learning_rate=0.05, max_iter=300, random_state=42),
                None,
                False,
                False,
                "learning_rate=0.05, max_iter=300",
            )
        if model_type in ("logistic_regression", "linear_regression"):
            if task_type == "regression":
                return Ridge(alpha=1.0, random_state=42), None, False, False, "Ridge(alpha=1.0)"
            return LogisticRegression(max_iter=2000, C=0.5, random_state=42), None, False, False, "C=0.5"
        if model_type == "catboost":
            try:
                from catboost import CatBoostClassifier, CatBoostRegressor

                cls = CatBoostClassifier if task_type != "regression" else CatBoostRegressor
                return (
                    cls(verbose=0, random_state=42, iterations=600, depth=6, learning_rate=0.05),
                    None,
                    False,
                    False,
                    "iterations=600, depth=6",
                )
            except Exception:
                return None, None, False, False, None
        return None, None, False, False, None
