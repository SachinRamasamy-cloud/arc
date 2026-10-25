"""SQLAlchemy models owned by files; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class FileObject(Base):
    __tablename__='files'
    id=Column(String(48),primary_key=True,default=lambda:uid('file'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    project_id=Column(ForeignKey('projects.id'),nullable=False,index=True)
    environment=Column(String(8),nullable=False)
    name=Column(String(200),nullable=False)
    content_type=Column(String(80),nullable=False)
    expected_size=Column(BigInteger,nullable=False)
    size=Column(BigInteger,nullable=False,default=0)
    digest=Column(String(64))
    expected_digest=Column(String(64))
    purpose=Column(String(16),nullable=False,default='processing')
    retention_hours=Column(Integer,nullable=False,default=24)
    object_key=Column(String(256),nullable=False)
    state=Column(String(24),nullable=False,default='pending')
    expires_at=Column(BigInteger,nullable=False)
    created_at=Column(BigInteger,nullable=False,default=now)


class StorageInterval(Base):
    """Bill only verified retained bytes; actual close time stops accumulation."""
    __tablename__ = 'storage_intervals'
    id = Column(String(48), primary_key=True, default=lambda: uid('si'))
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    environment = Column(String(8), nullable=False)
    file_id = Column(ForeignKey('files.id'), nullable=False, unique=True)
    size_bytes = Column(BigInteger, nullable=False)
    opened_at = Column(BigInteger, nullable=False)
    closed_at = Column(BigInteger)
    __table_args__ = (Index('ix_storage_intervals_scope', 'workspace_id', 'environment', 'opened_at'),)


class StorageStatement(Base):
    __tablename__ = 'storage_statements'
    id = Column(String(128), primary_key=True)
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    environment = Column(String(8), nullable=False)
    period_start = Column(BigInteger, nullable=False)
    period_end = Column(BigInteger, nullable=False)
    measured_until = Column(BigInteger, nullable=False)
    byte_seconds = Column(BigInteger, nullable=False, default=0)
    assessed_milli = Column(BigInteger, nullable=False, default=0)
    settled_milli = Column(BigInteger, nullable=False, default=0)
    settled_byte_seconds = Column(BigInteger, nullable=False, default=0)
    state = Column(String(24), nullable=False, default='current')
    price_version = Column(String(64), nullable=False)
    rate_milli_gb_month = Column(BigInteger, nullable=False)
    __table_args__ = (UniqueConstraint('workspace_id', 'environment', 'period_start'),)


Index('ix_files_workspace_state', FileObject.workspace_id, FileObject.state)
