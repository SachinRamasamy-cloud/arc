"""workflows-owned customer HTTP handlers; no duplicate route implementations."""
import json
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, update, func
from foundation.errors.public import PublicError
from modules.workflows.interfaces.schemas import WorkflowBody
from modules.workflows.public import Workflow, WorkflowVersion
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor
from modules.audit.application.use_cases import audit
from modules.workflows.application.use_cases import validate_graph

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/projects/{pid}/workflows')
def workflows(pid:str,request:Request,db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'build')
    return {'items':[{'id':f.id,'name':f.name,'graph':f.draft,'revision':f.revision,'active_version':f.active_version} for f in db.scalars(select(Workflow).where(Workflow.project_id==pid).order_by(Workflow.created_at))]}


@router.post('/projects/{pid}/workflows',status_code=201)
def create_workflow(pid:str,body:WorkflowBody,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    if len(json.dumps(body.graph))>64_000: raise PublicError('PAYLOAD_TOO_LARGE')
    flow=Workflow(workspace_id=project.workspace_id,project_id=pid,name=body.name,draft=body.graph)
    db.add(flow);db.flush();audit(db,user.id,'workflow.created',flow.id,project.workspace_id);db.commit()
    return {'id':flow.id,'revision':flow.revision}


@router.patch('/projects/{pid}/workflows/{fid}')
def save_workflow(pid:str,fid:str,body:WorkflowBody,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    if len(json.dumps(body.graph))>64_000: raise PublicError('PAYLOAD_TOO_LARGE')
    updated=db.execute(update(Workflow).where(Workflow.id==fid,Workflow.project_id==pid,Workflow.revision==body.revision).values(name=body.name,draft=body.graph,revision=Workflow.revision+1))
    if updated.rowcount!=1: raise PublicError('STALE_DRAFT')
    audit(db,user.id,'workflow.saved',fid,project.workspace_id);db.commit();return {'id':fid,'revision':body.revision+1}


@router.post('/projects/{pid}/workflows/{fid}/validate')
def check_workflow(pid:str,fid:str,request:Request,db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'build')
    flow=db.scalar(select(Workflow).where(Workflow.id==fid,Workflow.project_id==pid))
    if not flow: raise PublicError('NOT_FOUND')
    return {'valid':True,'steps':validate_graph(flow.draft),'revision':flow.revision}


@router.post('/projects/{pid}/workflows/{fid}/publish')
def publish_workflow(pid:str,fid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    flow=db.scalar(select(Workflow).where(Workflow.id==fid,Workflow.project_id==pid).with_for_update())
    if not flow: raise PublicError('NOT_FOUND')
    compiled=validate_graph(flow.draft)
    number=(db.scalar(select(func.max(WorkflowVersion.number)).where(WorkflowVersion.workflow_id==fid)) or 0)+1
    version=WorkflowVersion(workspace_id=project.workspace_id,workflow_id=fid,number=number,graph=flow.draft,compiled=compiled)
    db.add(version);flow.active_version=number;audit(db,user.id,'workflow.published',fid,project.workspace_id);db.commit()
    return {'version':number,'endpoint':'/v1/workflows/'+fid+'/run','engine_version':'1.0.0'}


@router.get('/projects/{pid}/workflows/{fid}/versions')
def versions(pid:str,fid:str,request:Request,db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'build')
    flow=db.scalar(select(Workflow).where(Workflow.id==fid,Workflow.project_id==pid))
    if not flow: raise PublicError('NOT_FOUND')
    return {'active_version':flow.active_version,'items':[{'number':v.number,'graph':v.graph,'engine_version':v.engine_version,'created_at':v.created_at} for v in db.scalars(select(WorkflowVersion).where(WorkflowVersion.workflow_id==fid).order_by(WorkflowVersion.number.desc()))]}


@router.post('/projects/{pid}/workflows/{fid}/activate/{version}')
def activate_version(pid:str,fid:str,version:int,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    flow=db.scalar(select(Workflow).where(Workflow.id==fid,Workflow.project_id==pid))
    if not flow or not db.scalar(select(WorkflowVersion.id).where(WorkflowVersion.workflow_id==fid,WorkflowVersion.number==version)): raise PublicError('NOT_FOUND')
    flow.active_version=version;audit(db,user.id,'workflow.version_activated',fid,project.workspace_id,reason=str(version));db.commit();return {'active_version':version}

