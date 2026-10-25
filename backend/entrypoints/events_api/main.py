"""Independent event-only ASGI factory."""
from entrypoints.application import create_app
def events(): return create_app(surface='events')
