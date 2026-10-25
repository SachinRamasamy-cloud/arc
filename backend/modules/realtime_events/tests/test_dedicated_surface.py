import secrets
from cryptography.fernet import Fernet
from foundation.config.settings import Settings
from entrypoints.application import create_app

def test_events_surface_contains_only_event_routes_and_health():
    settings=Settings(_env_file=None,env='test',secret_key=secrets.token_urlsafe(48),encryption_key=Fernet.generate_key().decode())
    app=create_app(settings=settings,surface='events')
    paths={r.path for r in app.routes}
    assert '/v1/jobs/{jid}/events' in paths
    assert '/api/operator/v1/auth/login' not in paths
    assert '/api/payments/stripe/webhook' not in paths
