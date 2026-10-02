import re
from typing import Optional

import numpy as np
import pandas as pd

from ..schemas import DatasetProfile
from .base import AgentContext

ID_PATTERN = re.compile(r"(^|_)(id|uuid|guid|index|row_id)(_|$)", re.IGNORECASE)
TARGET_NAME_HINTS = ["target", "label", "y", "outcome", "churn", "default", "fraud", "survived", "price", "clicked"]
LEAKAGE_KEYWORDS = ["reason", "label", "outcome", "result", "answer", "after", "post_", "leak"]


def _column_kind(series: pd.Series, n_rows: int) -> str:
    name = str(series.name)
    n_unique = series.nunique(dropna=True)
    if ID_PATTERN.search(name):
        return "id_like"
    if n_rows > 20 and n_unique / max(n_rows, 1) > 0.98 and series.dtype == object:
        return "id_like"
    if pd.api.types.is_numeric_dtype(series):
        if n_rows > 20 and n_unique / max(n_rows, 1) > 0.98 and name.lower().endswith("id"):
            return "id_like"
        return "numeric"
    return "categorical"


def _suggest_target(df: pd.DataFrame, kinds: dict[str, str]) -> Optional[str]:
    lowered = {str(c).lower(): c for c in df.columns}
    for hint in TARGET_NAME_HINTS:
        if hint in lowered and kinds.get(lowered[hint]) != "id_like":
            return lowered[hint]
    last = df.columns[-1]
    if kinds.get(str(last)) != "id_like" and df[last].nunique(dropna=True) <= 20:
        return str(last)
    return None


def _task_hint(df: pd.DataFrame, target: Optional[str]) -> Optional[str]:
    if target is None:
        return None
    s = df[target]
    n_unique = s.nunique(dropna=True)
    if pd.api.types.is_numeric_dtype(s) and n_unique > 20:
        return "regression"
    if n_unique <= 2:
        return "binary_classification"
    if n_unique <= 20:
        return "multiclass_classification"
    return "regression" if pd.api.types.is_numeric_dtype(s) else None


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    n_rows, n_columns = df.shape
    n_duplicates = int(df.duplicated().sum())

    columns = []
    kinds: dict[str, str] = {}
    for col in df.columns:
        s = df[col]
        kind = _column_kind(s, n_rows)
        kinds[str(col)] = kind
        non_null = s.dropna()
        examples = [str(v) for v in non_null.unique()[:10]] if kind == "categorical" else [
            str(round(float(v), 4)) if isinstance(v, float) else str(v) for v in non_null.head(5)
        ]
        columns.append(
            {
                "name": str(col),
                "dtype": str(s.dtype),
                "kind": kind,
                "n_missing": int(s.isna().sum()),
                "missing_pct": round(float(s.isna().mean()) * 100, 2),
                "n_unique": int(s.nunique(dropna=True)),
                "examples": examples,
            }
        )

    numeric_columns = [c["name"] for c in columns if c["kind"] == "numeric"]
    categorical_columns = [c["name"] for c in columns if c["kind"] == "categorical"]
    id_columns = [c["name"] for c in columns if c["kind"] == "id_like"]

    target = _suggest_target(df, kinds)
    task_hint = _task_hint(df, target)

    leakage_candidates: list[dict] = []
    for col in df.columns:
        name = str(col)
        if name == target or kinds.get(name) == "id_like":
            continue
        low = name.lower()
        if target and target.lower() in low:
            leakage_candidates.append({"column": name, "reason": f"Column name contains the target name '{target}'"})
            continue
        if any(k in low for k in LEAKAGE_KEYWORDS):
            leakage_candidates.append({"column": name, "reason": "Column name suggests post-outcome information"})
            continue
        if target and pd.api.types.is_numeric_dtype(df[col]) and pd.api.types.is_numeric_dtype(df[target]):
            pair = df[[col, target]].dropna()
            if len(pair) > 10 and pair[col].nunique() > 1 and pair[target].nunique() > 1:
                corr = float(pair[col].corr(pair[target]))
                if abs(corr) > 0.95:
                    leakage_candidates.append(
                        {"column": name, "reason": f"Suspiciously high correlation with target ({corr:.3f})"}
                    )

    class_balance = None
    imbalance_warning = False
    warnings: list[dict] = []

    if target and task_hint in ("binary_classification", "multiclass_classification"):
        counts = df[target].value_counts(dropna=False)
        class_balance = {str(k): int(v) for k, v in counts.items()}
        minority_share = float(counts.min() / counts.sum()) if counts.sum() else 0.0
        if task_hint == "binary_classification" and minority_share < 0.20:
            imbalance_warning = True
            warnings.append(
                {
                    "level": "warning",
                    "code": "class_imbalance",
                    "message": f"Class imbalance detected: minority class is {minority_share:.0%} of rows. "
                    "Accuracy-like metrics will be misleading; f1/recall recommended.",
                }
            )

    for c in columns:
        if c["missing_pct"] > 30:
            warnings.append(
                {
                    "level": "warning",
                    "code": "high_missing",
                    "message": f"Column '{c['name']}' has {c['missing_pct']:.0f}% missing values.",
                }
            )
        if c["kind"] == "categorical" and c["n_unique"] > 50:
            warnings.append(
                {
                    "level": "info",
                    "code": "high_cardinality",
                    "message": f"Categorical column '{c['name']}' has {c['n_unique']} unique values; encoding may be noisy.",
                }
            )

    if n_duplicates > 0 and n_duplicates / max(n_rows, 1) > 0.01:
        warnings.append(
            {
                "level": "info",
                "code": "duplicates",
                "message": f"{n_duplicates} exact duplicate rows ({n_duplicates / n_rows:.1%}).",
            }
        )
    for col in id_columns:
        warnings.append(
            {"level": "info", "code": "id_column", "message": f"Column '{col}' looks like an identifier and will be excluded from training."}
        )
    for cand in leakage_candidates:
        warnings.append(
            {
                "level": "critical",
                "code": "data_leakage",
                "message": f"Potential data leakage in '{cand['column']}': {cand['reason']}. It will be excluded from training.",
            }
        )

    return DatasetProfile(
        n_rows=int(n_rows),
        n_columns=int(n_columns),
        columns=columns,
        n_duplicates=n_duplicates,
        duplicate_pct=round(n_duplicates / max(n_rows, 1) * 100, 2),
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        id_columns=id_columns,
        leakage_candidates=leakage_candidates,
        target_column=target,
        task_hint=task_hint,
        class_balance=class_balance,
        imbalance_warning=imbalance_warning,
        warnings=warnings,
    )


class DataAnalystAgent:
    name = "DataAnalyst"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self) -> dict:
        ctx = self.ctx
        ctx.emit(self.name, "analyze", "Loading dataset and computing data profile…")
        df = ctx.load_df()
        profile = profile_dataframe(df)
        db_update = profile.model_dump()
        from .. import db as _db

        _db.update_project(ctx.project_id, profile_json=db_update)
        ctx.emit(
            self.name,
            "analyze",
            f"Profile ready: {profile.n_rows} rows × {profile.n_columns} columns — "
            f"{len(profile.numeric_columns)} numeric, {len(profile.categorical_columns)} categorical, "
            f"{len(profile.id_columns)} id-like. Duplicates: {profile.n_duplicates}.",
            "success",
            {"n_rows": profile.n_rows, "n_columns": profile.n_columns},
        )
        for w in profile.warnings:
            ctx.emit(self.name, "analyze", w.message, "warning" if w.level != "critical" else "error", w.model_dump())
        if profile.target_column:
            ctx.emit(
                self.name,
                "analyze",
                f"Potential target column detected: '{profile.target_column}' (hint: {profile.task_hint}).",
            )
        return profile.model_dump()
