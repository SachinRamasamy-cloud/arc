# Arc 0.2 — upgrade and verification

This is a development hardening release, not a production certification. Keep live access disabled until the release checklist is satisfied. The original 0.1 source is superseded by this complete archive; do not manually copy only one billing module.

## What changed

Billing now has its own immutable usage events, environment-aware monthly reports, included/prepaid splits, invoice mirrors, immutable usage prices, historical subscription-price snapshots, durable Checkout attempts and a bounded reconciliation command. A network retry reuses its existing Checkout attempt. An expired attempt returns a recoverable state rather than trapping the frontend. An unknown timeout must not cause the frontend to invent a new purchase.

The customer portal has a revised Billing page, a managed Application Data explorer, numeric pricing units and resumable direct uploads. Test views never borrow live allowance. Overview includes the live allowance when showing available credits. Usage totals aggregate the complete selected period; they are not sums of a truncated table. Recent credit entries are capped at 100, and recent payment/invoice lists at 50; these lists are not represented as complete historical exports.

Managed application records are a new, deliberately bounded API: encrypted JSON values, project/environment scopes, optimistic versions, stable pagination, 24-hour retry receipts and quotas. This is not PostgreSQL hosting, a complete BaaS, customer database synchronization or an end-user authentication product.

Files support JSON, CSV and UTF-8 text up to 16,000,000 bytes. Retention is explicit, 1–720 hours after verification. Files over 8 MiB use 5 MiB resumable parts in the portal. The R2 adapter issues direct storage URLs; the local adapter is for development. SHA-256 verification seals a distinct object. Metadata and byte-time billing start only after verification. Downloads/deletions are available to correctly scoped external API clients.

## Preserve existing data and secrets

Stop API mutation traffic and workers for the reviewed maintenance window. Back up the database and objects, and preserve the existing `ARC_SECRET_KEY` and `ARC_ENCRYPTION_KEY`. Changing the encryption key without a re-encryption procedure makes existing encrypted records, MFA secrets and email content unreadable. Do not regenerate `.env` as an upgrade technique.

Keep your existing `.env` outside version control. Review new non-secret settings in `.env.example`. The packaged rates are illustrative development values, not an approved price list.

From the extracted repository:

```sh
python -m pip install -e './backend[test]'
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build -j2
arc migrate
pytest -q
ctest --test-dir native/build --output-on-failure
npm install
npm test
npm run typecheck
npm run build
```

Install dependencies in a network-enabled environment. The authoring environment could not resolve the npm registry. No fabricated lockfile is included. Review the generated lockfile, run dependency/license checks and use `npm ci` afterwards.

Migration `0003_usage_storage` adds the new tables, indexed access paths and historical backfill. Tests cover fresh installation and upgrade from a populated 0002 SQLite database. Old settled processing rows are copied into reporting without another wallet debit. Existing ready files start their storage interval at the upgrade, not retroactively. Existing queued jobs retain their previous reservation/settlement path. PostgreSQL execution remains a staging qualification requirement.

An empty migration can be reversed for testing. A populated billing/customer-data migration refuses a destructive downgrade. Use a reviewed backup restore or a forward repair instead of deleting financial history.

## Pricing setup

`1 credit = 1,000 milli-credits`. Monetary amounts are integer minor currency units. This release accepts USD, EUR, GBP and INR; other minor-unit rules are not guessed.

Configure `ARC_PRICE_VERSION`, processing base/per-KiB rates, the records-per-1,000 rate and storage GB-month rate. Once a usage price version is recorded, its rates cannot be changed in place. Publish a new version. Each processing admission pins its own rate snapshot. A monthly record meter retains its rate for that version. Storage retains the price of its monthly statement.

Configure Stripe price IDs, expected currency/amount, pack credits and subscription allowance. Checkout checks the actual Stripe Price before creating the session. An existing subscription's registered price keeps its own allowance/base price even if the current offer changes. Changes to an existing registered plan's allowance require a new Stripe Price ID. Disable unsupported plan changes in the Stripe Customer Portal until separately qualified.

Do not enable `ARC_LIVE_ENABLED` or approval flags merely to bypass testing. The built-in `$29` and credit-pack figures are test configuration, not product recommendations.

## Reconcile before enabling paid use

Read-only local ledger/reservation diagnostic:

```sh
arc reconcile --workspace ws_YOUR_WORKSPACE
```

Explicit provider recovery with your configured Stripe test account:

```sh
arc reconcile --workspace ws_YOUR_WORKSPACE --apply
```

The second command retrieves existing Stripe Checkout/subscription/invoice state and applies verified missing events. It does not create a charge or rewrite balances to hide differences. It is idempotent and bounded; inspect `has_more`. Unknown payment links, refunds/disputes and larger historical imports still require an operator procedure. Schedule/review this reconciliation operationally; it is not silently run by every dashboard request.

## Running the upgraded application

```sh
python scripts/dev.py
```

Open the customer portal, select Test, then check Billing and Application Data. Use a key with `data:read`/`data:write` for your application's records. Use `files:read`/`files:write` for storage. Secrets stay in the customer's backend, not frontend source.

The real-loopback integration smoke uses a disposable migrated database and a compiled native engine:

```sh
python scripts/http_smoke.py
```

It performs real HTTP calls from an independent cookie-free client, record creation/read/retry/delete, file upload/download/delete, native processing, usage matching and ledger reconciliation. It does not claim to test a real R2 bucket or Stripe account.

## Limits you must keep visible

Record values are at most 65,536 JSON bytes. Defaults are 10,000 records / 16 MB logical data per workspace/environment. Retry receipts are limited to 4,096 active write receipts / 64 MB, with compact deletion receipts allowed so quota cannot trap data. Record keys and collection names are indexed metadata: do not put secrets there. Delete and portal inspection are not charged as commercial record calls.

Storage defaults to 256 MB per workspace. A record write does not automatically become a general storage API or expose arbitrary SQL. Processing results remain bounded inline job results in this release; a general large-output artifact service is not added.

Monthly storage charges accrue for retained verified files. Insufficient funds leave visible unsettled storage and block new uploads; they do not create a negative wallet or immediately erase existing data. Existing retained files can continue to accrue the disclosed storage fee until expiry/deletion. Project caps cover processing and record operations; a unified pre-reserved hard storage-spend ceiling is not yet implemented. Do not advertise an absolute all-services no-accrual guarantee.

## Production work still required

Real browser builds and billing journeys; PostgreSQL/Redis concurrency and RLS; real Stripe test-account flows and R2 CORS/multipart/lifecycle qualification; KMS/key rotation; a qualified native OS sandbox; production load/fairness; backup/restore and complete privacy erasure; financial reversal/tax handling; approved legal/pricing. Run `python scripts/release_check.py` to see the gates. It intentionally remains blocked.
