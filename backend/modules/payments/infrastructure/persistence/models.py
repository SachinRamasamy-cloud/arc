"""SQLAlchemy models owned by payments; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class Payment(Base):
    __tablename__='payments'
    id=Column(String(48),primary_key=True,default=lambda:uid('pay'))
    workspace_id=Column(ForeignKey('workspaces.id'),nullable=False,index=True)
    checkout_id=Column(String(128),unique=True)
    payment_intent=Column(String(128),unique=True)
    kind=Column(String(24),nullable=False,default='credits')
    request_key=Column(String(128))
    price_id=Column(String(128))
    checkout_url=Column(Text)
    checkout_expires_at=Column(BigInteger)
    state=Column(String(24),nullable=False,default='created')
    currency=Column(String(8),nullable=False)
    amount_minor=Column(BigInteger,nullable=False)
    credit_milli=Column(BigInteger,nullable=False,default=0)
    created_at=Column(BigInteger,nullable=False,default=now)


class StripeEvent(Base):
    __tablename__='stripe_events'
    id=Column(String(128),primary_key=True)
    kind=Column(String(80),nullable=False)
    state=Column(String(24),nullable=False,default='received')
    created_at=Column(BigInteger,nullable=False,default=now)


Index('ix_payments_pending', Payment.workspace_id, Payment.kind, Payment.state, Payment.checkout_expires_at)

Index('uq_payments_request_key', Payment.request_key, unique=True)
