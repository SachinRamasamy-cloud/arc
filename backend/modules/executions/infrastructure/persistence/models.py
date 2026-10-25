"""SQLAlchemy models owned by executions; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Job(Base):
    __tablename__='jobs'
    id=Column(String(48),primary_key=True,default=lambda:uid('run'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    project_id=Column(ForeignKey('projects.id'),nullable=False,index=True)
    environment=Column(String(8),nullable=False)
    operation=Column(String(40),nullable=False)
    idempotency_key=Column(String(128),nullable=False)
    fingerprint=Column(String(64),nullable=False)
    input_data=Column(JSON,nullable=False)
    file_id=Column(ForeignKey('files.id'))
    state=Column(String(24),nullable=False,default='queued')
    billing_state=Column(String(24),nullable=False,default='reserved')
    reserved_milli=Column(BigInteger,nullable=False)
    charged_milli=Column(BigInteger,nullable=False,default=0)
    price_version=Column(String(64),nullable=False,default='development-1')
    input_bytes=Column(BigInteger,nullable=False,default=0)
    price_snapshot=Column(JSON,nullable=False,default=dict)
    reserved_paid_milli=Column(BigInteger,nullable=False,default=0)
    reserved_allowance_milli=Column(BigInteger,nullable=False,default=0)
    allowance_id=Column(ForeignKey('allowances.id'))
    result=Column(JSON)
    result_digest=Column(String(64))
    payload_deleted_at=Column(BigInteger)
    error_code=Column(String(40))
    attempt=Column(Integer,nullable=False,default=0)
    lease_token=Column(String(48))
    lease_until=Column(BigInteger)
    cancel_requested=Column(Boolean,nullable=False,default=False)
    created_at=Column(BigInteger,nullable=False,default=now)
    started_at=Column(BigInteger)
    completed_at=Column(BigInteger)
    __table_args__=(UniqueConstraint('project_id','environment','idempotency_key'),Index('ix_jobs_queue','state','created_at'),)


Index('ix_jobs_project_budget', Job.project_id, Job.environment, Job.created_at)

Index('ix_jobs_project_active', Job.project_id, Job.environment, Job.state)

Index('ix_jobs_workspace_period', Job.workspace_id, Job.environment, Job.created_at)
