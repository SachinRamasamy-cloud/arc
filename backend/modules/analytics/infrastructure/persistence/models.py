"""SQLAlchemy models owned by analytics; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class RequestLog(Base):
    __tablename__='request_logs'
    id=Column(String(48),primary_key=True)
    workspace_id=Column(String(48),index=True)
    project_id=Column(String(48),index=True)
    environment=Column(String(8))
    method=Column(String(12),nullable=False)
    route=Column(String(180),nullable=False)
    status=Column(Integer,nullable=False)
    duration_ms=Column(Integer,nullable=False)
    created_at=Column(BigInteger,nullable=False,default=now)


Index('ix_logs_project_period', RequestLog.project_id, RequestLog.environment, RequestLog.created_at)
