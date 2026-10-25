# Approved modular architecture — implemented boundaries

## Composition, domain ownership and interfaces

The backend uses a domain-oriented modular monolith. The entry points are separately
selectable FastAPI applications; business modules live at `backend/modules/<domain>/`,
not in `backend/src`. Code shared by several modules belongs in `backend/foundation/`.

```text
backend/
  entrypoints/
    application.py            # ASGI composition only, no customer domain routes
    customer_api/             # Customer session APIs
    public_data_api/          # Customer application Bearer-token endpoints
    operator_api/             # Internal, MFA-gated operator session APIs
    events_api/               # SSE-only ASGI process
    execution_worker/         # Job processing process
    notification_worker/      # Email/notification process
    webhook_worker/           # Signed delivery process
    retention_worker/         # Storage deletion and expiry
    scheduler/                # Recovery and storage metering
    reconciliation_worker/    # Manual read-only accounting report
    cli/                      # Migrate, bootstrap, manual operations
  modules/                    # 28 independently owned business-context packages
  foundation/                 # Config, IDs, crypto, DB session, safe errors
  database/                   # ORM registry and original Alembic revision history
  src/arc/                    # v0.2 imports compatibility ONLY; not a business-code home
```

Each substantial business module owns its `domain/`, `application/`, `infrastructure/`,
`interfaces/`, `public.py`, and `tests/`. Backend module routers are registered by
surface-specific composition roots; production processes must never enable `surface='all'`.

Domain examples that are genuinely extracted rather than aliases: `payments/domain/checkout_policy.py`,
`payments/application/checkout.py`, `workflows/domain/graph_policy.py`,
`pricing/domain/units.py`, `wallets/application/use_cases.py`.

### Actual cross-module contract and persistence rules

- No module may depend on a different domain's private `infrastructure` package.
- A shared FastAPI DB-session dependency lives in `foundation/database/dependencies.py`.
- Database models belong to modules and are registered centrally for Alembic.
- Existing table/column names and migration revision identifiers are unchanged.
- HTTP request/response schemas are owned by their modules and assembled by entry points.
- Role, environment and tenant checks are required in every query path, even when a UI
  action is hidden. Public error messages are allowlisted and referenced by request ID.
- Shared credit transactions and job admission stay within PostgreSQL ACID boundaries;
  Stripe/R2/notifications are external effects managed through service adapters.
- SSE has an event-only surface with no billing, staff or customer management routes.
- C++ computation is a reusable `arc-native-core` library plus a small binary entrypoint.

## Database and migrations

No database changes are required for this *structural* release. The original 36
business tables are loaded from domain-owned models by `database/metadata_registry.py`.
The frozen `0001_initial` → `0003_usage_storage` revision chain remains the same.

Run `arc migrate` with the SAME `ARC_ENCRYPTION_KEY` and `ARC_SECRET_KEY` used previously,
after taking a complete backup. Never run `metadata.create_all` against a production DB.

## Surface routing

| Surface | What it exposes | Must not expose |
|---|---|---|
| customer | Signup/session, workspace, projects, customer management, billing | Staff operations |
| data | Public API, Bearer token data operations, Stripe callbacks | Customer/staff sessions |
| operator | Staff session, staff resource operations | Customer console APIs |
| events | Two authenticated job-event streams and health | Payment, staff, customer control routes |
| all | Local-development convenience only | Blocked by production Settings |

Health endpoints are available for load balancer/readiness checks. Envoy routes should
point public `v1` data traffic to the data pool, and long-lived SSE to the events pool.

## Integration debt (not concealed)

This is a **behavior-preserving modular refactor**, not a complete rewrite into
one-use-case-per-route. Some module-owned routers still execute SQLAlchemy queries directly
and some application services still reference other modules' exported ORM models. They
can be narrowed to command/query ports incrementally, protected by contract and billing
regressions. Empty `domain/` and `tests/` packages mark ownership but do NOT mean a
business module has already been fully implemented.

Production qualification is separate: PostgreSQL RLS, native seccomp/network isolation,
real R2 and Stripe integration, frontend dependency-backed builds and browser tests,
queue fairness, operational load tests, legal/pricing review, and restore drills remain
release blockers. Don't enable paid public traffic based on local test results alone.
