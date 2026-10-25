import pytest

from entrypoints.identity_cli import main as identity_command
from foundation.crypto.security import totp_code

from .conftest import PASSWORD, PREFIX, call, mail_token, signup, verified_login


def test_signup_requires_verification_and_link_is_single_use(ctx):
    signup(ctx)
    client = ctx["client"]
    denied = call(client, "POST", "/login", json={"email": "member@example.com", "password": PASSWORD})
    assert denied.json()["code"] == "EMAIL_UNVERIFIED"
    verification = mail_token(ctx, "Verify your Arc account")
    assert call(client, "POST", "/verify-email", json={"token": verification}).status_code == 200
    assert call(client, "POST", "/verify-email", json={"token": verification}).json()["code"] == "INVALID_TOKEN"
    assert call(client, "POST", "/login", json={"email": "member@example.com", "password": PASSWORD}).status_code == 200
    assert client.get(PREFIX + "/me").json()["user"]["verified"]


def test_password_reset_revokes_sessions_and_rejects_reuse(ctx):
    client = verified_login(ctx)
    assert call(client, "POST", "/forgot-password", json={"email": "member@example.com"}).status_code == 202
    reset = mail_token(ctx, "Reset your password")
    new_password = "changed-test-passphrase-456"
    assert call(client, "POST", "/reset-password", json={"token": reset, "password": new_password}).status_code == 200
    assert client.get(PREFIX + "/me").status_code == 401
    assert call(client, "POST", "/reset-password", json={"token": reset, "password": new_password}).status_code == 400
    assert call(client, "POST", "/login", json={"email": "member@example.com", "password": PASSWORD}).status_code == 401
    assert call(client, "POST", "/login", json={"email": "member@example.com", "password": new_password}).status_code == 200


def test_signup_and_reset_responses_do_not_disclose_account_existence(ctx):
    signup(ctx)
    client = ctx["client"]
    existing = call(client, "POST", "/signup", json={"email": "member@example.com", "name": "Other", "password": PASSWORD, "accept_terms": True})
    assert existing.json() == {"message": "Check your email for the next step."}
    known = call(client, "POST", "/forgot-password", json={"email": "member@example.com"})
    unknown = call(client, "POST", "/forgot-password", json={"email": "absent@example.com"})
    assert known.json() == unknown.json()


def test_authenticator_enrollment_and_recovery_code_single_use(ctx):
    client = verified_login(ctx)
    setup = call(client, "POST", "/mfa/setup").json()
    assert "secret" in setup
    confirmation = call(client, "POST", "/mfa/confirm", json={"code": totp_code(setup["secret"])})
    assert confirmation.status_code == 200
    recovery = confirmation.json()["recovery_codes"][0]
    assert client.get(PREFIX + "/me").json()["mfa_verified"]
    assert call(client, "POST", "/logout").status_code == 200
    credentials = {"email": "member@example.com", "password": PASSWORD}
    assert call(client, "POST", "/login", json=credentials).json()["code"] == "MFA_REQUIRED"
    assert call(client, "POST", "/login", json={**credentials, "code": recovery}).status_code == 200
    assert call(client, "POST", "/logout").status_code == 200
    assert call(client, "POST", "/login", json={**credentials, "code": recovery}).json()["code"] == "INVALID_CODE"


def test_logout_revokes_current_session(ctx):
    client = verified_login(ctx)
    assert len(client.get(PREFIX + "/sessions").json()["items"]) == 1
    assert call(client, "POST", "/logout").status_code == 200
    assert client.get(PREFIX + "/me").status_code == 401


def test_queued_mail_is_readable_without_smtp(ctx, capsys):
    signup(ctx)
    expected = mail_token(ctx, "Verify your Arc account")
    identity_command(["mail", "--email", "member@example.com"], settings=ctx["settings"])
    assert expected in capsys.readouterr().out


def test_local_mail_command_is_blocked_in_production(ctx):
    settings = ctx["settings"].model_copy(update={"env": "production"})
    with pytest.raises(SystemExit, match="only in development or test"):
        identity_command(["mail", "--email", "member@example.com"], settings=settings)


def test_preferences_validate_timezone(ctx):
    client = verified_login(ctx)
    good = call(client, "PATCH", "/preferences", json={"timezone": "Asia/Kolkata", "compact": True})
    assert good.status_code == 200
    assert client.get(PREFIX + "/me").json()["user"]["preferences"]["compact"] is True
    assert call(client, "PATCH", "/preferences", json={"timezone": "invalid/private-path"}).status_code == 422
