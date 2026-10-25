"""Checkout idempotency key and request invariants."""
import hashlib
from foundation.errors.public import PublicError

def checkout_request_key(workspace_id:str, idempotency_key:str)->str:
    """Derive a stable 256-bit key scoped to a workspace; reject blank/oversize tokens."""
    if not isinstance(workspace_id,str) or not workspace_id:
        raise PublicError('INVALID_INPUT')
    if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=128:
        raise PublicError('INVALID_INPUT')
    return hashlib.sha256((workspace_id+':'+idempotency_key).encode()).hexdigest()
