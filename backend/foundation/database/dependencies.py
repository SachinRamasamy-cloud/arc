"""FastAPI database session dependency shared by bounded contexts."""
from fastapi import Request

def db_session(request: Request):
    with request.app.state.database.session() as db:
        yield db
