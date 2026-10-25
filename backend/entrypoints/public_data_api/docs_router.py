"""Offline-capable public developer documentation; exposes only the consumer API contract.

Deliberately does not use app.openapi(): that includes customer and operator routes
in the combined development ASGI process. No third-party script or stylesheet is loaded.
"""
from html import escape
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from entrypoints.public_data_api.openapi_router import published_openapi

router = APIRouter(tags=['API documentation'])

@router.get('/docs', include_in_schema=False, response_class=HTMLResponse)
@router.get('/docs/', include_in_schema=False, response_class=HTMLResponse)
def developer_documentation():
    schema = published_openapi()
    rows = []
    for path, path_item in sorted(schema.get('paths', {}).items()):
        for verb, operation in path_item.items():
            if verb.lower() not in ('get', 'post', 'put', 'patch', 'delete'):
                continue
            summary = operation.get('summary') or operation.get('operationId') or 'API operation'
            rows.append('<tr><td><strong>' + escape(verb.upper()) + '</strong></td><td><code>' + escape(path) + '</code></td><td>' + escape(summary) + '</td></tr>')
    body = '\n'.join(rows)
    # The page deliberately has no inline JS, external scripts, tokens or staff routes.
    return HTMLResponse('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Arc — Developer API reference</title></head><body>
<header><h1>Arc Developer API</h1><p>Public integration reference for available first-party API products.</p></header>
<main><h2>Start here</h2><p>Create a test project and scoped API key in the customer portal. Keep that secret on your own server—not in frontend JavaScript.</p>
<p>Send an authenticated request to <code>/v1/jobs</code> to run a supported operation. Use a stable <code>Idempotency-Key</code> when retrying an uncertain submission.</p>
<p><a href="/v1/openapi.json">Read or download the public OpenAPI contract</a></p>
<h2>Available public operations</h2><table><thead><tr><th>Method</th><th>Path</th><th>Description</th></tr></thead><tbody>''' + body + '''</tbody></table>
<h2>Security and billing</h2><p>Only scoped Bearer credentials are accepted for protected public operations. Normalized public error codes and request IDs are returned on failures. Quote and credit settlement are handled by the platform.</p>
<p>Authentication-as-a-service, general application realtime, and scheduling are not yet available as commercial API products.</p></main></body></html>''', headers={'Cache-Control': 'public, max-age=300'})
