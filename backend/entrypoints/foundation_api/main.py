"""A standalone health surface with database readiness checks."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text

from foundation.config.settings import Settings
from foundation.database.session import Database
from foundation.errors.public import PublicError, install_handlers
from foundation.ids import uid


def create_app(settings=None, database=None):
    settings = settings or Settings()
    owns_database = database is None
    database = database or Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns_database:
            database.engine.dispose()

    app = FastAPI(
        title="Arc backend foundation",
        version="0.3.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    install_handlers(app)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uid("req")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        try:
            with database.session() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            raise PublicError("SERVICE_UNAVAILABLE") from None
        return {"status": "ready"}

    return app
