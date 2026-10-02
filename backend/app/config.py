import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MLUTION_DATA_DIR", str(BASE_DIR / "data"))).resolve()
DB_PATH = DATA_DIR / "mlution.db"
UPLOADS_DIR = DATA_DIR / "uploads"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
DEMO_DIR = DATA_DIR / "demo"
DEMO_CSV = DEMO_DIR / "churn_demo.csv"

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

LOWER_IS_BETTER = {"rmse", "mae", "mse", "log_loss"}

STAGES = ["analyze", "plan", "build_baseline", "evaluate", "critique", "improve", "finalize"]


def ensure_dirs() -> None:
    for d in (DATA_DIR, UPLOADS_DIR, ARTIFACTS_DIR, DEMO_DIR):
        d.mkdir(parents=True, exist_ok=True)
