"""SQLAlchemy models owned by webhooks; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class WebhookEndpoint(Base):
    __tablename__='webhook_endpoints'
    id=Column(String(48),primary_key=True,default=lambda:uid('wh'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    project_id=Column(ForeignKey('projects.id'),nullable=False,index=True)
    environment=Column(String(8),nullable=False)
    url=Column(String(2000),nullable=False)
    encrypted_secret=Column(Text,nullable=False)
    enabled=Column(Boolean,nullable=False,default=True)
    created_at=Column(BigInteger,nullable=False,default=now)


class WebhookDelivery(Base):
    __tablename__='webhook_deliveries'
    id=Column(String(48),primary_key=True,default=lambda:uid('del'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    endpoint_id=Column(ForeignKey('webhook_endpoints.id'),nullable=False,index=True)
    event_id=Column(String(80),nullable=False)
    payload=Column(JSON,nullable=False)
    state=Column(String(24),nullable=False,default='pending')
    attempts=Column(Integer,nullable=False,default=0)
    status_code=Column(Integer)
    due_at=Column(BigInteger,nullable=False,default=now)
    created_at=Column(BigInteger,nullable=False,default=now)
    __table_args__=(UniqueConstraint('endpoint_id','event_id'),)
