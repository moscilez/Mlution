import time
from alembic.config import Config
from alembic import command
from . import db
from .settings import get_settings


def main():
    for attempt in range(30):
        try:
            db.init_db()
            break
        except Exception:
            if attempt == 29:
                raise RuntimeError("PostgreSQL unavailable after 60 seconds") from None
            time.sleep(2)
    # One backend applies migrations; workers wait on its successful completion.
    command.upgrade(Config("alembic.ini"), "head")
    if get_settings().seed_demo:
        from .seed import main as seed

        seed()


if __name__ == "__main__":
    main()
