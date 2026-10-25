# Billing and usage contract — 0.2

## Separate payment, entitlement, usage and balance

Stripe collects a fixed monthly subscription and purchased credit packs. PostgreSQL records included allowances, prepaid balances, reservations and settled usage. Consumption of already purchased credits is not sent to Stripe as another charge.

A signed paid invoice grants the configured allowance once per subscription period. A duplicated event, an older failed-invoice event or a proration invoice does not mint another full allowance. Current subscription period boundaries come from provider objects, including item-level periods. A canceled-at-period-end subscription does not receive a misleading upcoming-renewal alert.

The Billing page shows the registered current plan, current allowance/prepaid funds, reserved credits, calendar-month usage, invoice amounts and payment states. Actual invoice totals include whatever Stripe reports; a displayed monthly base price is not represented as a tax-inclusive invoice. Final retail prices and tax treatment require approval.

## Usage units

- Processing: approved steps × (base milli-credits + max(1, rounded-up input KiB) × per-KiB rate). The accepted job stores the price version and snapshot. Failed internal processing releases its reservation. File retention is separate from processing.
- Managed records: successful external reads/lists/writes, priced per 1,000 logical operations. Round the cumulative monthly meter, not each request. Duplicate writes with the same idempotency key and identical input return the original receipt without another unit. Rejected/stale writes, portal inspection and deletion do not count.
- Verified file storage: byte-seconds, where 1 GB-month = 1,000,000,000 bytes × 30 days. Charge cumulative usage, not uploaded bytes or repeated hourly rounding. Stop at the earlier deletion/expiry boundary; delayed janitor execution does not extend customer billing.

The record meter is per project/environment/calendar month/price version. Usage reports group settlement timestamps in UTC. Subscription renewals follow the actual subscription period, not necessarily the first of the calendar month. Processing budget accounting uses its admission period, carries outstanding holds and includes current-month record charges.

## Transactions and concurrency

Acquire the workspace lock before wallet, allowance, job or usage state. Do not use different lock orders in API admission and workers. Included allowance is reserved/consumed before prepaid funds. Multiple eligible allowance grants are considered, not just the first row. Fencing prevents an expired worker from publishing another charge.

Each usage row satisfies gross = included + prepaid. Financial changes and the corresponding usage record commit together. Immutable identifiers protect job settlement, Stripe financial grants, record writes and monthly storage statements. Read queries aggregate full totals and use indexed, scoped pagination for usage events.

Storage shortfalls remain separately disclosed pending amounts. There is no silent overdraft. Retained data still has a cost; storage is not a fully pre-reserved spending-cap product in this release.

## Reconciliation and historical integrity

`arc reconcile --workspace ...` compares wallet balance to credit-ledger entries, held funds to active reservations and settled jobs to usage events. It reports differences and never overwrites the balance.

`--apply` reads Stripe and recovers known Checkout/invoice/subscription effects with stable event fingerprints. It is bounded to 100 pending attempts and up to five invoice pages by default. `has_more` requires further investigation. This is not comprehensive refund/dispute accounting: those conditions still freeze new paid work for review.

The upgrade copies existing successful job usage into reporting without another debit and starts existing-file billing at upgrade time. Historical price labels are explicitly `legacy-v0.1`; missing historical snapshots are not invented.

## Proof executed locally

Tests cover duplicate grants, raw webhook signatures, invoice ordering, price mismatch rejection, historical plan prices, calendar edges, Test/Live separation, reservation release, read/write idempotency, quota rollback and 25 competing record writes with credit for only seven. All seven successful writes were present; the balance was zero, never negative. Tests are local SQLite and provider-contract tests, not evidence of PostgreSQL load capacity or live provider operation.

References: https://docs.stripe.com/webhooks ; https://docs.stripe.com/billing/subscriptions/webhooks
