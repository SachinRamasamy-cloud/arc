"""Small synchronous server-side client. Keep ARC_API_KEY out of browser code."""
from __future__ import annotations
import hashlib
import hmac
import json
import time
from typing import Any
import httpx

class ArcAPIError(Exception):
    def __init__(self, status: int, code: str, request_id: str = ''):
        super().__init__(f'Arc request failed ({status}, {code}). Reference: {request_id}')
        self.status, self.code, self.request_id = status, code, request_id

class ArcClient:
    """Caller owns idempotency keys; unsafe requests are not automatically retried."""
    def __init__(self, base_url: str, api_key: str, *, transport: httpx.BaseTransport | None = None):
        if not api_key:
            raise ValueError('An API key is required.')
        self._client = httpx.Client(base_url=base_url.rstrip('/'), headers={'Authorization': 'Bearer '+api_key}, timeout=30, follow_redirects=False, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> 'ArcClient':
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not response.is_success:
            # Do not reflect an upstream detail/exception string into the host application's UI.
            code = str(body.get('code', 'INTERNAL_ERROR')) if isinstance(body, dict) else 'INTERNAL_ERROR'
            if not all(c.isupper() or c=='_' for c in code) or len(code)>64:
                code = 'INTERNAL_ERROR'
            ref = response.headers.get('x-request-id', '')
            raise ArcAPIError(response.status_code, code, ref[:64])
        return body

    def run(self, *, operation: str, data: Any = None, file_id: str | None = None, idempotency_key: str, max_credits_milli: int = 10000, **options: Any) -> dict[str, Any]:
        if not idempotency_key:
            raise ValueError('Supply and retain an idempotency key for this operation.')
        payload = {'operation': operation, 'data': data, 'max_credits_milli': max_credits_milli, **options}
        if file_id:
            payload['file_id'] = file_id
        return self._request('POST', '/v1/jobs', json=payload, headers={'Idempotency-Key': idempotency_key})

    def job(self, job_id: str) -> dict[str, Any]:
        if not job_id.startswith('run_') or not job_id[4:].isalnum():
            raise ValueError('Invalid job ID.')
        return self._request('GET', '/v1/jobs/'+job_id)

    def wait(self, job_id: str, *, timeout: float = 120, interval: float = 1) -> dict[str, Any]:
        if timeout <= 0 or interval <= 0:
            raise ValueError('Timeout and polling interval must be positive.')
        until = time.monotonic()+timeout
        while True:
            value = self.job(job_id)
            if value['job']['state'] in ('succeeded','failed','canceled'):
                return value
            if time.monotonic() >= until:
                raise TimeoutError('Polling expired; the server job has not been canceled.')
            time.sleep(min(interval, max(0, until-time.monotonic())))

def verify_webhook(raw: bytes, signature: str, secret: str, *, clock: int | None = None, tolerance: int = 300) -> dict[str, Any]:
    """Verify exact received bytes before JSON parsing. Persist event IDs to deduplicate."""
    if not secret or tolerance < 0:
        raise ValueError('Invalid signing configuration.')
    try:
        fields = dict(part.split('=', 1) for part in signature.split(','))
        stamp = int(fields['t'])
        if abs((int(time.time()) if clock is None else clock)-stamp) > tolerance:
            raise ValueError()
        expected = hmac.new(secret.encode(), str(stamp).encode()+b'.'+raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, fields['v1']):
            raise ValueError()
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError()
        return body
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise ValueError('Invalid webhook signature or payload.') from None
