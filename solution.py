"""Organizer contract: python solution.py task.md (Python 3.12)."""
import os
import sys
import time
from pathlib import Path

started_at = time.monotonic()

# Apply limits before importing numerical libraries in either parent or trial process.
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = str(min(8, max(1, int(os.environ.get("MLUTION_CPU_LIMIT", "8")))))
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

if __name__ == "__main__":
    from app.competition.cli import main
    main(started_at=started_at)
