"""Isolated foundation fixtures; never use developer or provider credentials."""
import secrets

import pytest
from cryptography.fernet import Fernet

from database.metadata_registry import Base  # Register every migration-owned model.
from foundation.config.settings import Settings
from foundation.database.session import Database


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        env="test",
        database_url="sqlite:///" + str(tmp_path / "foundation.sqlite"),
        secret_key=secrets.token_urlsafe(48),
        encryption_key=Fernet.generate_key().decode(),
    )


@pytest.fixture
def database(settings):
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    yield database
    database.engine.dispose()
