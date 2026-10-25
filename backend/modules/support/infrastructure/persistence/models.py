"""SQLAlchemy models owned by support; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class SupportTicket(Base):
    __tablename__='support_tickets'
    id=Column(String(48),primary_key=True,default=lambda:uid('ticket'))
    workspace_id=Column(ForeignKey('workspaces.id'),index=True)
    user_id=Column(ForeignKey('users.id'))
    email=Column(String(254),nullable=False)
    subject=Column(String(160),nullable=False)
    message=Column(String(4000),nullable=False)
    state=Column(String(24),nullable=False,default='open')
    reply=Column(String(4000),nullable=False,default='')
    created_at=Column(BigInteger,nullable=False,default=now)
