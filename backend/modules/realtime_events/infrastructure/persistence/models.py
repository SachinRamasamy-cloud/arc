"""SQLAlchemy models owned by realtime_events; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class RunEvent(Base):
    __tablename__='run_events'
    id=Column(Integer,primary_key=True,autoincrement=True)
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    job_id=Column(ForeignKey('jobs.id'),nullable=False,index=True)
    kind=Column(String(40),nullable=False)
    payload=Column(JSON,nullable=False,default=dict)
    created_at=Column(BigInteger,nullable=False,default=now)
