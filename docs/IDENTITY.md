# Customer identity API

Milestone 3a introduces the customer account lifecycle as a standalone API.
It reuses the foundation configuration, schema and authorization rules. It does
not require the frontends, project/job APIs, a worker or an external mail service.

## Install and start

Use the [foundation setup](FOUNDATION.md) to activate a Python environment, then:

```bash
python -m pip install -e './backend[test]'
python scripts/bootstrap.py
arc-foundation migrate
python -m uvicorn entrypoints.identity_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Bootstrap refuses to overwrite an existing `.env`; skip it if already configured.
The API serves the foundation health endpoints plus customer identity endpoints.
Run it instead of the health-only API when using the same port.

## Account lifecycle

All paths below are relative to `/api/console/v1/auth`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/csrf` | Obtain the CSRF cookie and matching token |
| POST | `/signup` | Queue an email verification link |
| POST | `/verify-email` | Consume a single-use verification token |
| POST | `/resend-verification` | Queue another verification message |
| POST | `/login` | Authenticate and establish a customer session |
| GET | `/me` | Inspect the current account and MFA state |
| POST | `/forgot-password` | Queue a single-use password reset link |
| POST | `/reset-password` | Change the password and revoke sessions |
| GET | `/sessions` | List active sessions for the current account |
| DELETE | `/sessions/{session_id}` | Revoke an account-owned session |
| POST | `/logout` | Revoke the current session |
| PATCH | `/preferences` | Update account display and notification preferences |
| POST | `/mfa/setup` | Begin authenticator enrollment |
| POST | `/mfa/confirm` | Confirm enrollment and return one-use recovery codes |

Mutating requests must send the CSRF cookie and a matching `X-CSRF-Token` header.
Tokens are bound to the session, so fetch a new token after login. Browser origins
must match `ARC_PORTAL_ORIGIN` (default `http://127.0.0.1:5173`). Requests without
an Origin header can be made by local API clients with the same CSRF protections.

## Verification without SMTP

The sign-up/reset handlers store encrypted mail in the database. In another
terminal, using the same environment and database:

```bash
arc-identity mail --email developer@example.com
```

The command reads the latest 20 queued messages for that recipient. It is allowed
only in development/test and does not mark an account verified automatically.
Copy the `token` value from the link and send it to `/verify-email` as JSON.
The frontend verification page is a later increment, so opening that link in a
browser requires a separately available frontend.

For example, in a local Python shell:

```python
import httpx
from getpass import getpass

client = httpx.Client(base_url="http://127.0.0.1:8000")
prefix = "/api/console/v1/auth"

def post(path, payload):
    csrf = client.get(prefix + "/csrf").json()["csrf_token"]
    response = client.post(prefix + path, json=payload, headers={"X-CSRF-Token": csrf})
    response.raise_for_status()
    return response.json()

email = "developer@example.com"
password = getpass("Choose a password with at least 12 characters: ")
post("/signup", {"email": email, "name": "Developer", "password": password, "accept_terms": True})
# Run arc-identity mail in another terminal, then copy only the token value.
verification = input("Verification token from the local mailbox: ")
post("/verify-email", {"token": verification})
post("/login", {"email": email, "password": password})
print(client.get(prefix + "/me").json()["user"]["email"])
client.close()
```

MFA enrollment returns an authenticator setup key. Add it to an authenticator and
confirm its current six-digit code. Save the returned recovery codes: each can
be used once. The setup/confirmation endpoints require an authenticated session.

## Verification

```bash
python -m pytest -c backend/pyproject.toml backend/foundation_tests backend/identity_tests -q
```

The integration tests use temporary SQLite databases and generated test keys.
They cover verification/reset token reuse, session revocation, MFA enrollment and
recovery-code reuse, account enumeration responses, CSRF, origin restrictions,
body limits, rate limiting, and sanitized errors. No provider accounts or mail
delivery are used. Production mail delivery and the wider product APIs remain
separate increments.
