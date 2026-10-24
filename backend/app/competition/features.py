import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class TabularFeatures(TransformerMixin, BaseEstimator):
    """Fit schema only on the training fold; never derive features from the target."""

    def __init__(self, mode="standard"):
        self.mode = mode

    def fit(self, X, y=None):
        self.columns_ = list(X.columns)
        self.numeric_ = [name for name in X if pd.api.types.is_numeric_dtype(X[name])]
        self.categorical_ = [name for name in X if name not in self.numeric_]
        return self

    def transform(self, X):
        result = X[self.columns_].copy()
        for name in self.numeric_:
            result[name] = (
                pd.to_numeric(result[name], errors="coerce").replace([np.inf, -np.inf], np.nan).astype(float)
            )
        for name in self.categorical_:
            result[name] = result[name].map(lambda value: str(value) if pd.notna(value) else np.nan)
        if self.mode == "interactions":
            for index, name in enumerate(self.numeric_[:6]):
                value = result[name].clip(-1e12, 1e12)
                result[f"__mlution_log_{index}"] = np.sign(value) * np.log1p(np.abs(value))
                result[f"__mlution_missing_{index}"] = value.isna().astype(float)
                if index:
                    denominator = result[self.numeric_[index - 1]].replace(0, np.nan)
                    result[f"__mlution_ratio_{index}"] = (value / denominator).clip(-1e12, 1e12)
        return result
