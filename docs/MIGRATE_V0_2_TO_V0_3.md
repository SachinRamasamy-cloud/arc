# v0.2 → v0.3 clean-architecture source migration

**This is a code and package layout upgrade, not a schema/data conversion.**

1. Back up the PostgreSQL/SQLite database, private R2 objects, and your current
   `.env`/secret-manager configuration. Store backups outside the source tree.
2. Stop API traffic and workers, then drain any active jobs and SSE connections.
3. Extract the **complete** v0.3 archive into a new deployment directory; do not copy
   `backend/modules` on top of v0.2 while leaving old Python bytecode/imports loaded.
4. Keep existing `ARC_SECRET_KEY`, `ARC_ENCRYPTION_KEY`, Stripe webhook secret, and
   storage credentials. Rotating them unintentionally can invalidate stored ciphertext
   and sessions. Never copy the test fixtures or `.env.example` over real credentials.
5. Rebuild the C++ engine (`cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release`,
   then `cmake --build native/build -j2`). The old binary was not included in the ZIP.
6. Install Python (`python -m pip install -e './backend[test]'`) and `arc migrate`.
   This runs the original Alembic revision chain; it must remain at
   `0003_usage_storage` for an already upgraded v0.2 database.
7. Install reviewed frontend dependencies. Generate/review/commit an npm lockfile;
   use `npm ci` in CI and deployments after that review.
8. Run `python scripts/verify_architecture.py`, backend tests, native CTest and
   frontend build/typecheck/browser tests. Verify authenticated HTTP, payment
   accounting, file sealing and SSE on your staging deployment.
9. Start separate `entrypoints.application:console`, `:data`, `:operator`, and
   `entrypoints.events_api.main:events` factories with `--factory`. Run dedicated
   worker entrypoints as required; `arc worker` remains the combined LOCAL dev worker.
10. Monitor reconciliation, request errors and old in-flight jobs before routing
    all traffic. Have a rollback that preserves database state and restores the
    previous app binary; do not automatically downgrade migrations.

## Compatibility

`backend/src/arc/*.py` now consists of backwards-compatible import facades only.
The old tables, customer and operator endpoints, billing ledger references,
and Stripe idempotency keys retain their original identities. No credits are
reissued during migration. The new table owner modules share one Alembic history.

## Remaining production blockers

The package release checker intentionally remains FAIL/CLOSED until Stripe, R2,
PostgreSQL/Redis, backups, RLS, native sandboxing, pricing/legal review,
frontend browser qualification, concurrency/load and independent security checks
have verifiable evidence. See `docs/RELEASE.md`.
