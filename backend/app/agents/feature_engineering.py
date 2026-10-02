import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .base import AgentContext


class FeatureEngineeringAgent:
    name = "FeatureEngineering"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def plan(self, df: pd.DataFrame, target: str, profile: dict) -> dict:
        drop_cols = set(profile.get("id_columns") or [])
        drop_cols |= {c["column"] for c in (profile.get("leakage_candidates") or [])}
        features = [c for c in df.columns if c != target and c not in drop_cols]
        numeric = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
        categorical = [c for c in features if c not in numeric]
        dropped = sorted(drop_cols & set(df.columns))
        if dropped:
            self.ctx.emit(
                self.name,
                "plan",
                f"Excluding id/leakage columns from features: {', '.join(dropped)}.",
                "warning",
            )
        self.ctx.emit(
            self.name,
            "plan",
            f"Preprocessing: median-impute + standard-scale {len(numeric)} numeric, "
            f"most-frequent-impute + one-hot encode {len(categorical)} categorical features.",
        )
        return {"features": features, "numeric": numeric, "categorical": categorical, "dropped": dropped}

    @staticmethod
    def build_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
        transformers = []
        if numeric:
            transformers.append(
                ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric)
            )
        if categorical:
            transformers.append(
                (
                    "cat",
                    Pipeline(
                        [
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                        ]
                    ),
                    categorical,
                )
            )
        return ColumnTransformer(transformers)
