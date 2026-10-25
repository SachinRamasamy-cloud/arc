"""files-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.uploads.interfaces.schemas import Upload
from modules.executions.public import Job
from modules.files.public import FileObject
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor, env_guard
from modules.files.application.storage import start_upload,finish_upload,file_view
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/projects/{pid}/files')
def files(pid:str,request:Request,environment:str='test',db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'files')
    return {'items':[file_view(f) for f in db.scalars(select(FileObject).where(FileObject.project_id==pid,FileObject.environment==environment).order_by(FileObject.created_at.desc()).limit(100))]}


@router.post('/projects/{pid}/files',status_code=201)
def upload(pid:str,body:Upload,request:Request,environment:str='test',db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'files');env_guard(request,db,user,environment)
    file,url=start_upload(db,request.app.state.settings,request.app.state.store,project,environment,body)
    audit(db,user.id,'file.upload_authorized',file.id,project.workspace_id);db.commit()
    return {'file':file_view(file),'upload_url':url,'method':'PUT','headers':{'Content-Type':file.content_type},'expires_in':600}


@router.post('/projects/{pid}/files/{fid}/complete')
def complete_upload(pid:str,fid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'files')
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==pid).with_for_update())
    if not file: raise PublicError('NOT_FOUND')
    file=finish_upload(db,request.app.state.store,file)
    audit(db,user.id,'file.verified',fid,project.workspace_id);db.commit();return file_view(file)


@router.get('/projects/{pid}/files/{fid}/download')
def download(pid:str,fid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'files')
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==pid,FileObject.state=='ready',FileObject.expires_at>now()))
    if not file: raise PublicError('NOT_FOUND')
    audit(db,user.id,'file.download_authorized',fid,project.workspace_id);db.commit()
    return {'url':request.app.state.store.download_url(file),'expires_in':120}


@router.delete('/projects/{pid}/files/{fid}')
def delete_file(pid:str,fid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'files')
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==pid))
    if not file: raise PublicError('NOT_FOUND')
    if db.scalar(select(func.count(Job.id)).where(Job.file_id==fid,Job.state.in_(['queued','running'])))>0: raise PublicError('CONFLICT')
    from modules.metering.application.accounting import lock_workspace, close_storage_interval
    lock_workspace(db,project.workspace_id)
    request.app.state.store.delete(file.object_key);file.state='deleted'
    close_storage_interval(db,file.id)
    audit(db,user.id,'file.deleted',fid,project.workspace_id);db.commit();return {'message':'File deleted from active storage.'}

