# Modular Refactor v0.3 — Delivery Notes

**Source:** `API_Provider_Modular_Clean_Architecture_v0_3.zip` (full replacement package)

The existing first-party API provider was refactored into 28 domain-owned backend
modules; domain-level models, HTTP routers, public facades, application operations,
source-level dependency checks and module tests. Customer and operator React apps
now have separate per-feature pages and independent styles. The native engine
is a reusable C++ core library with separate JSON/CSV validation, normalization,
processing protocol and worker executable. The old imports are retained as thin
compatibility aliases, not as duplicate business implementations.

**Verified:** 121/121 routes, 36/36 ORM metadata structures unchanged;
158 Python tests, 2 C++ tests, 21 frontend logic tests, 59 source file checks.
Fresh Alembic migration completed. Release readiness remains correctly blocked.

**Not verified:** full frontend builds/Playwright/3D rendering, real Stripe/R2
accounts, deployment under load, PostgreSQL RLS, production sandbox and restore
qualification. Do not enable public paid traffic without these.

Upgrade safely: back up the DB and objects, stop workers, extract the complete
ZIP to a NEW directory, retain existing secrets, compile C++, run `arc migrate`,
install reviewed npm dependencies, test on staging and switch API instances
without changing prior financial ledger references. See
`docs/MIGRATE_V0_2_TO_V0_3.md` for detailed steps.
