"""SQLAlchemy models owned by application_data; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class CustomerRecord(Base):
    """Managed application records, not platform user identities or arbitrary SQL."""
    __tablename__ = 'customer_records'
    id = Column(String(48), primary_key=True, default=lambda: uid('rec'))
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    environment = Column(String(8), nullable=False)
    collection = Column(String(64), nullable=False)
    record_key = Column(String(128), nullable=False)
    encrypted_data = Column(Text, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(BigInteger, nullable=False, default=now)
    updated_at = Column(BigInteger, nullable=False, default=now)
    __table_args__ = (UniqueConstraint('project_id', 'environment', 'collection', 'record_key'),
        Index('ix_records_cursor', 'project_id', 'environment', 'collection', 'record_key'),)


class MutationReceipt(Base):
    __tablename__ = 'mutation_receipts'
    id = Column(String(128), primary_key=True)
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    environment = Column(String(8), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    response_encrypted = Column(Text, nullable=False)
    response_bytes = Column(BigInteger, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False, default=now)
    expires_at = Column(BigInteger, nullable=False, index=True)


Index('ix_records_workspace_quota',CustomerRecord.workspace_id,CustomerRecord.environment,CustomerRecord.size_bytes)

Index('ix_receipts_workspace_quota',MutationReceipt.workspace_id,MutationReceipt.environment,MutationReceipt.expires_at,MutationReceipt.response_bytes)
