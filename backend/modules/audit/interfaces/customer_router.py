"""audit-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select
from modules.audit.public import Audit
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/audit')
def audits(wid:str,request:Request,limit:int=Query(50,ge=1,le=100),db=Depends(db_session)):
    workspace_access(db,wid,actor(request,db),'security')
    return {'items':[{k:getattr(a,k) for k in ('id','actor_id','action','resource_id','reason','created_at')} for a in db.scalars(select(Audit).where(Audit.workspace_id==wid).order_by(Audit.created_at.desc()).limit(limit))]}

