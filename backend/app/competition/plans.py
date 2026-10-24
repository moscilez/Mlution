from dataclasses import asdict, dataclass, field
import math

ALGORITHMS = {"linear", "hist_gradient", "extra_trees", "random_forest", "catboost", "lightgbm", "xgboost"}
FEATURE_MODES = {"standard", "robust", "interactions", "selection", "log_target"}
PARAMETERS = {
    "iterations": (20, 2000),
    "max_depth": (2, 16),
    "learning_rate": (0.005, 0.3),
    "l2": (0.01, 1000),
    "min_samples_leaf": (1, 100),
    "balanced": (0, 1),
}


@dataclass
class Plan:
    algorithm: str = "linear"
    features: str = "standard"
    parameters: dict = field(default_factory=dict)
    hypothesis: str = "A simple regularized model establishes a reproducible baseline."
    rationale: str = "Compare every candidate using exactly the same training-only split."
    source: str = "local"

    @classmethod
    def parse(cls, data: dict, source="llm"):
        if not isinstance(data, dict) or set(data) - {
            "algorithm",
            "features",
            "parameters",
            "hypothesis",
            "rationale",
            "source",
        }:
            raise ValueError("Unexpected hypothesis fields")
        plan = cls(**{k: v for k, v in data.items() if k != "source"}, source=source)
        if plan.algorithm not in ALGORITHMS or plan.features not in FEATURE_MODES:
            raise ValueError("Unsupported algorithm or feature recipe")
        if not isinstance(plan.parameters, dict):
            raise ValueError("Parameters must be an object")
        applicable = {
            "linear": {"l2", "balanced"},
            "hist_gradient": {"iterations", "max_depth", "learning_rate", "l2"},
            "extra_trees": {"iterations", "max_depth", "min_samples_leaf", "balanced"},
            "random_forest": {"iterations", "max_depth", "min_samples_leaf", "balanced"},
            "catboost": {"iterations", "max_depth", "learning_rate", "l2"},
            "lightgbm": {"iterations", "max_depth", "learning_rate"},
            "xgboost": {"iterations", "max_depth", "learning_rate"},
        }
        if set(plan.parameters) - applicable[plan.algorithm]:
            raise ValueError("Parameter does not apply to the selected algorithm")
        for name, value in plan.parameters.items():
            if name not in PARAMETERS or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Unknown or non-numeric model parameter")
            low, high = PARAMETERS[name]
            if not low <= value <= high:
                raise ValueError(f"Parameter outside allowed range: {name}")
            if name in {"iterations", "max_depth", "min_samples_leaf", "balanced"} and int(value) != value:
                raise ValueError(f"Integer parameter required: {name}")
        if not isinstance(plan.hypothesis, str) or not isinstance(plan.rationale, str):
            raise ValueError("Hypothesis and rationale must be text")
        plan.hypothesis = plan.hypothesis[:1500]
        plan.rationale = plan.rationale[:1500]
        return plan

    def dump(self):
        return asdict(self)

    def signature(self):
        return self.algorithm, self.features, tuple(sorted(self.parameters.items()))


def fallback_plans(kind: str, available: set[str]) -> list[Plan]:
    choices = [
        Plan("linear"),
        Plan(
            "hist_gradient",
            parameters={"iterations": 200, "learning_rate": 0.07},
            hypothesis="Nonlinear effects may improve upon the linear baseline.",
        ),
        Plan(
            "extra_trees",
            parameters={"iterations": 200, "min_samples_leaf": 2},
            hypothesis="Randomized trees may capture interactions that boosting misses.",
        ),
        Plan(
            "hist_gradient",
            "interactions",
            {"iterations": 300, "learning_rate": 0.05},
            "Ratios and nonlinear numerical features may explain residual error.",
        ),
        Plan(
            "linear",
            "robust",
            {"l2": 10},
            "Robust scaling and stronger regularization may reduce sensitivity to outliers.",
        ),
        Plan(
            "random_forest",
            "selection",
            {"iterations": 200, "max_depth": 12},
            "Feature selection may reduce noise and overfitting.",
        ),
    ]
    for algorithm in ("xgboost", "lightgbm", "catboost"):
        if algorithm in available:
            choices.insert(
                1,
                Plan(
                    algorithm,
                    parameters={"iterations": 500, "learning_rate": 0.05, "max_depth": 6},
                    hypothesis=f"A {algorithm} boosting model may handle heterogeneous tabular signals better.",
                ),
            )
    if kind == "regression":
        choices.append(
            Plan(
                "hist_gradient",
                "log_target",
                {"iterations": 250},
                "A signed logarithmic target may reduce the influence of large residuals.",
            )
        )
    else:
        choices.append(
            Plan(
                "random_forest",
                parameters={"iterations": 250, "balanced": 1},
                hypothesis="Balanced class weights may improve macro F1 for minority classes.",
            )
        )
    return choices
