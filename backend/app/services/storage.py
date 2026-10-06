from pathlib import Path
import uuid
import shutil

from ..config import ARTIFACTS_DIR, UPLOADS_DIR


def upload_path(project_id: str, filename: str) -> Path:
    directory = UPLOADS_DIR / project_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{uuid.uuid4()}.csv"


def experiment_dir(project_id: str, experiment_id: str) -> Path:
    d = ARTIFACTS_DIR / project_id / experiment_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def experiment_artifact_path(project_id: str, experiment_id: str) -> Path:
    return experiment_dir(project_id, experiment_id) / "pipeline.joblib"


def remove_project_files(project_id: str):
    uuid.UUID(project_id)
    for root in (ARTIFACTS_DIR, UPLOADS_DIR):
        directory = (root / project_id).resolve()
        if directory.is_relative_to(root.resolve()) and directory.exists():
            shutil.rmtree(directory)
