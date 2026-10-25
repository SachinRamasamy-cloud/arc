"""SQLAlchemy models owned by metering; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class UsageEvent(Base):
    """Append-only settlement evidence. Credits and money are never floats."""
    __tablename__ = 'usage_events'
    id = Column(String(48), primary_key=True, default=lambda: uid('use'))
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    project_id = Column(ForeignKey('projects.id'))
    environment = Column(String(8), nullable=False)
    reference = Column(String(200), nullable=False, unique=True)
    service = Column(String(40), nullable=False)
    operation = Column(String(60), nullable=False)
    quantity = Column(BigInteger, nullable=False, default=1)
    unit = Column(String(32), nullable=False)
    price_version = Column(String(64), nullable=False)
    gross_milli = Column(BigInteger, nullable=False, default=0)
    included_milli = Column(BigInteger, nullable=False, default=0)
    prepaid_milli = Column(BigInteger, nullable=False, default=0)
    occurred_at = Column(BigInteger, nullable=False, default=now)
    __table_args__ = (
        CheckConstraint('quantity >= 0 AND gross_milli >= 0 AND included_milli >= 0 AND prepaid_milli >= 0 AND gross_milli = included_milli + prepaid_milli'),
        Index('ix_usage_workspace_period', 'workspace_id', 'environment', 'occurred_at', 'id'),
        Index('ix_usage_project_period', 'project_id', 'environment', 'occurred_at'),
    )


class UsageCounter(Base):
    """Aggregate meter used for fractional per-1,000 API request prices."""
    __tablename__ = 'usage_counters'
    id = Column(String(128), primary_key=True)
    workspace_id = Column(ForeignKey('workspaces.id'), nullable=False)
    project_id = Column(ForeignKey('projects.id'), nullable=False)
    environment = Column(String(8), nullable=False)
    service = Column(String(40), nullable=False)
    period_start = Column(BigInteger, nullable=False)
    quantity = Column(BigInteger, nullable=False, default=0)
    charged_milli = Column(BigInteger, nullable=False, default=0)
    price_version = Column(String(64), nullable=False)
    rate_milli = Column(BigInteger, nullable=False)
    __table_args__ = (Index('ix_usage_counter_scope', 'workspace_id', 'environment', 'period_start'),)
