"""audit-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from modules.audit.public import Audit
from foundation.database.dependencies import db_session
from modules.authorization.public import staff

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/audit')
def audits(request:Request,db=Depends(db_session)):
    staff(request,db)
    return {'items':[{k:getattr(a,k) for k in ('id','workspace_id','actor_id','action','resource_id','reason','created_at')} for a in db.scalars(select(Audit).where(Audit.action.like('operator.%')).order_by(Audit.created_at.desc()).limit(100))]}

