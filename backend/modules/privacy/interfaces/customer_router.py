"""privacy-owned customer HTTP handlers; no duplicate route implementations."""
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy import select
from modules.privacy.interfaces.schemas import Privacy
from modules.executions.public import Job
from modules.privacy.public import PrivacyRequest
from modules.files.public import FileObject
from modules.projects.public import Project
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor, project_view
from modules.files.application.storage import file_view
from modules.audit.application.use_cases import audit
from modules.executions.application.use_cases import public_job

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/privacy')
def privacy(wid:str,request:Request,db=Depends(db_session)):
    workspace_access(db,wid,actor(request,db),'privacy')
    return {'storage':'Private R2' if request.app.state.settings.storage_mode=='r2' else 'Local development storage',
            'processing':'Authorized cloud workers can read plaintext during requested processing. This is not zero-knowledge encryption.',
            'requests':[{k:getattr(p,k) for k in ('id','kind','state','created_at')} for p in db.scalars(select(PrivacyRequest).where(PrivacyRequest.workspace_id==wid))]}


@router.post('/workspaces/{wid}/privacy')
def request_privacy(wid:str,body:Privacy,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user,'privacy')
    entry=PrivacyRequest(workspace_id=wid,user_id=user.id,kind=body.kind);db.add(entry);audit(db,user.id,'privacy.'+body.kind+'_requested',wid,wid);db.commit()
    return {'id':entry.id,'state':entry.state,'message':'Request recorded. Deletion is not represented as completed until verified.'}


@router.get('/workspaces/{wid}/export')
def export_workspace(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace,member=workspace_access(db,wid,user,'privacy')
    data={'workspace':{'id':wid,'name':workspace.name},'projects':[project_view(p) for p in db.scalars(select(Project).where(Project.workspace_id==wid))],
          'files':[file_view(f) for f in db.scalars(select(FileObject).where(FileObject.workspace_id==wid))],
          'executions':[public_job(j) for j in db.scalars(select(Job).where(Job.workspace_id==wid).limit(1000))]}
    audit(db,user.id,'privacy.metadata_exported',wid,wid);db.commit()
    return Response(json.dumps(data),media_type='application/json',headers={'Content-Disposition':'attachment; filename="workspace-export.json"'})

