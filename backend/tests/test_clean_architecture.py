"""Pin architecture boundaries and externally visible paths during v0.2 migration."""
import secrets
from collections import Counter
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from foundation.config.settings import Settings
from entrypoints.application import create_app
from foundation.database.base import Base
from database import metadata_registry  # noqa: F401 - registers module ORM tables
# pytest's standalone executable does not always prepend the project root.
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.verify_architecture import inspect_architecture

def settings():
    return Settings(_env_file=None,env='test',secret_key=secrets.token_urlsafe(48),encryption_key=Fernet.generate_key().decode())

def routes(app):
    return {(route.path,method) for route in app.routes for method in getattr(route,'methods',[]) if method not in ('HEAD','OPTIONS')}

def test_architecture_guard():
    assert inspect_architecture()==[]

def test_metadata_table_names_preserved():
    expected={'action_tokens','allowances','api_keys','audit_events','credit_allocations','credit_ledger','customer_records','files','invoices','jobs','mail_outbox','memberships','multipart_uploads','mutation_receipts','notifications','payments','plan_prices','privacy_requests','projects','request_logs','run_events','sessions','storage_intervals','storage_statements','stripe_events','support_tickets','usage_counters','usage_events','usage_prices','users','wallets','webhook_deliveries','webhook_endpoints','workflow_versions','workflows','workspaces'}
    assert set(Base.metadata.tables)==expected

def test_route_surface_isolation_and_unique_paths():
    authorization=settings()
    surfaces={name:create_app(settings=authorization,surface=name) for name in ('all','console','data','operator','events')}
    paths={name:routes(app) for name,app in surfaces.items()}
    for app in surfaces.values():
        rows=[(route.path,method) for route in app.routes for method in getattr(route,'methods',[]) if method not in ('HEAD','OPTIONS')]
        assert not [name for name,count in Counter(rows).items() if count>1]
    assert ('/api/console/v1/projects/{pid}/jobs/{jid}/events','GET') in paths['events']
    assert ('/v1/jobs/{jid}/events','GET') in paths['events']
    assert paths['events']=={('/api/console/v1/projects/{pid}/jobs/{jid}/events','GET'),('/v1/jobs/{jid}/events','GET'),('/health/live','GET'),('/health/ready','GET')}
    assert not any(url.startswith('/api/operator/') for url,_ in paths['console'])
    assert not any(url.startswith('/api/console/') for url,_ in paths['operator'])
    assert not any(url.startswith('/api/console/') for url,_ in paths['data'])
    assert paths['events'] <= paths['all']

def test_events_reject_unknown_jobs_without_exposing_staff_routes():
    app=create_app(settings=settings(),surface='events')
    with TestClient(app,raise_server_exceptions=False) as client:
        assert client.get('/health/live').status_code==200
        assert client.get('/api/operator/v1/customers').status_code==404
        assert client.get('/api/console/v1/workspaces').status_code==404
        response=client.get('/v1/jobs/missing/events')
        assert response.status_code in (401,403,404)
        assert 'traceback' not in response.text.lower()
