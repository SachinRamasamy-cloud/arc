import re
import secrets

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from database.metadata_registry import Base
from entrypoints.identity_api.main import create_app
from foundation.config.settings import Settings
from foundation.crypto.security import unseal
from foundation.database.session import Database
from modules.notifications.public import Mail

PREFIX = "/api/console/v1/auth"
PASSWORD = "identity-test-passphrase-123"


@pytest.fixture
def ctx(tmp_path):
    settings = Settings(_env_file=None, env="test", database_url="sqlite:///" + str(tmp_path / "identity.sqlite"), secret_key=secrets.token_urlsafe(48), encryption_key=Fernet.generate_key().decode())
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    with TestClient(create_app(settings, database)) as client:
        yield {"settings": settings, "database": database, "client": client}
    database.engine.dispose()


def call(client, method, path, **kwargs):
    csrf = client.get(PREFIX + "/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf, **kwargs.pop("headers", {})}
    return client.request(method, PREFIX + path, headers=headers, **kwargs)


def mail_token(ctx, subject, email="member@example.com"):
    with ctx["database"].session() as session:
        message = session.scalar(select(Mail).where(Mail.recipient == email, Mail.subject == subject).order_by(Mail.created_at.desc()))
        assert message is not None
        return re.search(r"token=([A-Za-z0-9_-]+)", unseal(message.body_encrypted, ctx["settings"], "mail")).group(1)


def signup(ctx, email="member@example.com"):
    response = call(ctx["client"], "POST", "/signup", json={"email": email, "name": "Member", "password": PASSWORD, "accept_terms": True})
    assert response.status_code == 202, response.text


def verified_login(ctx):
    signup(ctx)
    client = ctx["client"]
    verification = mail_token(ctx, "Verify your Arc account")
    assert call(client, "POST", "/verify-email", json={"token": verification}).status_code == 200
    assert call(client, "POST", "/login", json={"email": "member@example.com", "password": PASSWORD}).status_code == 200
    return client
