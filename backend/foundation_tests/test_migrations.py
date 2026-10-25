from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from database.metadata_registry import Base
from entrypoints.foundation_cli import main, migration_config


def configure_environment(monkeypatch, settings):
    for name in ("env", "database_url", "secret_key", "encryption_key"):
        monkeypatch.setenv("ARC_" + name.upper(), getattr(settings, name))


def test_fresh_migrations_match_models_and_repeat_safely(monkeypatch, settings):
    configure_environment(monkeypatch, settings)
    main(["migrate"])
    main(["migrate"])
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003_usage_storage"
        assert {"users", "sessions", "workspaces", "memberships"} <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_empty_database_can_upgrade_from_previous_revision(monkeypatch, settings):
    configure_environment(monkeypatch, settings)
    config = migration_config()
    command.upgrade(config, "0002_retention_marker")
    command.upgrade(config, "head")
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    finally:
        engine.dispose()
