from typing import Any, Optional

from ..config import LOWER_IS_BETTER
from .base import AgentContext


def _val_metric(exp: dict, name: str) -> Optional[float]:
    for m in exp.get("metrics") or []:
        if m["name"] == name and m["split"] == "validation":
            return m["value"]
    return None


def _train_metric(exp: dict, name: str) -> Optional[float]:
    for m in exp.get("metrics") or []:
        if m["name"] == name and m["split"] == "train":
            return m["value"]
    return None


class CriticAgent:
    name = "Critic"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(self, task: dict, experiments: list[dict], profile: dict) -> tuple[list[dict], Optional[dict]]:
        ctx = self.ctx
        primary = task["primary_metric"]
        higher_better = primary not in LOWER_IS_BETTER
        completed = [e for e in experiments if e["status"] == "completed" and e["stage"] == "baseline"]
        warnings: list[dict] = []
        if not completed:
            return warnings, None

        best = max(
            completed,
            key=lambda e: e["primary_metric_value"] if higher_better else -e["primary_metric_value"],
        )

        train_v = _train_metric(best, primary)
        val_v = _val_metric(best, primary)
        if train_v is not None and val_v is not None:
            if higher_better and train_v - val_v > 0.15:
                warnings.append(
                    {
                        "level": "warning",
                        "code": "overfitting",
                        "message": f"Possible overfitting in {best['name']}: train {primary}={train_v:.3f} vs validation {val_v:.3f}.",
                    }
                )
            if not higher_better and val_v > 0 and (val_v - train_v) / val_v > 0.3:
                warnings.append(
                    {
                        "level": "warning",
                        "code": "overfitting",
                        "message": f"Possible overfitting in {best['name']}: train {primary}={train_v:.4f} vs validation {val_v:.4f}.",
                    }
                )

        if higher_better and val_v is not None and val_v >= 0.999:
            leak = profile.get("leakage_candidates") or []
            warnings.append(
                {
                    "level": "critical",
                    "code": "suspicious_perfect_score",
                    "message": f"Validation {primary} is nearly perfect ({val_v:.4f}). "
                    + (
                        f"Leakage suspects already excluded: {', '.join(c['column'] for c in leak)}."
                        if leak
                        else "Double-check for data leakage."
                    ),
                }
            )

        for w in warnings:
            ctx.emit(
                self.name, "critique", w["message"], "warning" if w["level"] != "critical" else "error", w
            )

        proposal: Optional[dict[str, Any]] = None
        if ctx.experiment_slots_left() <= 0:
            ctx.emit(self.name, "critique", "Experiment budget exhausted — skipping improvement step.")
        elif ctx.time_left() < 30:
            ctx.emit(self.name, "critique", "Time budget nearly exhausted — skipping improvement step.")
        elif task["task_type"] == "binary_classification" and profile.get("imbalance_warning"):
            proposal = {
                "kind": "imbalance",
                "hypothesis": "Class imbalance reduces recall of the minority class",
                "reason": "Minority class share is below 20%, so a default 0.5 threshold and uniform class weights under-detect the positive class.",
                "action": "Retrain the best model family with balanced class weights and optimize the decision threshold on validation data",
                "base_experiment_id": best["id"],
            }
        elif task["task_type"] == "binary_classification":
            proposal = {
                "kind": "threshold",
                "hypothesis": "The default 0.5 decision threshold is suboptimal for the chosen metric",
                "reason": f"Primary metric is {primary}; tuning the threshold can improve it without retraining.",
                "action": f"Optimize the decision threshold on validation data for {primary}",
                "base_experiment_id": best["id"],
            }
        else:
            proposal = {
                "kind": "hpo",
                "hypothesis": "A stronger hyperparameter configuration of the best model family improves validation performance",
                "reason": "Baseline models used default hyperparameters.",
                "action": "Train one tuned variant of the best baseline model family",
                "base_experiment_id": best["id"],
            }

        if proposal:
            ctx.emit(
                self.name, "critique", f"Improvement hypothesis: {proposal['hypothesis']}", data=proposal
            )
        return warnings, proposal
