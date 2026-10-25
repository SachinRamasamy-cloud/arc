"""projects-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, update, func
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.projects.interfaces.schemas import CreateProject
from modules.executions.public import Job
from modules.api_credentials.public import ApiKey
from modules.projects.public import Project
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, project_access, actor, project_view
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/projects')
def list_projects(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user)
    return {'items':[project_view(p) for p in db.scalars(select(Project).where(Project.workspace_id==wid).order_by(Project.created_at))]}


@router.post('/workspaces/{wid}/projects',status_code=201)
def create_project(wid:str,body:CreateProject,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user,'build')
    if db.scalar(select(func.count(Project.id)).where(Project.workspace_id==wid,Project.archived.is_(False)))>=20: raise PublicError('POLICY_LIMIT')
    project=Project(workspace_id=wid,name=body.name.strip(),description=body.description);db.add(project);db.flush()
    audit(db,user.id,'project.created',project.id,wid);db.commit();return project_view(project)


@router.patch('/projects/{pid}')
def edit_project(pid:str,body:CreateProject,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build');project.name=body.name.strip();project.description=body.description
    audit(db,user.id,'project.updated',pid,project.workspace_id);db.commit();return project_view(project)


@router.post('/projects/{pid}/archive')
def archive_project(pid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'team')
    if db.scalar(select(func.count(Job.id)).where(Job.project_id==pid,Job.state.in_(['queued','running'])))>0: raise PublicError('CONFLICT')
    project.archived=True;db.execute(update(ApiKey).where(ApiKey.project_id==pid,ApiKey.revoked_at.is_(None)).values(revoked_at=now()))
    audit(db,user.id,'project.archived',pid,project.workspace_id);db.commit();return {'message':'Project archived; its API keys have been revoked.'}

