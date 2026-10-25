"""SQLAlchemy models owned by notifications; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Notification(Base):
    __tablename__='notifications'
    id=Column(String(48),primary_key=True,default=lambda:uid('ntf'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    user_id=Column(ForeignKey('users.id'),nullable=False,index=True)
    category=Column(String(24),nullable=False)
    title=Column(String(160),nullable=False)
    message=Column(String(600),nullable=False)
    link=Column(String(200),nullable=False,default='overview')
    dedupe_key=Column(String(200),unique=True,nullable=False)
    read_at=Column(BigInteger)
    created_at=Column(BigInteger,nullable=False,default=now)


class Mail(Base):
    __tablename__='mail_outbox'
    id=Column(String(48),primary_key=True,default=lambda:uid('mail'))
    recipient=Column(String(254),nullable=False)
    subject=Column(String(200),nullable=False)
    body_encrypted=Column(Text,nullable=False)
    state=Column(String(24),nullable=False,default='pending')
    attempts=Column(Integer,nullable=False,default=0)
    due_at=Column(BigInteger,nullable=False,default=now)
    created_at=Column(BigInteger,nullable=False,default=now)
