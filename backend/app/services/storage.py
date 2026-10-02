from pathlib import Path

from ..config import ARTIFACTS_DIR, UPLOADS_DIR


def upload_path(project_id: str, filename: str) -> Path:
    safe = Path(filename).name.replace(" ", "_") or "dataset.csv"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR / f"{project_id}__{safe}"


def experiment_dir(project_id: str, experiment_id: str) -> Path:
    d = ARTIFACTS_DIR / project_id / experiment_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def experiment_artifact_path(project_id: str, experiment_id: str) -> Path:
    return experiment_dir(project_id, experiment_id) / "pipeline.joblib"
