# Application data and files — 0.2

The platform account database and customer application records are different domains. Platform users, MFA, memberships and wallets stay in their existing tables. The new service stores authorized JSON records in `customer_records`, scoped by workspace, project and Test/Live environment.

Hosted deployment uses your managed PostgreSQL. Local development uses SQLite. Customers do not hand over their existing database credentials, and this implementation does not connect to their business database automatically. It is not a relational database-hosting product, Supabase replacement, login API or arbitrary SQL executor.

## Record endpoints

| Endpoint | Scope | Contract |
|---|---|---|
| PUT `/v1/data/{collection}/{key}` | data:write | JSON object, expected_version, stable Idempotency-Key |
| GET `/v1/data/{collection}/{key}` | data:read | Authorized current record |
| GET `/v1/data/{collection}?limit=25&cursor=...` | data:read | Scoped cursor, max 100 rows |
| DELETE `/v1/data/{collection}/{key}?expected_version=...` | data:write | Version check, stable Idempotency-Key; free deletion |

Create with `expected_version: 0`; update with the last returned version. A stale version is 409, not a silent overwrite. Repeating an uncertain identical write with its original key returns its encrypted receipt and does not charge again. Receipts expire after 24 hours. After that retention window, an old idempotency key is no longer a perpetual replay guarantee.

Values and retry responses are encrypted before persistence with context-bound encryption. The platform runtime can decrypt authorized reads: this is not zero-knowledge encryption. Keys, collection names, sizes, versions and timestamps are operational metadata; keep secrets out of names. Database disks, backups, key management and rotation need separate deployment controls.

Quota checks, mutation, receipt and usage settlement share a transaction. A quota or funding failure rolls everything back. Indexed per-workspace queries avoid scanning other tenants' records. Record deletion remains available when the prepaid balance or write-receipt quota is exhausted. Customer-portal reads are role checked/audited and free; staff do not gain a browse-all-records endpoint.

## File endpoints

Authorize with POST `/v1/files`; upload directly to the returned URL without the API key or portal cookies; complete using POST `/v1/files/{id}/complete`. The response is not trusted until server verification seals the object. Use GET `/v1/files/{id}/download` for a short-lived authorized download, and DELETE `/v1/files/{id}` for deletion. Active-job input deletion is rejected.

For resumable files: POST `/v1/files/{id}/multipart`, request signed part URLs from `/parts/{number}`, then POST `/complete` under the multipart path. The server determines which parts exist and their sizes; it does not trust a client-invented ETag list. Browser resume is bound to file size and SHA-256. Retry completed sessions without retransferring already verified content.

The supported product is JSON/CSV/UTF-8 text up to 16 MB, not arbitrary binary files or multi-GB video. R2 integration code uses presigned operations and canonical object sealing. Local tests exercise actual uploads to the local adapter; SDK stubs exercise R2 signing/HEAD/If-Match/read/write/delete contracts. Real R2 uploads, CORS, multipart crash windows and lifecycle/deletion must still be qualified in a private test bucket.

Presigned permissions are bearer URLs until expiry, not single-use credentials. Declaring an expected size does not enforce a hard network ingress cap at R2. Enforce ingress-abuse controls before public exposure. Retention removes access according to policy; complete backup erasure still requires a qualified deletion procedure.

Reference: https://developers.cloudflare.com/r2/api/s3/presigned-urls/
