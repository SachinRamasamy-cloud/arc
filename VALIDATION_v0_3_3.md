# ARC v0.3.3 — Verification and release status

## Executed in this environment

| Test | Result |
|---|---|
| Python backend regression — identity, execution, docs, service catalogs, security, workflows | 97 passed |
| Python backend regression — payments, usage, storage, records, migrations and workers | 65 passed |
| Total independent Python cases | **162 passed** |
| Native C++ engine CTest | 2 passed |
| Shared TypeScript logic + SDK test script | 13 passed |
| Existing billing/upload frontend logic | 9 passed |
| Visual workflow graph tests | 11 passed |
| New navigation/search tests | 3 passed |
| TypeScript/TSX syntax and local import resolution | 65 files, 0 errors |
| New documentation and member access tests | Included in 162 backend tests; standalone rerun: 2 passed |
| Release guard | Correctly reports NOT ready |

The full backend test command timed out during execution in this environment; it was rerun in **two disjoint file groups** and both completed successfully. The combined test count is 162 (97+65).

## Not executed

- Third-party-dependent TypeScript typecheck and Vite/Next builds. `npm install --offline` failed with `ENOTCACHED` for `@playwright/test`.
- Browser-based Playwright tests, including the new Team loading-state and portal docs scenarios.
- Real PostgreSQL/Redis deployment qualification, hosted R2 upload/lifecycle checks, live Stripe payments and webhook replay.
- Production load, RLS, native OS sandbox, disaster recovery and independent security review.

**Passing logic/syntax checks does not qualify rendered behavior or production release.** The existing fail-closed `scripts/release_check.py` intentionally blocks release until required evidence is provided.

## Manual/browser qualification when dependencies are available

1. Run `npm install` in a clean environment, generate and review a lockfile; run `npm run typecheck` and `npm run build`.
2. Start the API and portal using the existing setup guide. Visit `/docs` on port 5173 and 8000; confirm `/v1/openapi.json` only exposes `/v1` consumer operations.
3. Visit Team & access. With a delayed network response, verify there is **no** empty-members message while loading. Confirm owner membership appears, invitations show only for manager roles, and viewer access is read-only.
4. Collapse and expand navigation, use Ctrl/Cmd+K to find `billing`, `R2`, `OpenAPI`, and project names. Confirm no horizontal overflow or trapped keyboard focus.
5. Browse all ten catalog entries without creating a project. Available service actions require a project; planned products have no callable or billable controls.
6. Confirm customer MFA remains optional and staff MFA remains mandatory.
7. Verify 429, network failures, unknown server exceptions and unavailable live payment setup show safe, actionable messages rather than raw exception text.
