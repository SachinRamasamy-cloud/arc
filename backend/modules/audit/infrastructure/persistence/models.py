"""SQLAlchemy models owned by audit; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Audit(Base):
    __tablename__='audit_events'
    id=Column(String(48),primary_key=True,default=lambda:uid('aud'))
    workspace_id=Column(String(48),index=True)
    actor_id=Column(String(48),nullable=False)
    action=Column(String(80),nullable=False)
    resource_id=Column(String(80),nullable=False)
    reason=Column(String(240),nullable=False,default='')
    created_at=Column(BigInteger,nullable=False,default=now)
