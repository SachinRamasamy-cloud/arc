from types import SimpleNamespace

import pytest

from foundation.clock import now
from foundation.crypto.security import digest, password_hash, token
from foundation.errors.public import PublicError
from modules.authorization.application.access import current_user, require_live, workspace_access
from modules.identity.public import LoginSession, User
from modules.tenancy.public import Membership, Workspace


def seed_identity(database, *, role="viewer", audience="console", mfa=False, staff=False, expires=None):
    raw = token()
    with database.session() as session:
        user = User(email="member@example.test", name="Member", password_hash=password_hash("test-passphrase-only"), verified=True, staff=staff)
        workspace = Workspace(name="Owned workspace")
        foreign = Workspace(name="Other workspace")
        session.add_all([user, workspace, foreign])
        session.flush()
        session.add(Membership(workspace_id=workspace.id, user_id=user.id, role=role))
        session.add(LoginSession(id=digest(raw), user_id=user.id, audience=audience, mfa=mfa, expires_at=expires if expires is not None else now() + 3600))
        session.commit()
        return user.id, workspace.id, foreign.id, raw


def request_for(settings, raw, audience="console"):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)), cookies={settings.cookie(audience): raw})


def test_members_cannot_discover_other_workspaces(database, settings):
    user_id, workspace_id, foreign_id, raw = seed_identity(database)
    with database.session() as session:
        user, _ = current_user(request_for(settings, raw), session)
        assert user.id == user_id
        assert workspace_access(session, workspace_id, user)[0].id == workspace_id
        with pytest.raises(PublicError) as denied:
            workspace_access(session, foreign_id, user)
        assert denied.value.code == "NOT_FOUND"


def test_viewer_cannot_manage_finance(database, settings):
    _, workspace_id, _, raw = seed_identity(database)
    with database.session() as session:
        user, _ = current_user(request_for(settings, raw), session)
        with pytest.raises(PublicError) as denied:
            workspace_access(session, workspace_id, user, "finance")
        assert denied.value.code == "FORBIDDEN"


@pytest.mark.parametrize("audience,expires", [("console", 0), ("operator", None)])
def test_expired_or_wrong_audience_session_is_rejected(database, settings, audience, expires):
    _, _, _, raw = seed_identity(database, audience=audience, mfa=True, staff=True, expires=expires)
    with database.session() as session:
        with pytest.raises(PublicError) as denied:
            current_user(request_for(settings, raw), session)
        assert denied.value.code == "UNAUTHORIZED"


def test_operator_session_requires_staff_and_mfa(database, settings):
    _, _, _, raw = seed_identity(database, audience="operator", staff=True, mfa=False)
    with database.session() as session:
        with pytest.raises(PublicError) as denied:
            current_user(request_for(settings, raw, "operator"), session, "operator")
        assert denied.value.code == "FORBIDDEN"


@pytest.mark.parametrize("enrolled,mfa", [(False, False), (False, True), (True, False)])
def test_live_access_requires_enrollment_and_verified_session(settings, enrolled, mfa):
    settings.live_enabled = True
    user = SimpleNamespace(totp_secret="enrolled" if enrolled else None)
    session = SimpleNamespace(mfa=mfa)
    with pytest.raises(PublicError) as denied:
        require_live(settings, user, session)
    assert denied.value.code == "MFA_REQUIRED"
    user.totp_secret = "enrolled"
    session.mfa = True
    require_live(settings, user, session)
