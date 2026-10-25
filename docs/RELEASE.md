# Release checklist — currently BLOCKED

The source is for local development and further qualification. Run `python scripts/release_check.py`; a nonzero exit is expected. Do not change booleans merely to make a dashboard green.

## 1. Reproducible build

Install dependencies with network access. Generate/review and commit npm and Python locks; audit versions and licenses. Run full TypeScript checking, Next export, both Vite builds and the shared logic suite. Compare generated public OpenAPI with the SDK/tests. Build the C++ engine with warnings-as-errors and run sanitizer/fuzz qualification in an isolated pipeline.

## 2. Browser/UI qualification

Run all supplied Playwright cases with the API and worker online. Add the full signup→verification→project→key→upload→run→billing journey plus keyboard/focus, screen reader, high zoom, reduced motion, mobile and WebGL-disabled variants. Inspect all customer/operator pages, 404/legal links, long names, errors and loading states. Test GLB disposal/context loss and measure GPU/bundle/network cost on low-end hardware. Syntax checks alone are not release evidence.

## 3. Data and authorization

Migrate a fresh PostgreSQL instance and an existing schema, test backups/restore and migration rollback. Add/qualify RLS and restricted DB roles. Run all authorization tests against PostgreSQL, including streams/objects/invoices across tenants. Rehearse operator access and mandatory MFA. No universal staff key may download customer content.

## 4. Worker and queue

Isolate native processes with restrictive OS/runtime controls. Repeat crashes/timeouts/cancel/lease-expiry tests. Implement and benchmark fair multi-tenant scheduling before advertising capacity guarantees. Validate maximum concurrency, memory, CPU, scratch capacity, parser limits and safe shutdown. Redis transport/fair scheduling is not implemented merely because Redis appears in the stack.

## 5. R2

Use a private bucket and scoped service credentials. Test actual browser CORS, signing expiry, content headers, oversize uploads, read races, canonical sealing, lifecycle/orphans, deletion and access denial. Keep an inventory and lifecycle rule for abandoned staging. Never infer that a presigned URL is single-use. Review data residency for compute, storage, database, logs and backups together.

## 6. Stripe and finance

Confirm the operating entity/country/account eligibility. Set reviewed price IDs, monetary amounts and credit grants. In Stripe test mode verify Checkout/Portal, asynchronous payment, repeated/out-of-order webhooks, period grants, proration, cancellation, failed renewal, price changes, refunds/disputes and account/customer mapping. Qualify `arc reconcile --workspace ... --apply` against the actual test account and investigate any remaining missing links or has_more result. Do not grant from redirects; do not bill prepaid consumption again. Disable unsupported plan changes in the hosted portal until qualified.

Approve published prices, tax/invoice treatment, credits validity, cancellation/refund policy, failure charging and budgeting behavior. Conduct parallel job admission tests against production-like PostgreSQL. Review the ledger with actual reconciled payment records.

## 7. Mail, webhooks and reminders

Configure SPF/DKIM/DMARC and transactional sender policy. Verify mailbox delivery, retries and redaction. Test webhook DNS rebinding/redirect defenses, certificates, idempotent receivers, bounded retry and dead-letter handling. Prove renewal reminders use real billing periods/timezones and deduplicate. Never represent SMTP acceptance as a user reading a message.

## 8. Privacy and legal

Name the legal entity, addresses, support/security/privacy contacts and actual subprocessors. Finalize Terms, Privacy, AUP, billing/refunds and applicable DPA. Replace draft notices only after review. Implement verified export/deletion workflows including backups/financial retention. The present deletion request queue is not automated erasure.

## 9. Edge and deployments

Use separate public/portal/operator hosts and separate API factories. Operator routes must not be reachable through the public API proxy. Configure HTTPS, HSTS, build-specific CSP, strict CORS, trusted proxy addresses, secret redaction and safe error bodies at the load balancer. Do not enable automatic retries on arbitrary mutations. Test SSE idle timeouts, reconnect, connection draining and overload behavior. Envoy reference YAML is not a load test.

Deploy new worker code only after checking immutable capability/version compatibility. Use additive migrations before application cutover; maintain a rollback-compatible schema. Snapshot and verify backups before destructive changes. Restarting workers must not repeat financial effects.

## 10. Operations and evidence

Establish request/queue/worker/financial/retention/notification dashboards, SLOs and alerts. Add an independently hosted status page. Rehearse Redis/DB/R2/provider outage, restore, compromised key response and staff break-glass. Record evidence artifacts, reviewer, date, configuration and exact build/dependency hashes.

Update each gate in `docs/release-evidence.json` only after an actual qualified run, referencing an existing artifact path. Re-run the release checker and security sign-off. Configuration flags such as `ARC_SECURITY_QUALIFIED` are deployment guards—not independent proof.

## Remaining explicit backlog

Real R2 multipart crash-window qualification and large outputs; full financial reversals and operational reconciliation coverage; complete privacy erasure; project-level team assignments and ownership transfer; fine-grained staff roles; RLS; production sandbox/fair scheduler/metrics; advanced workflow branches; generalized new API products; private runners/WASM. Publish only what is actually supported.

## Added 0.2 gates

Verify current-versus-offer subscription prices, fixed monthly invoices, record-call usage, allowance/prepaid splits, storage arrears and all environment/month filters in the real browser. Run `0003_usage_storage` on a populated PostgreSQL clone, then reconcile without rewriting money. Qualify expired/lost Checkout responses and multipart completion during process crashes. Confirm pricing snapshots are immutable and money units match the approved currency. The current storage model does not pre-reserve the entire retention cost: disclose this and implement a unified storage spend ceiling before claiming one.
