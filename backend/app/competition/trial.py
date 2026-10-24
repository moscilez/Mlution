"""Runs inside a bounded child process; accepts validated declarative model plans."""

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor, make_column_selector
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.feature_selection import SelectPercentile, f_classif, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, OrdinalEncoder, RobustScaler, StandardScaler
from threadpoolctl import threadpool_limits

from .features import TabularFeatures
from .plans import Plan


def signed_log(values):
    return np.sign(values) * np.log1p(np.abs(values))


def signed_exp(values):
    return np.sign(values) * np.expm1(np.minimum(np.abs(values), 40))


def estimator(plan: Plan, classification: bool, seed: int, threads: int):
    p = plan.parameters
    iterations = int(p.get("iterations", 200))
    common = {"random_state": seed}
    if plan.algorithm == "linear":
        return (
            LogisticRegression(
                C=1 / p.get("l2", 1),
                max_iter=1500,
                class_weight="balanced" if p.get("balanced") else None,
                random_state=seed,
            )
            if classification
            else Ridge(alpha=p.get("l2", 1), solver="lsqr")
        )
    if plan.algorithm == "hist_gradient":
        cls = HistGradientBoostingClassifier if classification else HistGradientBoostingRegressor
        return cls(
            max_iter=iterations,
            max_depth=int(p.get("max_depth", 6)),
            learning_rate=p.get("learning_rate", 0.07),
            l2_regularization=p.get("l2", 1),
            early_stopping=True,
            **common,
        )
    if plan.algorithm in {"extra_trees", "random_forest"}:
        cls = (
            (ExtraTreesClassifier if classification else ExtraTreesRegressor)
            if plan.algorithm == "extra_trees"
            else (RandomForestClassifier if classification else RandomForestRegressor)
        )
        kwargs = {"class_weight": "balanced" if p.get("balanced") else None} if classification else {}
        return cls(
            n_estimators=iterations,
            max_depth=int(p.get("max_depth", 12)),
            min_samples_leaf=int(p.get("min_samples_leaf", 2)),
            n_jobs=threads,
            **common,
            **kwargs,
        )
    if plan.algorithm == "catboost":
        from catboost import CatBoostClassifier, CatBoostRegressor

        cls = CatBoostClassifier if classification else CatBoostRegressor
        return cls(
            iterations=iterations,
            depth=int(p.get("max_depth", 6)),
            learning_rate=p.get("learning_rate", 0.05),
            l2_leaf_reg=p.get("l2", 3),
            thread_count=threads,
            verbose=False,
            allow_writing_files=False,
            random_seed=seed,
        )
    if plan.algorithm == "lightgbm":
        from lightgbm import LGBMClassifier, LGBMRegressor

        cls = LGBMClassifier if classification else LGBMRegressor
        return cls(
            n_estimators=iterations,
            max_depth=int(p.get("max_depth", 6)),
            num_leaves=31,
            learning_rate=p.get("learning_rate", 0.05),
            verbosity=-1,
            n_jobs=threads,
            **common,
        )
    if plan.algorithm == "xgboost":
        from xgboost import XGBClassifier, XGBRegressor

        cls = XGBClassifier if classification else XGBRegressor
        return cls(
            n_estimators=iterations,
            max_depth=int(p.get("max_depth", 6)),
            learning_rate=p.get("learning_rate", 0.05),
            tree_method="hist",
            n_jobs=threads,
            **common,
        )
    raise ValueError("Unsupported estimator")


def make_pipeline(plan, classification, seed, threads):
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", RobustScaler() if plan.features == "robust" else StandardScaler()),
        ]
    )
    encoding = (
        OneHotEncoder(handle_unknown="ignore", max_categories=24, sparse_output=True)
        if plan.algorithm == "linear"
        else OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    )
    categorical = Pipeline(
        [
            (
                "impute",
                SimpleImputer(strategy="constant", fill_value="__missing__", keep_empty_features=True),
            ),
            ("encode", encoding),
        ]
    )
    preprocessing = ColumnTransformer(
        [
            ("numeric", numeric, make_column_selector(dtype_include=np.number)),
            ("categorical", categorical, make_column_selector(dtype_exclude=np.number)),
        ],
        sparse_threshold=1.0 if plan.algorithm == "linear" else 0,
    )
    model = estimator(plan, classification, seed, threads)
    steps = [("features", TabularFeatures(plan.features)), ("preprocess", preprocessing)]
    if plan.features == "selection":
        steps.append(
            ("select", SelectPercentile(f_classif if classification else f_regression, percentile=75))
        )
    steps.append(("model", model))
    pipeline = Pipeline(steps)
    return (
        TransformedTargetRegressor(
            regressor=pipeline, func=signed_log, inverse_func=signed_exp, check_inverse=False
        )
        if plan.features == "log_target" and not classification
        else pipeline
    )


def measure(metric, truth, predicted, probabilities=None):
    if metric == "rmse":
        return float(np.sqrt(mean_squared_error(truth, predicted)))
    if metric == "mae":
        return float(mean_absolute_error(truth, predicted))
    if metric == "r2":
        return float(r2_score(truth, predicted))
    if metric == "accuracy":
        return float(accuracy_score(truth, predicted))
    if metric == "roc_auc":
        if probabilities is None or probabilities.shape[1] != 2:
            raise ValueError("Binary probabilities are required for ROC AUC")
        return float(roc_auc_score(truth, probabilities[:, 1]))
    return float(f1_score(truth, predicted, average="macro", zero_division=0))


def execute(config: dict):
    directory = Path(config["directory"])
    started = time.monotonic()
    X, y, X_test, kind, metric = joblib.load(config["input_path"])
    classification = kind == "classification"
    encoder = LabelEncoder().fit(y.astype(str)) if classification else None
    y = encoder.transform(y.astype(str)) if classification else np.asarray(y, dtype=float)
    train_idx, val_idx = train_test_split(
        np.arange(len(X)),
        test_size=max(0.2, (len(encoder.classes_) / len(X)) if classification else 0.2),
        random_state=config["seed"],
        stratify=y if classification else None,
    )
    if config.get("dummy"):
        model = DummyClassifier(strategy="prior") if classification else DummyRegressor(strategy="median")
        train_X, val_X, test_X = (
            np.zeros((len(train_idx), 1)),
            np.zeros((len(val_idx), 1)),
            np.zeros((len(X_test), 1)),
        )
    else:
        plan = Plan.parse(config["plan"])
        model = make_pipeline(plan, classification, config["seed"], config["threads"])
        train_X, val_X, test_X = X.iloc[train_idx], X.iloc[val_idx], X_test
    with threadpool_limits(limits=config["threads"]):
        model.fit(train_X, y[train_idx])
        predictions = model.predict(val_X)
        probabilities = model.predict_proba(val_X) if metric == "roc_auc" else None
        score = measure(metric, y[val_idx], predictions, probabilities)
        train_predictions = model.predict(train_X)
        train_probabilities = model.predict_proba(train_X) if metric == "roc_auc" else None
        training_score = measure(metric, y[train_idx], train_predictions, train_probabilities)
        # Refit the validated recipe using all labelled rows before predicting test.
        full_X = np.zeros((len(X), 1)) if config.get("dummy") else X
        model.fit(full_X, y)
        test_predictions = (
            model.predict_proba(test_X)[:, 1]
            if metric == "roc_auc"
            else encoder.inverse_transform(np.asarray(model.predict(test_X), dtype=int))
            if classification
            else model.predict(test_X)
        )
    if not np.isfinite(score) or (
        not classification and not np.isfinite(test_predictions.astype(float)).all()
    ):
        raise ValueError("Non-finite metric or prediction")
    pd.DataFrame({"prediction": test_predictions}).to_csv(directory / "predictions.csv", index=False)
    report = {
        "score": score,
        "train_score": training_score,
        "train_rows": len(train_idx),
        "validation_rows": len(val_idx),
        "seconds": round(time.monotonic() - started, 3),
        "metric": metric,
        "validation": "fixed_stratified_holdout" if classification else "fixed_holdout",
    }
    (directory / "result.json").write_text(json.dumps(report, allow_nan=False), encoding="utf-8")
