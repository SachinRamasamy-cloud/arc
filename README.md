# Arc v0.3 — Modular API Platform

This repository contains a **development implementation** of a first-party API
provider with a black/silver React/Three.js public website, separate customer
and staff applications, FastAPI backend, native C++ processing, files, credit
ledger, Stripe adapters, and customer APIs. **Not production qualified.**

## Source ownership

```text
apps/
  website/                 Next.js public website, GLB and docs
  customer-portal/         React+Vite application, 24 feature modules
  operator-console/        Independent React+Vite staff-only application
packages/                  Shared UI/client/contract libraries (no business ownership)
backend/
  entrypoints/             Customer/data/operator/events API factories and workers
  modules/                 28 separate business domains with layered ownership
  foundation/              Cross-domain configuration, crypto, HTTP, database session
  database/                Original Alembic revisions + 36-table registry
  src/arc/                 Compatibility aliases only; DO NOT add new business logic
native/
  include/arc/             Public native library contracts
  engines/validation/      JSON/CSV input and export validation
  engines/transformation/  Normalize and approved transforms
  worker/                  Small native executable
  tests/                   Native regression tests
sdk/                       Server-side Python and TypeScript clients
infra/                     Envoy, Docker and local qualification stack
tests/                     Browser and cross-module test definitions
docs/architecture/         Module ownership and cross-application restrictions
```

[Detailed backend structure](docs/architecture/MODULAR_BACKEND.md) ·
[Frontend structure](docs/architecture/FRONTEND_BOUNDARIES.md) ·
[Upgrade from v0.2](docs/MIGRATE_V0_2_TO_V0_3.md) ·
[Release gates](docs/RELEASE.md)

## Local prerequisites

Python 3.13 (3.12 supported), Node.js 22+, CMake 3.20+, C++20 compiler and Boost
JSON development headers. Install Python dependencies in your own environment.
No admin/password or live payment account is bundled.

```bash
python -m pip install -e './backend[test]'
python scripts/bootstrap.py                # fresh local .env only; preserves existing
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build -j2
ctest --test-dir native/build --output-on-failure
arc migrate
npm install                                 # only after dependency access + review
python scripts/dev.py
```

The dev launcher starts the website (`:3000`), customer portal (`:5173`), operator
(`:5174`), a combined development API (`:8000`), and the combined local worker.
Production must deploy separate ASGI surfaces and dedicated workers instead.

## Run acceptance checks

```bash
python scripts/verify_architecture.py
pytest -q backend/tests backend/modules
ctest --test-dir native/build --output-on-failure
node scripts/check_frontend.cjs
node scripts/test_frontend_logic.cjs
node scripts/test_billing_uploads.cjs
python scripts/release_check.py            # expected to BLOCK deployment
```

React dependency-backed builds and Playwright browser tests were not run here:
package installation wasn't available and there is no reviewed npm lockfile.
The modular Python tests were executed in three independent groups because the
single large job exceeded execution time limits. See `docs/VALIDATION_V0_3.md`.

## What exists versus what does not

**Exists:** first-party JSON/CSV validation and native conversion, scoped keys,
projects, uploads/storage adapters, workflows, replayable job events, credits,
usage metering, subscription/payment adapters, notification inbox, basic admin
operations and a real GLB landing asset.

**Not qualified/completed:** actual Stripe/R2 paid operations in staging,
PostgreSQL production load/RLS, seccomp worker isolation, frontend/browser
qualification, general app-auth, WhatsApp/automation, unlimited/binary file
processing, complex multi-tenant service hosting or production SLAs.

Do not advertise a roadmap API product as live without contract and runtime tests.
Do not enable `ARC_LIVE_ENABLED` without documented release evidence.


### v0.3.3 UX changes

See `docs/UX_SERVICES_DOCS_v0_3_3.md`, `docs/UPGRADE_v0_3_2_to_v0_3_3.md` and `VALIDATION_v0_3_3.md`. `/docs` is available from the portal and from the public API; it exposes only first-party consumer operations. All service categories appear in the catalog with accurate availability labels.
