"""Package only portable competition source; never include credentials or task data."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("__init__.py", "cli.py", "data.py", "engine.py", "features.py", "planner.py", "plans.py", "scoring.py", "trial.py")


def package(destination: Path):
    sources = {"solution.py": ROOT / "solution.py", "backend/app/__init__.py": ROOT / "backend/app/__init__.py", "requirements.txt": ROOT / "competition/requirements-runtime.txt", "README.md": ROOT / "competition/README.md"}
    sources.update({f"backend/app/competition/{name}": ROOT / "backend/app/competition" / name for name in MODULES})
    destination = destination.resolve()
    if destination.suffix != ".zip" or not destination.is_relative_to(ROOT):
        raise ValueError("Output must be a ZIP inside the project")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()}
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, path in sources.items():
            archive.write(path, name)
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "output/competition/mlution-solution.zip")
    print(package(parser.parse_args().output))
