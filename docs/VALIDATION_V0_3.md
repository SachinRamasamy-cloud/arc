# v0.3 Clean Architecture implementation — executed checks

**Status: local modular-refactor parity verified; release blocked.**

## Source parity with v0.2

- Parsed the original v0.2 archive in an isolated Python process and compared
  against v0.3. **121/121 API method+path pairs unchanged.** No removed/added
  endpoints and no duplicate route registrations.
- Compared all SQLAlchemy table metadata: **36/36 tables, columns, index definitions,
  and foreign-key relationships unchanged.**
- Fresh `arc migrate` generated the original `0003_usage_storage` revision and 36
  business tables; no new migration history or live data migration was required.
- The backend import boundary checker found **zero cross-domain private infrastructure
  imports**, and the dedicated event API exposed only two streams and health routes.

## Executed test results

| Suite | Result | Evidence |
|---|---:|---|
| Python backend group A | 77 passed | `artifacts/backend-full-tests.txt` |
| Python backend group B | 36 passed | same |
| Python backend group C (including domain tests) | 45 passed | same |
| **Python total** | **158 passed** | three mutually exclusive suites |
| Native CTest version/core operations | 2 passed | `artifacts/native-ctest.txt` |
| Frontend/SDK/billing/upload logic | 21 passed | `artifacts/frontend-logic-tests.txt` |
| TS syntax/local imports | 59 source files, no errors | `artifacts/frontend-syntax.json` |
| Architecture static check | 28 domains, 0 violations | `artifacts/architecture-check.json` |
| Release readiness | **blocked, intentionally** | `artifacts/release-check.json` |

The complete backend run in one execution exceeded the container's execution
window. The **same test collection** was then run in three disjoint groups.
We do not claim a single uninterrupted full-suite execution.

## Real native input

The split C++ engine was built and invoked with:

```json
{"operation":"normalize","data":[{"email":" ADA@EXAMPLE.TEST "}],"lowercase":["email"]}
```

Returned:

```json
{"ok":true,"engine_version":"1.0.0","records":1,"format":"json","output":[{"email":"ada@example.test"}]}
```

Native CTest explicitly checks normalization and malformed CSV rejection even
under Release flags, without relying on disabled `assert` macros.

## Tests not executed / release blockers

- Dependency-backed React/Next/Vite builds, TypeScript typechecking and browser
  Playwright/Three.js testing. npm registry downloads were unavailable; no
  reviewed `package-lock.json` was generated or invented.
- Live Stripe Checkout/webhook/renewal, R2 private bucket/CORS/multipart/lifecycle,
  production PostgreSQL/Redis concurrency, database RLS, native seccomp sandbox,
  backups and retention deletion recovery, external security review and load tests.
- A small number of module routers still contain SQLAlchemy queries. The module
  ownership is real, but further thin-controller/ports extraction is unfinished.

The original v0.2 service behavior remains in scope; this structural release does
not claim new commercial API products or production throughput improvements.
