"""SQLAlchemy models owned by tenancy; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Workspace(Base):
    __tablename__='workspaces'
    id=Column(String(48),primary_key=True,default=lambda:uid('ws'))
    name=Column(String(80),nullable=False)
    status=Column(String(24),nullable=False,default='active')
    stripe_customer=Column(String(128),unique=True)
    subscription_id=Column(String(128),unique=True)
    subscription_status=Column(String(32),nullable=False,default='none')
    period_end=Column(BigInteger)
    period_start=Column(BigInteger)
    cancel_at_period_end=Column(Boolean,nullable=False,default=False)
    subscription_price=Column(String(128))
    storage_checked_at=Column(BigInteger,nullable=False,default=0)
    created_at=Column(BigInteger,nullable=False,default=now)


class Membership(Base):
    __tablename__='memberships'
    id=Column(String(48),primary_key=True,default=lambda:uid('mem'))
    workspace_id=Column(ForeignKey('workspaces.id',ondelete='CASCADE'),nullable=False,index=True)
    user_id=Column(ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True)
    role=Column(String(20),nullable=False)
    __table_args__=(UniqueConstraint('workspace_id','user_id'),)
