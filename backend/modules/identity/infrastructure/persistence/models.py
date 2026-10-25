"""SQLAlchemy models owned by identity; v0.2 table names retained."""
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, JSON, ForeignKey, UniqueConstraint, CheckConstraint, Index
from foundation.database.base import Base
from foundation.clock import now
from foundation.ids import uid

class User(Base):
    __tablename__='users'
    id=Column(String(48),primary_key=True,default=lambda:uid('usr'))
    email=Column(String(254),unique=True,nullable=False)
    name=Column(String(80),nullable=False,default='')
    password_hash=Column(Text,nullable=False)
    verified=Column(Boolean,nullable=False,default=False)
    staff=Column(Boolean,nullable=False,default=False)
    disabled=Column(Boolean,nullable=False,default=False)
    totp_secret=Column(Text)
    totp_pending=Column(Text)
    last_totp_step=Column(BigInteger,nullable=False,default=-1)
    recovery_hashes=Column(JSON,nullable=False,default=list)
    preferences=Column(JSON,nullable=False,default=dict)
    legal_version=Column(String(32),nullable=False,default='draft-v5')
    created_at=Column(BigInteger,nullable=False,default=now)


class LoginSession(Base):
    __tablename__='sessions'
    id=Column(String(64),primary_key=True)
    user_id=Column(ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True)
    audience=Column(String(16),nullable=False)
    mfa=Column(Boolean,nullable=False,default=False)
    expires_at=Column(BigInteger,nullable=False,index=True)
    created_at=Column(BigInteger,nullable=False,default=now)


class Token(Base):
    __tablename__='action_tokens'
    id=Column(String(64),primary_key=True)
    user_id=Column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    purpose=Column(String(32),nullable=False)
    payload=Column(JSON,nullable=False,default=dict)
    expires_at=Column(BigInteger,nullable=False)
    consumed=Column(Boolean,nullable=False,default=False)
