"""audit application use cases. Existing v0.2 behavior retained."""
import hashlib,json,math,secrets,time
from datetime import datetime,timezone
from sqlalchemy import select,update,func
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import seal
from foundation.errors.public import PublicError
from modules.audit.public import Audit

def audit(db,actor,action,resource,wid=None,reason=''):
    db.add(Audit(workspace_id=wid,actor_id=actor,action=action,resource_id=resource,reason=reason))
