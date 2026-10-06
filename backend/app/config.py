import os
from pathlib import Path
from .settings import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MLUTION_DATA_DIR", str(BASE_DIR / "data"))).resolve()
UPLOADS_DIR = DATA_DIR / "uploads"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
DEMO_DIR = DATA_DIR / "demo"
DEMO_CSV = DEMO_DIR / "churn_demo.csv"

LLM_API_KEY = get_settings().llm_api_key
LLM_BASE_URL = get_settings().llm_base_url
LLM_MODEL = get_settings().llm_model

LOWER_IS_BETTER = {"rmse", "mae", "mse", "log_loss"}

STAGES = ["analyze", "plan", "build_baseline", "evaluate", "critique", "improve", "finalize"]


def ensure_dirs() -> None:
    for d in (DATA_DIR, UPLOADS_DIR, ARTIFACTS_DIR, DEMO_DIR):
        d.mkdir(parents=True, exist_ok=True)
