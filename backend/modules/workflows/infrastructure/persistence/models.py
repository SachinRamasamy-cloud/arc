"""SQLAlchemy models owned by workflows; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Workflow(Base):
    __tablename__='workflows'
    id=Column(String(48),primary_key=True,default=lambda:uid('flow'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    project_id=Column(ForeignKey('projects.id'),nullable=False,index=True)
    name=Column(String(80),nullable=False)
    draft=Column(JSON,nullable=False)
    revision=Column(Integer,nullable=False,default=1)
    active_version=Column(Integer)
    created_at=Column(BigInteger,nullable=False,default=now)


class WorkflowVersion(Base):
    __tablename__='workflow_versions'
    id=Column(String(48),primary_key=True,default=lambda:uid('ver'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    workflow_id=Column(ForeignKey('workflows.id'),nullable=False,index=True)
    number=Column(Integer,nullable=False)
    graph=Column(JSON,nullable=False)
    compiled=Column(JSON,nullable=False)
    engine_version=Column(String(24),nullable=False,default='1.0.0')
    created_at=Column(BigInteger,nullable=False,default=now)
    __table_args__=(UniqueConstraint('workflow_id','number'),)
