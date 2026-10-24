"""Run this with the exact organizer subset installed, without any web dependencies."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def materials(root, classification):
    root.mkdir()
    rng = np.random.default_rng(91)
    values = rng.normal(size=180)
    train = pd.DataFrame({"record_key": [f"{i:05}" for i in range(180)], "measurement": values, "type": np.where(values > 0, "high", "low")})
    target = "unseen_label" if classification else "unseen_value"
    train[target] = np.where(values > .4, "01", np.where(values < -.4, "02", "03")) if classification else values * 4 + rng.normal(0, .05, len(values))
    test = train.drop(columns=target).iloc[:23].copy()
    test["record_key"] = [f"{i + 800:05}" for i in range(len(test))]
    train.to_csv(root / "train.csv", index=False)
    test.to_csv(root / "test.csv", index=False)
    pd.DataFrame({"record_key": test.record_key.iloc[::-1], target: 0}).to_csv(root / "sample_submission.csv", index=False)
    pd.DataFrame({"feature": train.columns, "role": ["id", "feature", "feature", "target"]}).to_csv(root / "data_dictionary.csv", index=False)
    path = root / "task.md"
    path.write_text("Read the task. RMSE is not our goal.\nMetric: Macro F1\nWrite predictions.csv" if classification else "Metric: RMSE\nWrite predictions.csv", encoding="utf-8")
    return path, target


@pytest.mark.parametrize("classification", [False, True])
def test_portable_zip_entrypoint(tmp_path, classification):
    spec = importlib.util.spec_from_file_location("packager", ROOT / "competition/package_solution.py")
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    archive_path = packager.package(tmp_path / "solution.zip")
    code = tmp_path / "source"
    with ZipFile(archive_path) as archive:
        assert "solution.py" in archive.namelist()
        assert not any(".env" in name or "data/" in name or "web.py" in name for name in archive.namelist())
        archive.extractall(code)
    task, target = materials(tmp_path / "task", classification)
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("OPENAI_", "LLM_", "DATABASE_", "REDIS_"))}
    result = subprocess.run([sys.executable, str(code / "solution.py"), str(task), "--offline", "--time-budget", "60", "--max-experiments", "3", "--trial-timeout", "20", "--threads", "1"], env=environment, cwd=tmp_path, text=True, capture_output=True, timeout=80)
    assert result.returncode == 0, result.stderr + result.stdout
    predicted = pd.read_csv(task.parent / "predictions.csv", dtype=str)
    expected = pd.read_csv(task.parent / "sample_submission.csv", dtype=str)
    assert list(predicted) == list(expected)
    assert predicted.record_key.tolist() == expected.record_key.tolist()
    if classification:
        assert set(predicted[target]) <= {"01", "02", "03"}
    else:
        assert np.isfinite(predicted[target].astype(float)).all()
    report = json.loads((task.parent / "research.json").read_text())
    assert report["profile"]["metric"] == ("f1_macro" if classification else "rmse")
    assert report["best"]["status"] == "completed"
    assert any(not item["dummy"] and item["status"] == "completed" for item in report["experiments"])
