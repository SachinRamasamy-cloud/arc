# Product API integration

The base URL is the configured public API origin. Control/customer routes are under `/api/console/v1`; they are not the API your customers should embed. Staff routes are private under `/api/operator/v1`.

| Method | Endpoint | Scope |
|---|---|---|
| POST | `/v1/jobs` | `jobs:write` + `Idempotency-Key` |
| GET | `/v1/jobs/{id}` | `jobs:read` |
| GET | `/v1/jobs/{id}/events` | `jobs:read` |
| POST | `/v1/workflows/{id}/run` | `jobs:write` + `Idempotency-Key` |
| POST | `/v1/files` | `files:write` |
| POST | `/v1/files/{id}/complete` | `files:write` |
| GET | `/v1/files/{id}/download` | `files:read` |
| GET | `/v1/openapi.json` | Public reference |

Use `Authorization: Bearer <project key>` from a backend/serverless function. A portal session and a product API key are different credentials. The API key selects its project and environment; the caller cannot substitute another workspace ID.

## Python

The tested client is `sdk/python/arc_client.py` and requires `httpx`. Add that file/module to your server integration, or package it before publishing an official SDK.

```python
import os, uuid
from arc_client import ArcClient

# Persist this key with the business operation; reuse it if submission is uncertain.
operation_key = str(uuid.uuid4())
with ArcClient(os.environ['ARC_API_URL'], os.environ['ARC_API_KEY']) as client:
    submitted = client.run(
        operation='normalize',
        data=[{'name': ' Ada ', 'email': ' ADA@EXAMPLE.TEST '}],
        lowercase=['email'],
        max_credits_milli=10000,
        idempotency_key=operation_key,
    )
    finished = client.wait(submitted['job']['id'], timeout=120)
    # Check finished['job']['state']; a failed job is not a valid result.
```

The client implementation and its normalize/wait path were tested against the actual local application/native engine. This snippet depends on your own URL/key and running worker.

## TypeScript

Use `sdk/typescript/index.ts` from your server. The tested client checks HTTP status, exposes safe error codes and never blindly retries a mutation. It is not a browser authentication library. The SDK is source in this repository, not a published npm package.

## File lifecycle

Authorize with `name`, `size` and `content_type` (`application/json` or `text/csv`). PUT exact bytes to `upload_url`, with its required headers and **without** the Arc bearer key. Complete the upload through the authenticated API. Only after verification may the `file_id` be used in a job. A download call returns an expiring capability, not a public object URL.

## SSE and webhooks

SSE emits `id`, typed `event` and JSON `data`; reconnect using `Last-Event-ID`. Keep a bounded event cache and do not treat network disconnect as job failure. Native browser EventSource cannot attach your server API secret; use your own backend relay or an explicitly implemented scoped-browser-token flow (not supplied here).

A webhook includes `Arc-Event-ID` and `Arc-Signature: t=<seconds>,v1=<hex>`. Verify HMAC-SHA256 over `timestamp + '.' + raw_body`, enforce freshness, then parse JSON. Persist event IDs before handling business effects. The Python SDK includes a tested signature verifier. Replays can redeliver the same logical event.

## Failure behavior

`401` credentials/session; `403` permission; `409` state/idempotency conflict; `413` input size; `422` invalid processing input; `429` rate/concurrency; `402` budget/credits; `503` unavailable service. Read the stable `code` and `request_id`, not internal exception strings. Safe retry depends on operation/idempotency, not just HTTP status.

## Application data and resumable files (0.2)

See `APPLICATION_DATA_V0_2.md` for the data:read/data:write service, optimistic versions, idempotency, scoped pagination, encryption and bounded file multipart paths. See `BILLING_V0_2.md` for successful-operation charging and free deletion. The generated public OpenAPI contains these routes.
