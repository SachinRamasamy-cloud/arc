"""SQLAlchemy models owned by wallets; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Wallet(Base):
    __tablename__='wallets'
    id=Column(String(48),primary_key=True,default=lambda:uid('wal'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    environment=Column(String(8),nullable=False)
    balance_milli=Column(BigInteger,nullable=False,default=0)
    held_milli=Column(BigInteger,nullable=False,default=0)
    spent_milli=Column(BigInteger,nullable=False,default=0)
    frozen=Column(Boolean,nullable=False,default=False)
    __table_args__=(UniqueConstraint('workspace_id','environment'),CheckConstraint('balance_milli >= 0 AND held_milli >= 0 AND held_milli <= balance_milli AND spent_milli >= 0'),)


class Allowance(Base):
    __tablename__='allowances'
    id=Column(String(128),primary_key=True)
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    balance_milli=Column(BigInteger,nullable=False)
    held_milli=Column(BigInteger,nullable=False,default=0)
    expires_at=Column(BigInteger,nullable=False,index=True)
    __table_args__=(CheckConstraint('balance_milli >= 0 AND held_milli >= 0 AND held_milli <= balance_milli'),)


class Ledger(Base):
    __tablename__='credit_ledger'
    id=Column(String(48),primary_key=True,default=lambda:uid('txn'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    environment=Column(String(8),nullable=False)
    reference=Column(String(160),unique=True,nullable=False)
    kind=Column(String(32),nullable=False)
    amount_milli=Column(BigInteger,nullable=False)
    description=Column(String(200),nullable=False)
    created_at=Column(BigInteger,nullable=False,default=now)


class CreditAllocation(Base):
    __tablename__ = 'credit_allocations'
    id = Column(String(48), primary_key=True, default=lambda: uid('alloc'))
    job_id = Column(ForeignKey('jobs.id'), nullable=False, index=True)
    allowance_id = Column(ForeignKey('allowances.id'), nullable=False)
    reserved_milli = Column(BigInteger, nullable=False)
    __table_args__ = (UniqueConstraint('job_id', 'allowance_id'), CheckConstraint('reserved_milli > 0'))
