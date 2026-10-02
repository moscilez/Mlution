from typing import Any

from .base import AgentContext

try:
    from catboost import CatBoostClassifier, CatBoostRegressor

    HAS_CATBOOST = True
except Exception:  # pragma: no cover - optional dependency
    HAS_CATBOOST = False


def build_model_zoo(task_type: str) -> list[dict[str, Any]]:
    """Return the safe, bounded model zoo. Each entry: name, model_type, factory, hyperparameters."""
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LinearRegression, LogisticRegression

    if task_type in ("binary_classification", "multiclass_classification"):
        zoo = [
            {
                "name": "Logistic Regression",
                "model_type": "logistic_regression",
                "factory": lambda: LogisticRegression(max_iter=2000, random_state=42),
                "hyperparameters": {"max_iter": 2000, "penalty": "l2", "C": 1.0},
            },
            {
                "name": "Random Forest",
                "model_type": "random_forest",
                "factory": lambda: RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
                "hyperparameters": {"n_estimators": 300, "max_depth": None},
            },
            {
                "name": "HistGradientBoosting",
                "model_type": "hist_gradient_boosting",
                "factory": lambda: HistGradientBoostingClassifier(random_state=42),
                "hyperparameters": {"max_iter": 100, "learning_rate": 0.1},
            },
        ]
        if HAS_CATBOOST:
            zoo.append(
                {
                    "name": "CatBoost",
                    "model_type": "catboost",
                    "factory": lambda: CatBoostClassifier(verbose=0, random_state=42, iterations=400),
                    "hyperparameters": {"iterations": 400, "verbose": 0},
                }
            )
        return zoo

    zoo = [
        {
            "name": "Linear Regression",
            "model_type": "linear_regression",
            "factory": lambda: LinearRegression(),
            "hyperparameters": {},
        },
        {
            "name": "Random Forest Regressor",
            "model_type": "random_forest",
            "factory": lambda: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1),
            "hyperparameters": {"n_estimators": 300, "max_depth": None},
        },
        {
            "name": "HistGradientBoosting Regressor",
            "model_type": "hist_gradient_boosting",
            "factory": lambda: HistGradientBoostingRegressor(random_state=42),
            "hyperparameters": {"max_iter": 100, "learning_rate": 0.1},
        },
    ]
    if HAS_CATBOOST:
        zoo.append(
            {
                "name": "CatBoost Regressor",
                "model_type": "catboost",
                "factory": lambda: CatBoostRegressor(verbose=0, random_state=42, iterations=400),
                "hyperparameters": {"iterations": 400, "verbose": 0},
            }
        )
    return zoo


class ModelBuilderAgent:
    name = "ModelBuilder"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self, task_type: str) -> list[dict[str, Any]]:
        zoo = build_model_zoo(task_type)
        self.ctx.emit(
            self.name,
            "build_baseline",
            f"Model zoo for {task_type}: {', '.join(m['name'] for m in zoo)}.",
            data={"models": [m["model_type"] for m in zoo]},
        )
        return zoo
