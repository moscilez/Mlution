"""Seed script: generates the demo churn CSV and creates a demo project.

Run:  python -m app.seed
"""

import pandas as pd
import os
import secrets
from sqlalchemy import select
from argon2 import PasswordHasher

from . import db
from . import models as m
from .settings import get_settings
from .agents.data_analyst import profile_dataframe
from .config import DEMO_CSV, ensure_dirs
from .demo_data import generate_demo_csv


def main() -> None:
    if not get_settings().demo_enabled or get_settings().environment == "production":
        raise RuntimeError("Seed is only available when development demo mode is enabled")
    ensure_dirs()
    db.init_db()
    if not DEMO_CSV.exists():
        generate_demo_csv(DEMO_CSV)
        print(f"Demo dataset generated: {DEMO_CSV}")
    password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(18)
    with db.SessionLocal.begin() as s:
        user = s.scalar(select(m.User).where(m.User.email == "demo@mlution.local"))
        if user is None:
            user = m.User(email="demo@mlution.local", password_hash=PasswordHasher().hash(password))
            s.add(user)
            s.flush()
            print(f"Development-only demo login: demo@mlution.local / {password}")
        owner_id = user.id
    projects = db.list_projects(owner_id)
    if projects:
        print(f"Demo project already exists: {projects[0]['id']}")
        return
    project = db.create_project(
        "Telco Churn (Demo)",
        "Predict customer churn from subscription and usage data. Business priority: catch as many churners as possible.",
        owner_id,
    )
    df = pd.read_csv(DEMO_CSV)
    profile = profile_dataframe(df)
    db.update_project(
        project["id"],
        dataset_name="churn_demo.csv",
        dataset_path=str(DEMO_CSV),
        profile_json=profile.model_dump(),
    )
    print(
        f"Demo project created: id={project['id']} (rows={profile.n_rows}, target hint={profile.target_column})"
    )


if __name__ == "__main__":
    main()
