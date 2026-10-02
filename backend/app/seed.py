"""Seed script: generates the demo churn CSV and creates a demo project.

Run:  python -m app.seed
"""
import pandas as pd

from . import db
from .agents.data_analyst import profile_dataframe
from .config import DEMO_CSV, ensure_dirs
from .demo_data import generate_demo_csv


def main() -> None:
    ensure_dirs()
    db.init_db()
    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
        print(f"Demo dataset generated: {DEMO_CSV}")
    project = db.create_project(
        "Telco Churn (Demo)",
        "Predict customer churn from subscription and usage data. Business priority: catch as many churners as possible.",
    )
    df = pd.read_csv(DEMO_CSV)
    profile = profile_dataframe(df)
    db.update_project(
        project["id"],
        dataset_name="churn_demo.csv",
        dataset_path=str(DEMO_CSV),
        profile_json=profile.model_dump(),
    )
    print(f"Demo project created: id={project['id']} (rows={profile.n_rows}, target hint={profile.target_column})")


if __name__ == "__main__":
    main()
