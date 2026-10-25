# Backend foundation

Milestone 2 publishes infrastructure and identity/tenant boundaries independently
of the feature APIs. It can migrate a new development database and serve health
checks without starting a frontend, worker, payment integration or mail service.

## Requirements

- Python 3.12 or later (CI uses Python 3.13).
- A virtual environment and access to Python package dependencies.
- SQLite for the default local setup; PostgreSQL is also supported by the driver.

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e './backend[test]'
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[test]'
```

## Configuration and migrations

```bash
python scripts/bootstrap.py
arc-foundation migrate
arc-foundation migration-status
```

Bootstrap creates `.env` with random signing/encryption keys and leaves existing
configuration untouched. The default database is `.local/arc.sqlite`. No provider
credentials are needed for this milestone. Keep `.env` outside version control.

`arc-foundation migrate` uses package-relative migration discovery, so it works
from an editable install or an installed wheel. The frozen revision chain is
`0001_initial` -> `0002_retention_marker` -> `0003_usage_storage`.

The `arc` command delegates to the full platform CLI when that later component
is installed; otherwise it exposes the same commands as `arc-foundation`.

The schema baseline includes tables for later platform domains. Their model
definitions are included to keep migration metadata complete; HTTP routes,
workers and third-party integration implementations remain separate increments.

## Start the health API

```bash
python -m uvicorn entrypoints.foundation_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health/live` | Confirms the process is serving requests |
| `GET /health/ready` | Confirms a database query succeeds |

Responses carry a request reference. Readiness failures return a sanitized
service-unavailable error. This application does not expose customer login,
workspace management, payment or operator routes yet. Stop it with `Ctrl+C`.

## Verification

```bash
python -m pytest -c backend/pyproject.toml backend/foundation_tests -q
```

Tests create temporary SQLite databases and random test keys. They verify fresh
and repeatable migrations, schema/model agreement, workspace isolation, role and
session checks, MFA gates, token validation, password hashing, encryption context
and health behavior. They do not use the developer's database or provider keys.

These are local SQLite and application-policy checks. They do not establish
PostgreSQL row-level security, production load behavior or provider integration
qualification.
