"""SQLAlchemy models owned by api_credentials; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class ApiKey(Base):
    __tablename__='api_keys'
    id=Column(String(48),primary_key=True,default=lambda:uid('key'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    project_id=Column(ForeignKey('projects.id'),nullable=False,index=True)
    label=Column(String(80),nullable=False)
    prefix=Column(String(24),nullable=False)
    digest=Column(String(64),nullable=False,unique=True)
    environment=Column(String(8),nullable=False)
    scopes=Column(JSON,nullable=False)
    expires_at=Column(BigInteger,nullable=False)
    revoked_at=Column(BigInteger)
    last_used_at=Column(BigInteger)
    created_at=Column(BigInteger,nullable=False,default=now)
