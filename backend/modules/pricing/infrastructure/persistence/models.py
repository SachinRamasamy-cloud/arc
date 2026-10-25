"""SQLAlchemy models owned by pricing; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class PlanPrice(Base):
    """Immutable commercial snapshot: never reprice existing subscriptions from env."""
    __tablename__='plan_prices'
    id=Column(String(128),primary_key=True)
    price_version=Column(String(64),nullable=False)
    currency=Column(String(8),nullable=False)
    amount_minor=Column(BigInteger,nullable=False)
    included_milli=Column(BigInteger,nullable=False)
    created_at=Column(BigInteger,nullable=False,default=now)


class UsagePrice(Base):
    __tablename__='usage_prices'
    version=Column(String(64),primary_key=True)
    processing_base_milli=Column(BigInteger,nullable=False)
    processing_kib_milli=Column(BigInteger,nullable=False)
    records_per_1000_milli=Column(BigInteger,nullable=False)
    storage_gb_month_milli=Column(BigInteger,nullable=False)
    created_at=Column(BigInteger,nullable=False,default=now)
