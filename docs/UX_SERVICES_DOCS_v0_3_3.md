# ARC v0.3.3 — Portal usability, service discovery and developer documentation

## Source and ownership

Based on v0.3.2. Separate `apps/customer-portal`, `apps/website`, operator app, backend modules, native engine and database contracts are retained. This release does not change SQL tables, Alembic versions, billing calculations or native processing operations.

## Fixed defects

- **Team & access** formerly rendered a loading notice *and* an empty table simultaneously. Its query now exclusively shows a skeleton, actionable error/retry, or resolved data. Members include their role and pending invitations are shown to managers only.
- **Navigation** has persistent quick links, collapsible feature groups and command search by synonyms (e.g. invoice, R2, OpenAPI, MFA). The doc link is always visible.
- **Public `/docs`** now works on both the Portal at `http://127.0.0.1:5173/docs` and the API at `http://127.0.0.1:8000/docs`. Envoy's staging route forwards `/docs` to the public-data API. The backend docs show only publicly supported `/v1` operations. The website still serves `/docs/` from Next.js.
- **API catalog** allows searchable, filterable discovery of all 10 product categories: five implemented and five specifically labeled planned, with call buttons *only* for implemented services. No project is needed to browse services or documentation.
- **Team visibility** is now read-only for all valid workspace members. Invite/remove and viewing pending invitations remain owner/admin only. Read-only access never implies a change to team permissions.
- **Loading safety**: GET queries use a 12-second abort deadline and surface a recoverable network error rather than indefinitely showing a spinner.
- **Public site** lists all categories, accurately differentiates planned products, and corrects older MFA/multipart descriptions.

## Current service products

| Service | Development availability |
|---|---|
| Native JSON/CSV processing | Available |
| Temporary processing-file uploads | Available |
| Job SSE and completion webhooks | Available |
| Encrypted application JSON records | Available |
| Approved linear custom workflows | Available |
| Application-user identity | Roadmap |
| Permanent general-purpose file storage | Roadmap |
| Customer-application notifications | Roadmap |
| General application realtime | Roadmap |
| Scheduling | Roadmap |

The portal's own login, email notifications and platform billing are **not** commercial products for customer applications.

## Security boundaries deliberately preserved

- Customer MFA remains optional (as in v0.3.2); staff MFA is mandatory.
- Workspace owners/admins can invite/remove members, while every member can view the directory.
- The backend continues to enforce live-environment flags, roles, CSRF, payment verification, API-key scopes, file isolation and tenant boundaries.
- Public docs do not expose staff OpenAPI contracts or live secrets. No external JS is loaded on API-hosted docs.
- Roadmap services do not accept API calls or consume credits.

## Local usage

Start the existing API and portal services (see README):

- Portal: `http://127.0.0.1:5173` → open a workspace → **Team & access** or **API services**.
- Portal reference: `http://127.0.0.1:5173/docs` (no login required).
- API reference: `http://127.0.0.1:8000/docs` and public contract `/v1/openapi.json`.
- Marketing/docs site: `http://127.0.0.1:3000/docs/` if the Next.js app is running.

The console only offers paid/live operations when existing entitlement and deployment checks pass. Those requirements are intentional and cannot be bypassed from the UI.

## Tests and limitations

Backend tests: `PYTHONPATH=backend:backend/src pytest -q backend/tests` (can be grouped by file in constrained environments).
Frontend syntax/local imports: `node scripts/check_frontend.cjs`.
Frontend navigation: `node --experimental-strip-types --test apps/customer-portal/app/navigation.test.mjs`.
Complete browser/build qualification: `npm install && npm run build && npm run test:e2e` on an Internet-capable environment with configured services.

This package has not been qualified against live Stripe/R2 or a public production deployment. Product-level features listed as roadmap are not implemented by this UX release.
