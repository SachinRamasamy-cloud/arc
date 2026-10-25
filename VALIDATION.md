# Arc 0.2 — audit and executed validation

Prepared: 25 October 2026. This report applies to the complete source in `API_Provider_Implementation_v0_2.zip`. It is not a hosted-service certification.

## Audit findings and changes

| Original issue / omission | Change in 0.2 | Verification |
|---|---|---|
| Test dashboard could display live allowance | Environment-specific billing response and frontend normalization | Backend and shared-client tests |
| No immutable monthly metering ledger | Unique usage events, price versions, included/prepaid allocation and UTC month reports | Full-period aggregation and calendar tests |
| Checkout retry did not have a durable purchase attempt | Attempt persisted before network call; same provider idempotency key; known expired attempt recovery | Timeout/retry/expiration and webhook tests |
| Missing invoices and historical plan pricing | Invoice mirror, safe hosted links, immutable subscription price snapshots | Paid/failed event ordering and period tests |
| Several allowance grants and job locking had gaps | Earliest-expiring allowance allocation, fixed lock order, fenced settlement | Regression and concurrent-spend tests |
| Files had no persistent byte-time billing | Verified-file intervals, retention, monthly assessed/settled statements and visible arrears | Expiry/deletion and insufficient-balance tests |
| Upload completion/recovery was incomplete | SHA-256 verification, idempotent finish, bounded multipart and resume | Local flow, JS transfer logic and R2 SDK contract tests |
| No customer-application records API | Encrypted project/environment JSON records, versions, quotas, idempotency receipts | Public API integration and isolation tests |
| No recovery when payment delivery was missing | Bounded provider reconciliation plus read-only ledger/reservation diagnostic | Mock-provider recovery repeated without duplicate grant |
| Billing UI did not distinguish base plan from consumption | Separate subscription, allowance, prepaid, pending storage, payments and invoices | Source implemented and shared helpers tested; browser still unverified |

## Executed results

| Check | Result | Raw evidence |
|---|---|---|
| Backend/native/Python SDK suite | **141 passed** (95 previous + 46 added) | `artifacts/backend-full-tests.txt`, `backend-tests.xml` |
| Shared TypeScript/SDK/billing/upload logic | **21 passed** (12 existing + 9 added) | `artifacts/frontend-logic-tests.txt` |
| Frontend syntax/local imports | **32 source files; zero detected errors** | `artifacts/frontend-syntax.json` |
| Native CTest | **1 passed**; engine behavior also covered in pytest | `artifacts/native-ctest.txt` |
| Fresh migrated database and real HTTP | **16 checks passed**, compiled C++ and independent API consumer | `artifacts/http-smoke.json` |
| Migration upgrade | Fresh and populated SQLite revisions 0001–0003; balances preserved; backfill does not debit again; repeat-safe | Backend tests |
| Concurrent record writes | 25 competing writes with funds for 7: exactly 7 succeeded; remaining balance nonnegative | `test_v02_qualification.py` |
| Usage queries | Tested index selection for relevant SQLite quota/usage queries; complete month totals not limited to display rows | Backend tests |
| Release guard | **Release blocked**: 12 evidence gates and missing reviewed npm lockfile | `artifacts/release-check.json` |
| Archive integrity | ZIP CRC and each packaged file SHA-256 verified during packaging | `SOURCE_MANIFEST.json` inside archive |

Do not combine these counts into a claim of 179 browser/end-to-end features. Tests include parameterized scenarios. The 144 cases in the original plan were requirements, not a completed suite.

## External API calls actually executed

A separate HTTP client without portal cookies used a scoped API key against a real loopback Uvicorn server. The server used a freshly Alembic-migrated SQLite database and actual compiled C++ engine. The calls covered job submission/idempotency/status/SSE, encrypted application-record create/read/retry/delete, authorized file upload/verification/download/delete, monthly usage/wallet agreement and a balanced reconciliation diagnostic. Native normalization returned `ada@example.test` from ` ADA@EXAMPLE.TEST `.

This is an external consumer integration over real HTTP on the local host. It is **not** a public Internet deployment, React browser test, live R2 transfer or actual Stripe payment.

## Billing semantics verified

Monthly base subscription amounts are separate from service consumption. Included credits are used before prepaid credits; an operation is not charged from both sources for the same units. Monetary values use integer minor units, and credit values use integer milli-credits. Prices are versioned. Duplicate logical operations and duplicated payment events have one financial effect.

The selected calendar month is a UTC reporting window, not necessarily the Stripe subscription anniversary. The screen separately displays the actual subscription period. Current credit balances are labeled current rather than pretending they are historical closing balances. Usage totals cover the complete selected period; recent ledger/invoice/payment tables remain bounded views.

Storage is accumulated byte-time until expiry/deletion, using the documented 30-day GB-month convention. Insufficient funds leave an explicitly unsettled amount and block additional uploads. There is no claim that retained storage stops accruing whenever a processing budget is exhausted. Production needs a unified pre-reserved storage hard-budget policy before advertising that guarantee.

## What was not executed

- `npm install` could not complete; the registry DNS request fails here. No dependency-backed TypeScript build, Next/Vite build, React rendering, Playwright, accessibility audit or browser GPU profile was completed.
- No real PostgreSQL or Redis service, Cloudflare R2 bucket, Stripe account, SMTP delivery, Docker/Envoy deployment, public HTTPS endpoint or production KMS was available.
- Stripe tests use correctly signed synthetic events and contract-controlled provider responses. R2 tests use the local adapter and boto3 signing/Stubber checks. They are not live-provider evidence.
- No production performance benchmark, independent penetration test, sandbox escape assessment, restore drill or complete privacy-erasure qualification was run.

The GLB asset is unchanged from 0.1. Its included generation/parse evidence is inherited; browser rendering remains unverified.

## Deliberate implementation limits

Files are JSON/CSV/UTF-8 text, at most 16,000,000 bytes, with 1–720 hour retention. Multipart makes this bounded upload recoverable; it does not make the service a multi-gigabyte binary/video store. Processing results remain bounded inline output records.

Customer application values are encrypted JSON up to 65,536 bytes, with default workspace/environment quotas of 10,000 records / 16 MB. Record/collection names are indexed metadata. Retry responses are encrypted and expire after 24 hours, with bounded write receipts. This is not full database hosting, arbitrary SQL, customer-owned database synchronization or a commercial identity product.

Financial refund/dispute reversal, production RLS, a qualified native OS sandbox, Redis Streams processing transport/fairness, comprehensive observability, large artifact output, full archival/ownership workflows and verified deletion/backups remain incomplete or unqualified. Live prices and legal terms are not approved.

## Reproduce

Follow `docs/UPGRADE_V0_2.md`; preserve existing secrets and back up data before migration. Run the compiled native engine, `pytest -q`, `ctest --test-dir native/build --output-on-failure`, `npm test`, `npm run check:source` and `python scripts/http_smoke.py`. After network installation, run `npm run typecheck`, `npm run build` and the browser suite. Qualify the real infrastructure in staging before live activation.

**Release status: development hardening release. Do not label this package production-ready.**
