"""SQLAlchemy models owned by invoices; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(String(128), primary_key=True)
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    subscription_id = Column(String(128))
    status = Column(String(32), nullable=False)
    currency = Column(String(8), nullable=False)
    amount_due_minor = Column(BigInteger, nullable=False, default=0)
    amount_paid_minor = Column(BigInteger, nullable=False, default=0)
    period_start = Column(BigInteger)
    period_end = Column(BigInteger)
    hosted_url = Column(Text)
    pdf_url = Column(Text)
    updated_at = Column(BigInteger, nullable=False, default=now)
    created_at = Column(BigInteger, nullable=False, default=now)
    __table_args__ = (Index('ix_invoices_workspace_created', 'workspace_id', 'created_at'),)
