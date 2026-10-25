"""Pure pricing calculation; the saved rate version is owned by the admission flow."""
from foundation.errors.public import PublicError

def quote_cost(payload_bytes,steps=1,settings=None):
    if payload_bytes<0 or steps<1 or steps>8: raise PublicError('INVALID_INPUT')
    base = settings.processing_base_milli if settings else 500
    rate = settings.processing_kib_milli if settings else 100
    return steps*(base+max(1,(payload_bytes+1023)//1024)*rate)

