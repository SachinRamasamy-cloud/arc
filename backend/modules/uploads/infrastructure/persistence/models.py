"""SQLAlchemy models owned by uploads; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class MultipartUpload(Base):
    __tablename__ = 'multipart_uploads'
    file_id = Column(ForeignKey('files.id'), primary_key=True)
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False, index=True)
    provider_id = Column(Text, nullable=False)
    state = Column(String(24), nullable=False, default='uploading')
    part_size = Column(Integer, nullable=False, default=5242880)
    created_at = Column(BigInteger, nullable=False, default=now)
