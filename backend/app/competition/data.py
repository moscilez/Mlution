import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Task:
    root: Path
    description: str
    target: str
    identifiers: list[str]
    features: list[str]
    kind: str
    metric: str
    train: pd.DataFrame
    test: pd.DataFrame
    sample: pd.DataFrame
    dictionary: pd.DataFrame
    output: Path


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    # Detect duplicate headers before pandas silently mangles them.
    with path.open(encoding="utf-8-sig", newline="") as stream:
        headers = next(csv.reader(stream), [])
    if not headers or len(headers) != len(set(headers)):
        raise ValueError(f"Empty or duplicate CSV columns: {path.name}")
    kwargs.setdefault("keep_default_na", False)
    kwargs.setdefault("na_values", [""])
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kwargs)


def load_task(task_path: Path, output: Path | None = None) -> Task:
    task_path = task_path.resolve()
    root = task_path.parent
    description = task_path.read_text(encoding="utf-8-sig")[:40000]
    train = read_csv(root / "train.csv")
    test = read_csv(root / "test.csv")
    # Preserve identifier strings, including leading zeros, exactly as provided.
    sample = read_csv(root / "sample_submission.csv", dtype=str, na_values=[])
    dictionary = read_csv(root / "data_dictionary.csv")
    if train.empty or test.empty or len(sample) != len(test):
        raise ValueError("Train/test must be non-empty; sample_submission must have one row per test row")
    candidates = [column for column in sample if column in train and column not in test]
    if len(candidates) != 1:
        raise ValueError(
            "Cannot infer one target from train/test/sample_submission; target must be absent in test"
        )
    target = candidates[0]
    identifiers = [column for column in sample if column != target]
    if not identifiers or any(column not in test for column in identifiers):
        raise ValueError("Submission identifiers must exist in test.csv")
    raw_test_ids = read_csv(root / "test.csv", usecols=identifiers, dtype=str, na_values=[])
    if (sample[identifiers] == "").any().any() or (raw_test_ids == "").any().any():
        raise ValueError("Identifiers cannot be empty")
    if sample[identifiers].duplicated().any() or raw_test_ids.duplicated().any():
        raise ValueError("Submission/test identifiers must be unique")
    if set(map(tuple, sample[identifiers].values)) != set(map(tuple, raw_test_ids.values)):
        raise ValueError("Submission and test identifiers do not match")
    # Align test to submission order; never assume the sample has the same row order.
    index = raw_test_ids.reset_index().set_index(identifiers)
    order = index.loc[
        pd.MultiIndex.from_frame(sample[identifiers]) if len(identifiers) > 1 else sample[identifiers[0]],
        "index",
    ]
    test = test.iloc[np.asarray(order)].reset_index(drop=True)
    y = train[target]
    labelled = y.notna()
    if y.isna().any():
        train = train.loc[y.notna()].reset_index(drop=True)
        y = train[target]
    if len(train) < 10:
        raise ValueError("At least 10 labelled training rows are required")
    if not {"feature", "role"}.issubset(dictionary.columns):
        raise ValueError("data_dictionary.csv requires feature and role columns")
    roles = dict(zip(dictionary.feature.astype(str), dictionary.role.astype(str).str.lower()))
    excluded = set(identifiers) | {
        name for name, role in roles.items() if role in {"id", "identifier", "target", "ignore", "ignored"}
    }
    features = [column for column in train if column != target and column not in excluded and column in test]
    if not features:
        raise ValueError("No shared input features")
    lower = description.lower()
    metric_line = re.search(
        r"(?:основная\s+метрика|метрика|primary\s+metric|metric)\s*[:=]\s*([^\n]+)", lower
    )
    if metric_line:
        lower = metric_line.group(1)
    if any(word in lower for word in ("rmse", "mae", "r2", "r²", "регресси", "regression")):
        kind = "regression"
    elif any(
        word in lower for word in ("macro", "классификац", "classification", "f1", "accuracy", "roc_auc")
    ):
        kind = "classification"
    else:
        kind = "regression" if pd.api.types.is_numeric_dtype(y) and y.nunique() > 20 else "classification"
    if kind == "regression":
        numeric_target = pd.to_numeric(y, errors="raise")
        if not np.isfinite(numeric_target).all():
            raise ValueError("Regression targets must be finite")
        train[target] = numeric_target
        metric = (
            "mae"
            if re.search(r"\bmae\b", lower) and "rmse" not in lower
            else "r2"
            if re.search(r"\br2\b|r²", lower) and "rmse" not in lower
            else "rmse"
        )
    else:
        metric = "f1_macro"
        raw_target = read_csv(root / "train.csv", usecols=[target], dtype=str)
        train[target] = raw_target.loc[labelled, target].reset_index(drop=True)
        y = train[target]
        if "macro" not in lower and "макро" not in lower:
            if "roc_auc" in lower or "roc auc" in lower:
                metric = "roc_auc"
            elif "accuracy" in lower and not re.search(r"\bf1\b", lower):
                metric = "accuracy"
        if y.nunique() < 2 or y.value_counts().min() < 2:
            raise ValueError("Classification needs at least two examples of every class")
        if metric == "roc_auc" and y.nunique() != 2:
            raise ValueError("ROC AUC submission currently requires a binary target")
    if output is None:
        # Respect common output filenames in task.md; input filenames cannot become output.
        names = re.findall(r"[\w./-]*(?:submission|predictions)[\w.-]*\.csv", description, flags=re.I)
        names = [name for name in names if Path(name).name != "sample_submission.csv"]
        output = Path(names[-1] if names else "submission.csv")
    output = output.resolve() if output.is_absolute() else (root / output).resolve()
    if not output.is_relative_to(root) or output.name in {
        "train.csv",
        "test.csv",
        "sample_submission.csv",
        "data_dictionary.csv",
    }:
        raise ValueError("Prediction output must be a new CSV inside the task directory")
    return Task(
        root,
        description,
        target,
        identifiers,
        features,
        kind,
        metric,
        train,
        test,
        sample,
        dictionary,
        output,
    )


def task_summary(task: Task) -> dict:
    return {
        "target": task.target,
        "task_type": task.kind,
        "metric": task.metric,
        "train_rows": len(task.train),
        "test_rows": len(task.test),
        "features": [
            {
                "name": col,
                "dtype": str(task.train[col].dtype),
                "missing": round(float(task.train[col].isna().mean()), 3),
                "unique": int(task.train[col].nunique()),
            }
            for col in task.features[:80]
        ],
        "classes": int(task.train[task.target].nunique()) if task.kind == "classification" else None,
    }
