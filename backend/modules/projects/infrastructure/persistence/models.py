"""SQLAlchemy models owned by projects; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Project(Base):
    __tablename__='projects'
    id=Column(String(48),primary_key=True,default=lambda:uid('prj'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    name=Column(String(80),nullable=False)
    description=Column(String(500),nullable=False,default='')
    archived=Column(Boolean,nullable=False,default=False)
    rpm=Column(Integer,nullable=False,default=60)
    concurrency=Column(Integer,nullable=False,default=3)
    monthly_cap_milli=Column(BigInteger,nullable=False,default=100_000)
    retention_hours=Column(Integer,nullable=False,default=168)
    created_at=Column(BigInteger,nullable=False,default=now)
    __table_args__=(CheckConstraint('rpm > 0 AND concurrency > 0 AND monthly_cap_milli >= 0'),)
