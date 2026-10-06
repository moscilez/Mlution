from typing import Optional

from .. import db
from ..config import LOWER_IS_BETTER
from ..services.llm import narrate
from .base import AgentContext


def _fmt(v: Optional[float]) -> str:
    return f"{v:.4f}" if v is not None else "n/a"


def generate_usage_code(project: dict, best: dict, profile: dict, task: dict) -> str:
    target = task["target_column"]
    dropped = set(profile.get("id_columns") or []) | {
        c["column"] for c in (profile.get("leakage_candidates") or [])
    }
    example = {}
    for col in profile.get("columns") or []:
        if col["name"] == target or col["name"] in dropped:
            continue
        ex = (col.get("examples") or [None])[0]
        if ex is None:
            continue
        if col["kind"] == "numeric":
            try:
                ex = float(ex)
            except (TypeError, ValueError):
                pass
        example[col["name"]] = ex

    is_classification = task["task_type"] != "regression"
    lines = [
        '"""',
        "Mlution inference script. Load only the model downloaded from your own project.",
        f"Validation {best['primary_metric_name']} = {_fmt(best['primary_metric_value'])}.",
        "",
        "Usage:  pip install joblib pandas scikit-learn",
        "        python mlution_inference.py",
        '"""',
        f"# Project: {project['name']!r}; target: {target!r}; model: {best['model_type']!r}",
        "import joblib",
        "import pandas as pd",
        "",
        'ARTIFACT_PATH = "mlution_model.joblib"  # downloaded from Mlution',
        "",
        "sample = {",
    ]
    for k, v in example.items():
        lines.append(f"    {k!r}: {v!r},")
    lines += [
        "}",
        "",
        "bundle = joblib.load(ARTIFACT_PATH)",
        'pipeline, meta = bundle["pipeline"], bundle["meta"]',
        "",
        'df = pd.DataFrame([{key: sample.get(key) for key in meta["features"]}])',
        'for col in meta.get("numeric_features", []):',
        "    if col in df:",
        '        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)',
        "",
    ]
    if is_classification:
        lines += [
            "proba = pipeline.predict_proba(df)[0]",
            'classes = [str(c) for c in meta["classes"]]',
            'threshold = meta.get("threshold") or 0.5',
            "if len(classes) == 2:",
            "    prediction = classes[1] if proba[1] >= threshold else classes[0]",
            "else:",
            "    prediction = classes[int(proba.argmax())]",
            'print("Prediction:", prediction)',
            'print("Probabilities:", {c: round(float(p), 4) for c, p in zip(classes, proba)})',
        ]
    else:
        lines += [
            "prediction = float(pipeline.predict(df)[0])",
            'print("Prediction:", round(prediction, 4))',
        ]
    return "\n".join(lines) + "\n"


class ReportAgent:
    name = "Report"

    def __init__(self, ctx: AgentContext):
        self.ctx = ctx

    def run(
        self,
        task: dict,
        profile: dict,
        experiments: list[dict],
        improvements: list[dict],
        critic_warnings: list[dict],
    ) -> dict:
        ctx = self.ctx
        project = ctx.project
        primary = task["primary_metric"]
        higher_better = primary not in LOWER_IS_BETTER
        completed = [e for e in experiments if e["status"] == "completed"]
        if not completed:
            raise RuntimeError("No completed experiments to report on.")
        best = max(
            completed,
            key=lambda e: e["primary_metric_value"] if higher_better else -e["primary_metric_value"],
        )

        leaderboard = [
            {
                "experiment_id": e["id"],
                "model_type": e["model_type"],
                "stage": e["stage"],
                "primary_metric_value": e["primary_metric_value"],
            }
            for e in sorted(
                completed,
                key=lambda e: e["primary_metric_value"] if higher_better else -e["primary_metric_value"],
                reverse=True,
            )
        ]

        others = [e for e in completed if e["id"] != best["id"]]
        runner_up = max(
            others,
            key=lambda e: e["primary_metric_value"] if higher_better else -e["primary_metric_value"],
            default=None,
        )
        comparison = (
            f"It beats the runner-up ({runner_up['name']}, {_fmt(runner_up['primary_metric_value'])})"
            if runner_up
            else "It is the only completed experiment"
        )
        fallback_explanation = (
            f"{best['name']} achieved the best validation {primary} ({_fmt(best['primary_metric_value'])}). "
            f"{comparison} on a held-out 20% validation split. "
            + (
                f"The improvement step ({improvements[-1]['action']}) was "
                f"{'accepted' if improvements[-1]['decision'] == 'accept_improvement' else 'rejected — the baseline stayed better'}."
                if improvements
                else "No improvement step was applied."
            )
        )
        explanation = narrate(
            "Explain in 2-4 sentences why the winning model was selected, referencing only the metrics given.",
            f"Task: {task['task_type']}, primary metric: {primary}. "
            f"Leaderboard: {[(entry['model_type'], round(entry['primary_metric_value'], 4)) for entry in leaderboard]}. "
            f"Improvements: {[(i['action'], i['decision']) for i in improvements]}.",
            fallback_explanation,
        )

        summary = (
            f"Mlution trained {len(completed)} model(s) for {task['task_type']} on "
            f"{profile['n_rows']} rows × {profile['n_columns']} columns. "
            f"Best model: {best['name']} with validation {primary} = {_fmt(best['primary_metric_value'])}."
        )

        limitations = [
            "Single 80/20 train/validation split — no cross-validation.",
            "One improvement step only (bounded hyperparameter exploration).",
        ]
        if profile["n_rows"] < 2000:
            limitations.append(f"Small dataset ({profile['n_rows']} rows) — metrics may be unstable.")
        if profile.get("imbalance_warning"):
            limitations.append("Class imbalance present — interpret precision/recall together, not accuracy.")

        next_steps = [
            "Collect more data, especially for underrepresented segments.",
            "Add domain-specific features (ratios, aggregates, time windows).",
            "Run a longer Optuna hyperparameter search with cross-validation.",
            "Set up periodic retraining and drift monitoring.",
        ]

        usage_code = generate_usage_code(project, best, profile, task)
        warnings = (profile.get("warnings") or []) + critic_warnings

        from ..schemas import FinalReport

        report = FinalReport(
            summary=summary,
            task=task,
            best_experiment_id=best["id"],
            best_model_type=best["model_type"],
            metrics=best["metrics"],
            leaderboard=leaderboard,
            improvements=improvements,
            warnings=warnings,
            limitations=limitations,
            next_steps=next_steps,
            explanation=explanation,
            usage_code=usage_code,
            generated_at=db.utcnow(),
        )
        db.update_project(ctx.project_id, report_json=report.model_dump())
        ctx.emit(self.name, "finalize", "Final report generated.", "success")
        return report.model_dump()
