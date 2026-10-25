"""One shared declarative metadata registry; ORM classes owned by domain modules."""
from sqlalchemy.orm import declarative_base
Base=declarative_base()
