"""SQLAlchemy models owned by privacy; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class PrivacyRequest(Base):
    __tablename__='privacy_requests'
    id=Column(String(48),primary_key=True,default=lambda:uid('privacy'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    user_id=Column(ForeignKey('users.id'),nullable=False)
    kind=Column(String(16),nullable=False)
    state=Column(String(24),nullable=False,default='requested')
    created_at=Column(BigInteger,nullable=False,default=now)
