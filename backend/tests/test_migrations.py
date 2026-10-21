from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.db import Base

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def test_migrations_match_models(tmp_path):
    # The API tests build tables straight from the models, so this is what
    # catches a model change that nobody wrote a migration for.
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []


def test_migrations_downgrade_cleanly(tmp_path):
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migrated.db'}")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
