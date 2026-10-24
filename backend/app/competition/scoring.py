import math


def normalized_score(metric: str, value: float, baseline: float) -> float:
    if not all(math.isfinite(number) for number in (value, baseline)):
        raise ValueError("Scores must be finite")
    if metric == "rmse":
        if baseline <= 0 or value < 0:
            raise ValueError("RMSE baseline must be positive and candidate RMSE non-negative")
        return 100 * max(0, min(1, 1 - value / baseline))
    if metric == "f1_macro":
        if not 0 <= baseline < 1 or not 0 <= value <= 1:
            raise ValueError("Macro F1 must be in [0,1] and its baseline below 1")
        return 100 * max(0, min(1, (value - baseline) / (1 - baseline)))
    raise ValueError("Organizer normalized score is specified only for RMSE and Macro F1")


def combined_score(first: float, second: float) -> float:
    if not all(math.isfinite(value) and 0 <= value <= 100 for value in (first, second)):
        raise ValueError("Task scores must be in [0,100]")
    return (first + second) / 2
