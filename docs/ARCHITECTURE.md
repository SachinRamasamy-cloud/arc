# Runtime and data ownership

## Surfaces

`apps/website` is prerendered public content and the interactive 3D demo. `apps/customer-portal` is the customer application. `apps/operator-console` is a separate staff application. Only UI styling/components and typed client infrastructure are shared; customer data permissions do not become staff permissions.

The backend exposes `arc.main:console`, `arc.main:data` and `arc.main:operator` factories. The combined `arc.main:development` factory is explicitly prohibited in production. An event pool can use the data factory behind an SSE-only proxy route; a separate dedicated event-only ASGI app is not delivered.

## Source map

| Source | Responsibility |
|---|---|
| `config.py`, `main.py`, `errors.py` | Validated config, ASGI surfaces, safe errors/headers/origins/body limits |
| `auth_routes.py`, `security.py`, `access.py` | Account flows, tokens, MFA, CSRF, scopes, tenant/role permissions |
| `models.py`, `db.py`, `alembic/` | 25 authoritative tables, transactional constraints, migrations |
| `routes.py`, `operator_routes.py`, `data_routes.py` | Customer control, staff control and public product APIs |
| `services.py` | Approved capabilities, graph compiler, quotes, admission, settlement and notifications |
| `worker.py`, `native.py`, `sandbox_exec.py` | Durable claims, execution, fencing, resource-limited child process |
| `storage.py` | Local/R2 private objects, signed capabilities and verified upload lifecycle |
| `streams.py`, `limits.py` | Replayable SSE, stream capacity and atomic rate admission |
| `payments.py` | Stripe calls, raw-body signature verification and financial event effects |
| `deliveries.py` | Mail/webhook dispatch, reminders and retention cleanup |
| `cli.py` | Migration, worker, local mail and explicit account creation |

## One complete processing request

1. Resolve the session or scoped API key, workspace, project and environment.
2. Validate the payload and approved operation; calculate the development quote.
3. Check the idempotency key and fingerprint. Reusing a key for different input is a conflict.
4. Enforce limits and serialize the workspace's durable admission decision.
5. Reserve included allowance, then any remaining amount from paid/test credits; create the job and event.
6. A worker claims the queued row with a fenced lease and launches the approved C++ executable without shell expansion.
7. C++ returns bounded structured output. Failure messages are translated to public codes; stderr is not exposed.
8. Under a durable transaction, verify the fence, settle or release the reservation, commit the terminal state and enqueue notifications.
9. The portal or customer reads the result, follows SSE, or receives a signed webhook. SSE delivery can repeat; consumers deduplicate IDs.

An internal retry does not create another billable logical operation. Changing a quote formula requires a versioned commercial pricing rollout before live use; the development fixture is intentionally not represented as final commercial metering.

## Uploads

The customer backend authorizes an upload; the browser PUTs to the returned signed URL. Hosted R2 bypasses FastAPI for bytes. Local mode uses a signed local upload endpoint solely for development. A completion call verifies actual length and UTF-8/JSON content, writes a fresh canonical private object, commits the pointer, then removes staging. A still-valid staging URL cannot replace the verified input.

The worker fetches and hashes the verified object before processing. Ordinary cloud processing uses plaintext inside the authorized runtime. Direct upload is not zero-knowledge computation. There is no arbitrary URL fetch or access to the customer's database.

## Financial boundary

Stripe collects payment. PostgreSQL owns internal credits and usage. Browser redirects are not payment evidence. Checkout inputs are server-selected; raw webhook signatures, account mode, reference, currency and amount are checked. The customer link is persisted before creating a Checkout Session. Grants are unique per logical payment, and subscription allowance is unique per subscription period. Proration invoices do not mint another full allowance.

A refund/dispute freezes further paid work for review; an audited automated reversal is not implemented. Scheduled reconciliation and provider end-to-end validation remain release blockers.

## Storage and retention

PostgreSQL: accounts, permissions, jobs, bounded input/output, logs, credits and events. R2: private verified input objects. Redis: limiter/stream leases when configured. Local disk: development objects/mail. The worker uses its own temporary directory and resource limits.

Verified input files expire after 24 hours. Abandoned upload rows expire after one hour. Terminal job payloads follow `project.retention_hours` and record an erasure marker; metadata/usage remain. These active-store actions are not equivalent to backup deletion. General storage and large result vaults are not yet commercial products.

## Frontend state

TanStack Query owns server-state caches; edits use local React state. Mutations are not silently replayed. Scope changes remount scoped screens. SSE only updates confirmed state and invalidates relevant queries. UI counters derive from actual data; illustrative landing diagrams are labelled.

## GLB

`arc-assembly.glb` is original geometry generated by `scripts/generate_model.py`. A reusable layered silver assembly represents input, authorization, processing, results and events. The scene has no network-loaded textures. Motion pauses on reduced-motion preference, hidden document or offscreen canvas. Stage buttons provide a non-pointer alternative; WebGL failure falls back to CSS geometry and text.
