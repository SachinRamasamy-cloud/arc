# Security boundaries and limitations

This document describes controls in the code and unresolved deployment requirements. It is not a security certification.

## Implemented boundaries

- Argon2id password verifiers, email verification, expiring one-use action tokens and server-revocable sessions.
- Separate customer/operator session audiences; staff creation by CLI; MFA enforced for staff and live administrative actions.
- Session-bound CSRF for portal mutations, explicit origins, HttpOnly cookies, secure production cookie prefix and basic response security headers.
- Random API secrets revealed once, HMAC verifiers, explicit scopes, expiration/revocation and test/live association.
- Server-side role and object ownership checks for files, jobs, streams, billing and workspace settings. Hiding a button is not authorization.
- PostgreSQL-compatible transactional wallet constraints, holds, operation idempotency, fenced worker updates and immutable ledger references.
- No raw provider/database exception is returned. API errors use published codes; frontend errors use a safe message catalog. Logging avoids raw secret-bearing exception text.
- Restricted JSON/CSV processing, bounded file/record/column/depth counts, subprocess timeout and resource limits. No user-supplied executable, shell or arbitrary code node.
- Signed upload/download capabilities; verification of canonical input size/digest. R2 private credentials stay server-side.
- Webhook endpoints must be public HTTPS and are DNS-checked before delivery; validated IP is pinned while SNI/certificate validation remains hostname-based. No redirects; bounded response reading; signed raw payload.
- Operator interfaces show financial/support/security metadata; no universal content/download/secret access.

## Not yet qualified / must not be claimed

1. **OS isolation:** child process limits are not a complete sandbox. Add and validate non-root UID, read-only permitted mounts, isolated temporary filesystem, network deny, seccomp, PID/resource policies and kernel/runtime updates. The sample worker image is not proof of these controls.
2. **Database defense:** application tenant checks exist; RLS policies are not installed. Implement policies on tenant-owned tables using transaction-local tenant context and non-owner runtime roles, including worker/operator access paths. Do not enable blanket RLS without testing the real query model.
3. **Distributed concurrency:** the executed tests use SQLite. Repeat credit/allowance/idempotency/lease tests on PostgreSQL with several processes. Qualify Redis scripts and renewal leases under failure.
4. **Dependencies:** no frontend dependency lock or vulnerability audit could run without package downloads. Audit the complete JS/Python/C++ image supply chain, produce an SBOM, pin releases and review upgrades.
5. **Upload ingress:** a declared size is not an R2 ingress guarantee. Verification rejects oversized/untrusted content but cannot undo bandwidth/storage already consumed. Qualify signed Content-Length where supported or an upload gateway/token budget; use lifecycle and orphan reconciliation. Never enable arbitrary binary formats without parser/security work.
6. **Logs/data:** bounded JSON output is stored in the job row. Production should separate sensitive previews from metadata, implement comprehensive retention and audit access, and measure storage load. No signed attestation/zero-knowledge promise.
7. **Financial reconciliation:** signed-event unit tests are not bank settlement tests. Review Stripe asynchronous, out-of-order, cancellation, credits, refunds, dispute and proration behavior against a real test account.
8. **Notifications:** bounded retries and stable event IDs exist. Multi-worker outbox locking/lease recovery, SMTP deliverability and endpoint disable races need deployment qualification. Exactly-once network delivery is not promised.
9. **HTTP edge:** terminate HTTPS, apply body/deadline/connection/abuse policies, configure trusted forwarded IPs, sanitize edge-generated failures, and scope CSP to each real frontend build. The API's restrictive CSP must not be copied onto the frontend pages.
10. **Staff access:** use a separate private origin and enterprise access layer, least privilege and audited break-glass access. Fine-grained operator roles are not yet implemented.

## Secrets

Never commit `.env`, key material, `.local`, real payloads or payment receipts. Browser variables may contain only public origins. The encrypted local outbox is decryptable by the development application; protect the environment key and local files. Production needs a managed secret store/KMS, rotation and backup key recovery drills.

## Security tests supplied

Cross-tenant reads/writes, viewer/billing permissions, API key scope/revocation, session audience, CSRF/origin, one-use verification/reset, TOTP/recovery, password reset session revocation, stored-file replacement protection, billing replay and parallel reservations, sanitized unknown failures, URL validation, SDK signature and error handling, worker fencing and cancellation.

Full penetration testing, long fuzzing, memory sanitizer campaigns, browser XSS/CSP tests, dependency auditing and production failure injection were not performed in this environment.

## Vulnerability disclosure

Before launch establish a monitored security contact and documented response/notification process. Do not publish an invented security email. Never ask reporters to include passwords, live API keys or unrelated customer data.
