"""Customer-visible sanitized request metadata."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from modules.analytics.public import RequestLog
from modules.authorization.public import current_user, project_access
from foundation.database.dependencies import db_session
from foundation.errors.public import PublicError
router=APIRouter(prefix='/api/console/v1',tags=['analytics'])
@router.get('/projects/{pid}/logs')
def request_logs(pid:str,request:Request,db=Depends(db_session)):
    user,_=current_user(request,db)
    project,_,member=project_access(db,pid,user)
    if member.role=='billing': raise PublicError('FORBIDDEN')
    rows=db.scalars(select(RequestLog).where(RequestLog.project_id==pid).order_by(RequestLog.created_at.desc()).limit(100))
    return {'items':[{k:getattr(r,k) for k in ('id','method','route','environment','status','duration_ms','created_at')} for r in rows]}
