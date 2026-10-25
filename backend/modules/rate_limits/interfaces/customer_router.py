"""rate_limits-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from modules.rate_limits.interfaces.schemas import Limits
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor, project_view
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/projects/{pid}/limits')
def limits(pid:str,request:Request,db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db))
    return {'configured':project_view(project),'ceiling':{'rpm':600,'concurrency':10,'monthly_cap_milli':10_000_000,'retention_hours':168},'reset':'Calendar month, UTC','file_limit_bytes':request.app.state.settings.max_file_bytes,'workspace_storage_bytes':request.app.state.settings.storage_quota_bytes}


@router.patch('/projects/{pid}/limits')
def save_limits(pid:str,body:Limits,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'security')
    for key,value in body.model_dump().items(): setattr(project,key,value)
    audit(db,user.id,'project.limits_updated',pid,project.workspace_id);db.commit();return project_view(project)

