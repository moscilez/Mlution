import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import joblib
import pandas as pd

from .data import load_task, task_summary
from .planner import ResearchPlanner
from .plans import Plan, fallback_plans


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    replace_checkpoint(temporary, path)


def replace_checkpoint(source, destination):
    # Windows antivirus/indexing may briefly hold a file being atomically replaced.
    for attempt in range(6):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.02 * (attempt + 1))


def publish(task, predictions):
    if len(predictions) != len(task.sample):
        raise ValueError("Prediction count does not match sample_submission")
    result = task.sample.copy()
    result[task.target] = predictions
    task.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = task.output.with_suffix(".tmp.csv")
    result.to_csv(temporary, index=False, encoding="utf-8")
    replace_checkpoint(temporary, task.output)


def run_trial(input_path, directory, plan, timeout, seed, threads, dummy=False, check_cancelled=None):
    directory.mkdir(parents=True)
    config = {
        "input_path": str(input_path),
        "directory": str(directory),
        "plan": plan.dump(),
        "seed": seed,
        "threads": threads,
        "dummy": dummy,
    }
    # Generated executable source comes from this template; LLM values are JSON data.
    backend = str(Path(__file__).resolve().parents[2])
    source = (
        "import json, sys\nsys.path.insert(0, "
        + repr(backend)
        + ")\nfrom app.competition.trial import execute\nexecute(json.loads("
        + repr(json.dumps(config))
        + "))\n"
    )
    script = directory / "experiment.py"
    script.write_text(source, encoding="utf-8")
    env = {
        name: os.environ[name]
        for name in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "LANG", "PYTHONPATH")
        if name in os.environ
    }
    env.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
            "OMP_NUM_THREADS": str(threads),
            "OPENBLAS_NUM_THREADS": str(threads),
            "MKL_NUM_THREADS": str(threads),
            "NUMEXPR_NUM_THREADS": str(threads),
        }
    )
    env["PYTHONPATH"] = backend + os.pathsep + env.get("PYTHONPATH", "")
    if sys.platform != "win32":
        source = (
            "import resource\n"
            "resource.setrlimit(resource.RLIMIT_AS, (28*1024**3, 28*1024**3))\n"
            f"resource.setrlimit(resource.RLIMIT_CPU, ({math.ceil(timeout * threads)}, {math.ceil(timeout * threads) + 5}))\n"
            "resource.setrlimit(resource.RLIMIT_FSIZE, (256*1024**2, 256*1024**2))\n"
        ) + source
        script.write_text(source, encoding="utf-8")
    with (
        (directory / "stdout.log").open("w", encoding="utf-8") as stdout,
        (directory / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            [sys.executable, "-u", str(script)],
            cwd=directory,
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
        deadline = time.monotonic() + max(1, timeout)
        try:
            while process.poll() is None:
                if check_cancelled:
                    check_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(process.args, timeout)
                try:
                    process.wait(timeout=min(0.25, remaining))
                except subprocess.TimeoutExpired:
                    pass
        except BaseException:
            process.kill()
            process.wait()
            raise
    if process.returncode != 0:
        # Do not put credentials or arbitrary stderr into API responses or the LLM prompt.
        raise RuntimeError(f"Experiment exited with code {process.returncode}; inspect its local stderr.log")
    return json.loads((directory / "result.json").read_text(encoding="utf-8")), pd.read_csv(
        directory / "predictions.csv", dtype=str, keep_default_na=False
    )["prediction"]


def research(
    task_path,
    *,
    output=None,
    seconds=10800,
    max_experiments=24,
    trial_seconds=1200,
    threads=8,
    seed=42,
    offline=False,
    max_llm_calls=16,
    max_llm_tokens=24000,
    emit=None,
    check_cancelled=None,
    started_at=None,
):
    started = time.monotonic() if started_at is None else started_at
    if not 5 <= seconds <= 10800 or not 1 <= max_experiments <= 64 or not 1 <= threads <= 8:
        raise ValueError("Budget must be 5..10800s, experiments 1..64, CPU 1..8")
    planner = ResearchPlanner(max_llm_calls, max_llm_tokens, offline)
    task = load_task(Path(task_path), Path(output) if output else None)
    directory = task.root / ".mlution" / str(uuid.uuid4())
    directory.mkdir(parents=True)
    input_path = directory / "input.joblib"
    joblib.dump(
        (
            task.train[task.features],
            task.train[task.target],
            task.test[task.features],
            task.kind,
            task.metric,
        ),
        input_path,
        compress=0,
    )
    summary = task_summary(task)
    available = {"linear", "hist_gradient", "extra_trees", "random_forest"}
    available |= {name for name in ("catboost", "lightgbm", "xgboost") if importlib.util.find_spec(name)}
    fallback = fallback_plans(task.kind, available)
    history, tried = [], set()
    best_score = None
    lower_better = task.metric in {"rmse", "mae"}
    state = {
        "profile": summary,
        "mode": "offline_heuristic" if offline else "qwen_autoresearch",
        "run_id": directory.name,
        "validation": "fixed_training_only_holdout",
        "seed": seed,
        "experiments": history,
        "output": str(task.output),
        "status": "running",
        "warnings": [
            "Repeated selection on a fixed validation split may overfit; no claim is made about the hidden test score."
        ],
    }

    def event(stage, message, data=None):
        if check_cancelled:
            check_cancelled()
        if emit:
            emit(stage, message, data)

    def save():
        state.update(
            elapsed_seconds=round(time.monotonic() - started, 3),
            llm_calls=planner.calls,
            llm_tokens_reserved=planner.tokens,
        )
        atomic_json(directory / "research.json", state)
        atomic_json(task.root / "research.json", state)

    event("analyze", "Task materials loaded; target and submission schema inferred.", summary)
    # Publish a valid emergency prediction immediately, before any model or LLM call.
    target = task.train[task.target]
    emergency = target.mode().iloc[0] if task.kind == "classification" else float(target.median())
    if task.metric == "roc_auc":
        positive_class = sorted(target.astype(str).unique())[-1]
        emergency = float((target.astype(str) == positive_class).mean())
    publish(task, [emergency] * len(task.test))
    state["checkpoint"] = "emergency_constant"
    save()
    event("plan", "Training-only validation established; emergency submission saved.")
    reserve = min(60, max(2, seconds * 0.1))
    try:
        for index in range(max_experiments):
            remaining = seconds - (time.monotonic() - started)
            if remaining <= reserve:
                break
            event("build_baseline" if index == 0 else "improve", "Selecting next hypothesis.")
            plan = Plan()
            if index:
                plan = None
                if index > 1:
                    try:
                        plan = planner.propose(task.description, summary, history, available, remaining)
                    except Exception:
                        state["warnings"].append(
                            "LLM proposal unavailable or invalid; using an untried local hypothesis within the same budget."
                        )
                if plan and plan.signature() in tried:
                    plan = None
                if plan is None:
                    plan = next(
                        (candidate for candidate in fallback if candidate.signature() not in tried), None
                    )
                if plan is None:
                    break
                if task.kind == "classification" and plan.features == "log_target":
                    plan = Plan(
                        algorithm=plan.algorithm,
                        parameters=plan.parameters,
                        hypothesis=plan.hypothesis,
                        rationale=plan.rationale,
                        source=plan.source,
                    )
                tried.add(plan.signature())
            attempt = {"index": index, "plan": plan.dump(), "dummy": index == 0, "status": "running"}
            if index == 0:
                attempt["plan"].update(
                    algorithm="dummy",
                    hypothesis="A constant predictor establishes the minimum viable reference.",
                    rationale="Save a measured baseline before trying learned models and LLM hypotheses.",
                )
            history.append(attempt)
            save()
            candidate_dir = directory / f"trial-{index:03d}"
            try:
                limit = min(trial_seconds, max(1, seconds - (time.monotonic() - started) - reserve))
                result, predictions = run_trial(
                    input_path,
                    candidate_dir,
                    plan,
                    limit,
                    seed,
                    threads,
                    dummy=index == 0,
                    check_cancelled=check_cancelled,
                )
                score = result["score"]
                accepted = best_score is None or (
                    score < best_score - 1e-9 if lower_better else score > best_score + 1e-9
                )
                attempt.update(
                    result,
                    status="completed",
                    decision="accept" if accepted else "reject",
                    previous_best=best_score,
                )
                event("evaluate", "Validation metrics computed on the fixed training-only holdout.", result)
                if accepted:
                    publish(task, predictions)
                    best_score = score
                    state.update(best=attempt.copy(), checkpoint="validated_full_refit")
                gap = result["train_score"] - score if not lower_better else score - result["train_score"]
                attempt["critique"] = {
                    "generalization_gap": gap,
                    "next_focus": "regularization_or_feature_selection"
                    if gap > (0.1 if not lower_better else abs(score) * 0.25)
                    else "new_features_or_model_family",
                }
                event(
                    "critique",
                    "Hypothesis accepted and checkpoint replaced."
                    if accepted
                    else "Hypothesis rejected; previous checkpoint retained.",
                    attempt,
                )
            except Exception as error:
                attempt.update(
                    status="failed",
                    error="trial_timeout"
                    if isinstance(error, subprocess.TimeoutExpired)
                    else type(error).__name__,
                    decision="reject",
                )
                event(
                    "critique",
                    "Experiment failed; the existing prediction checkpoint is retained.",
                    {"index": index, "error": attempt["error"]},
                )
            save()
        state["status"] = "completed"
        event(
            "finalize",
            "Prediction file and reproducible research history are ready.",
            {"output": task.output.name, "best_score": best_score},
        )
    except BaseException:
        state["status"] = "interrupted"
        save()
        raise
    finally:
        save()
    return state
