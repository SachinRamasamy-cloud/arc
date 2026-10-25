from fastapi.middleware.cors import CORSMiddleware

from entrypoints.foundation_api.main import create_app as create_foundation_app
from foundation.http.identity_security import IdentitySecurityMiddleware
from modules.identity.interfaces.auth import create_auth_router
from modules.rate_limits.infrastructure.limiter import Limiter


def create_app(settings=None, database=None):
    app = create_foundation_app(settings, database)
    app.title = "Arc customer identity"
    settings = app.state.settings
    app.state.limiter = Limiter(settings)
    app.include_router(create_auth_router("console"))
    app.add_middleware(IdentitySecurityMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.portal_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    return app
