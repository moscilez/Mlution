import time
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix as sk_confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .. import db
from ..services.storage import experiment_artifact_path
from .base import AgentContext

try:
    from sklearn.metrics import root_mean_squared_error
except ImportError:  # pragma: no cover
    from sklearn.metrics import mean_squared_error

    def root_mean_squared_error(y_true, y_pred):
        return float(np.sqrt(mean_squared_error(y_true, y_pred)))


CLASSIFICATION = ("binary_classification", "multiclass_classification")


def compute_metrics(task_type: str, y_true, y_pred, y_proba_pos=None) -> list[dict]:
    out: list[dict] = []
    if task_type == "regression":
        out.append({"name": "rmse", "value": float(root_mean_squared_error(y_true, y_pred))})
        out.append({"name": "mae", "value": float(mean_absolute_error(y_true, y_pred))})
        out.append({"name": "r2", "value": float(r2_score(y_true, y_pred))})
        return out
    if task_type == "binary_classification":
        out.append({"name": "accuracy", "value": float(accuracy_score(y_true, y_pred))})
        out.append({"name": "precision", "value": float(precision_score(y_true, y_pred, zero_division=0))})
        out.append({"name": "recall", "value": float(recall_score(y_true, y_pred, zero_division=0))})
        out.append({"name": "f1", "value": float(f1_score(y_true, y_pred, zero_division=0))})
        if y_proba_pos is not None and len(np.unique(y_true)) == 2:
            out.append({"name": "roc_auc", "value": float(roc_auc_score(y_true, y_proba_pos))})
        return out
    out.append({"name": "accuracy", "value": float(accuracy_score(y_true, y_pred))})
    out.append({"name": "f1_macro", "value": float(f1_score(y_true, y_pred, average="macro", zero_division=0))})
    out.append({"name": "f1_weighted", "value": float(f1_score(y_true, y_pred, average="weighted", zero_division=0))})
    return out


def tune_threshold(y_true, proba_pos: np.ndarray, metric: str) -> tuple[float, float]:
    scorers = {
        "f1": lambda yt, yp: f1_score(yt, yp, zero_division=0),
        "recall": lambda yt, yp: recall_score(yt, yp, zero_division=0),
        "precision": lambda yt, yp: precision_score(yt, yp, zero_division=0),
        "accuracy": lambda yt, yp: accuracy_score(yt, yp),
    }
    scorer = scorers.get(metric)
    if scorer is None:
        return 0.5, 0.0
    best_thr, best_val = 0.5, -1.0
    for thr in np.arange(0.05, 0.96, 0.05):
        val = float(scorer(y_true, (proba_pos >= thr).astype(int)))
        if val > best_val:
            best_val, best_thr = val, float(thr)
    return best_thr, best_val


def _base_column(expanded_name: str, base_cols: list[str]) -> str:
    rest = expanded_name.split("__", 1)[-1]
    matches = [c for c in base_cols if rest == c or rest.startswith(c + "_")]
    return max(matches, key=len) if matches else rest


def _aggregate_importance(names: list[str], values: np.ndarray, base_cols: list[str]) -> list[dict]:
    agg: dict[str, float] = {}
    for n, v in zip(names, values):
        base = _base_column(str(n), base_cols)
        agg[base] = agg.get(base, 0.0) + float(abs(v))
    total = sum(agg.values())
    items = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:20]
    return [{"feature": k, "importance": round(v / total, 4) if total > 0 else 0.0} for k, v in items]


def feature_importance(pipe: Pipeline, X_val: pd.DataFrame, y_val, feature_names: list[str]) -> list[dict]:
    model = pipe.named_steps["model"]
    pre = pipe.named_steps["preprocess"]
    try:
        if hasattr(model, "feature_importances_"):
            values = np.asarray(model.feature_importances_, dtype=float)
            names = [str(n) for n in pre.get_feature_names_out()]
            if len(names) == len(values):
                return _aggregate_importance(names, values, feature_names)
        if hasattr(model, "coef_"):
            coef = np.asarray(model.coef_, dtype=float)
            values = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
            names = [str(n) for n in pre.get_feature_names_out()]
            if len(names) == len(values):
                return _aggregate_importance(names, values, feature_names)
    except Exception:
        pass
    try:
        result = permutation_importance(pipe, X_val, y_val, n_repeats=5, random_state=42)
        values = np.clip(np.asarray(result.importances_mean, dtype=float), 0, None)
        total = float(values.sum())
        items = sorted(zip(X_val.columns, values), key=lambda kv: kv[1], reverse=True)[:20]
        return [
            {"feature": str(k), "importance": round(float(v) / total, 4) if total > 0 else 0.0}
            for k, v in items
        ]
    except Exception:
        return []


class ExperimentAgent:
    name = "Experiment"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(
        self,
        *,
        name: str,
        model_type: str,
        estimator,
        preprocessor,
        X: pd.DataFrame,
        y: pd.Series,
        task_type: str,
        primary_metric: str,
        stage: str = "baseline",
        hyperparameters: Optional[dict] = None,
        fit_params: Optional[dict] = None,
        tune: bool = False,
        balance: bool = False,
    ) -> dict:
        ctx = self.ctx
        eid = db.create_experiment(ctx.project_id, name, model_type, stage, hyperparameters or {})
        db.update_experiment(eid, status="running")
        ctx.emit(self.name, "build_baseline" if stage == "baseline" else "improve", f"Training {name}…")
        t0 = time.time()
        try:
            stratify = y if task_type in CLASSIFICATION and y.value_counts().min() >= 2 else None
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=stratify
            )
            pipe = Pipeline([("preprocess", clone(preprocessor)), ("model", estimator)])
            fit_kwargs = {f"model__{k}": v for k, v in (fit_params or {}).items()}
            if balance and task_type in CLASSIFICATION:
                from sklearn.utils.class_weight import compute_sample_weight

                fit_kwargs["model__sample_weight"] = compute_sample_weight("balanced", y_train)
            pipe.fit(X_train, y_train, **fit_kwargs)
            train_seconds = round(time.time() - t0, 2)

            threshold = 0.5
            is_binary = task_type == "binary_classification"
            proba_val = proba_train = None
            if is_binary and hasattr(pipe, "predict_proba"):
                proba_val = pipe.predict_proba(X_val)[:, 1]
                proba_train = pipe.predict_proba(X_train)[:, 1]
                if tune:
                    threshold, _ = tune_threshold(y_val, proba_val, primary_metric)
            if is_binary and proba_val is not None:
                y_pred_val = (proba_val >= threshold).astype(int)
                y_pred_train = (proba_train >= threshold).astype(int)
            else:
                y_pred_val = pipe.predict(X_val)
                y_pred_train = pipe.predict(X_train)

            metrics = [
                {**m, "split": "validation"} for m in compute_metrics(task_type, y_val, y_pred_val, proba_val)
            ] + [{**m, "split": "train"} for m in compute_metrics(task_type, y_train, y_pred_train, proba_train)]

            primary_value = next(
                (m["value"] for m in metrics if m["name"] == primary_metric and m["split"] == "validation"), None
            )

            importance = feature_importance(pipe, X_val, y_val, list(X.columns))
            cm = None
            if task_type in CLASSIFICATION:
                labels = [str(c) for c in pipe.classes_]
                cm = {"labels": labels, "matrix": sk_confusion_matrix(y_val, y_pred_val).astype(int).tolist()}

            artifact = experiment_artifact_path(ctx.project_id, eid)
            classes = [str(c) for c in pipe.classes_] if hasattr(pipe, "classes_") else None
            joblib.dump(
                {
                    "pipeline": pipe,
                    "meta": {
                        "experiment_id": eid,
                        "project_id": ctx.project_id,
                        "model_type": model_type,
                        "model_name": name,
                        "task_type": task_type,
                        "target_column": ctx.task["target_column"] if ctx.task else None,
                        "features": list(X.columns),
                        "numeric_features": [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])],
                        "threshold": threshold if is_binary else None,
                        "classes": classes,
                        "primary_metric": primary_metric,
                    },
                },
                artifact,
            )

            db.update_experiment(
                eid,
                status="completed",
                metrics=metrics,
                primary_metric_name=primary_metric,
                primary_metric_value=primary_value,
                train_seconds=train_seconds,
                feature_importance=importance,
                confusion_matrix=cm,
                artifact_path=str(artifact),
                threshold=threshold if is_binary else None,
            )
            ctx.emit(
                self.name,
                "build_baseline" if stage == "baseline" else "improve",
                f"{name}: validation {primary_metric} = {primary_value:.4f} ({train_seconds:.1f}s)"
                + (f", threshold tuned to {threshold:.2f}" if tune and is_binary else ""),
                "success",
                {"experiment_id": eid, "metrics": metrics},
            )
        except Exception as exc:  # keep the pipeline alive if one model fails
            db.update_experiment(eid, status="failed", error=str(exc)[:500])
            ctx.emit(self.name, "build_baseline" if stage == "baseline" else "improve",
                     f"{name} failed: {exc}", "error")
        row = next(e for e in db.list_experiments(ctx.project_id) if e["id"] == eid)
        return row
