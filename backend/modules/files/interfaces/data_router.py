"""files-owned data HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.uploads.interfaces.schemas import Upload
from modules.executions.public import Job
from modules.uploads.public import MultipartUpload
from modules.files.public import FileObject
from foundation.database.dependencies import db_session
from modules.api_credentials.application.identity import identify
from modules.files.application.storage import start_upload,finish_upload,file_view
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/v1',tags=['product API'])

@router.post('/files',status_code=201)
def upload(body:Upload,request:Request,db=Depends(db_session)):
    identity=identify(request,db,'files:write')
    file,url=start_upload(db,request.app.state.settings,request.app.state.store,identity.project,identity.key.environment,body);db.commit()
    return {'file':file_view(file),'upload_url':url,'method':'PUT','headers':{'Content-Type':file.content_type},'expires_in':600}


@router.post('/files/{fid}/complete')
def complete(fid:str,request:Request,db=Depends(db_session)):
    identity=identify(request,db,'files:write')
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==identity.project.id,FileObject.environment==identity.key.environment).with_for_update())
    if not file: raise PublicError('NOT_FOUND')
    return file_view(finish_upload(db,request.app.state.store,file))


@router.get('/files/{fid}/download')
def download(fid:str,request:Request,db=Depends(db_session)):
    identity=identify(request,db,'files:read')
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==identity.project.id,FileObject.environment==identity.key.environment,FileObject.state=='ready',FileObject.expires_at>now()))
    if not file: raise PublicError('NOT_FOUND')
    return {'url':request.app.state.store.download_url(file),'expires_in':120}


@router.delete('/files/{fid}')
def delete_file(fid:str,request:Request,db=Depends(db_session)):
    from modules.tenancy.public import Workspace
    from modules.metering.application.accounting import lock_workspace, close_storage_interval
    from modules.audit.application.use_cases import audit
    i=identify(request,db,'files:write');lock_workspace(db,i.workspace.id)
    file=db.scalar(select(FileObject).where(FileObject.id==fid,FileObject.project_id==i.project.id,FileObject.environment==i.key.environment).with_for_update())
    if not file:raise PublicError('NOT_FOUND')
    if file.state in ('deleted','expired'):return {'state':file.state}
    if db.scalar(select(Job.id).where(Job.file_id==fid,Job.state.in_(['queued','running'])).limit(1)):raise PublicError('CONFLICT')
    from modules.uploads.public import MultipartUpload
    session=db.get(MultipartUpload,fid)
    if session and session.state in ('uploading','assembled'):
        from modules.uploads.interfaces.multipart import cancel
        cancel(db,request.app.state.store,file,session)
    else:
        request.app.state.store.delete(file.object_key);file.state='deleted';close_storage_interval(db,fid)
    audit(db,i.key.id,'file.deleted',fid,i.workspace.id);db.commit();return {'state':'deleted'}

