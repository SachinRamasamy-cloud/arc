"""Resumable direct uploads. Size/digest verification still gates processing."""
import hashlib
import math
import shutil
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select
from modules.files.public import FileObject
from modules.uploads.public import MultipartUpload
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import signed_token
from foundation.errors.public import PublicError
from foundation.database.dependencies import db_session
from modules.api_credentials.application.identity import identify
from modules.authorization.application.access import current_user, project_access
from modules.files.application.storage import finish_upload, file_view

api_router=APIRouter(tags=['multipart uploads'])
console_router=APIRouter(tags=['customer uploads'])


def file_access(request,db,fid,pid=None):
    if pid:
        user,_=current_user(request,db);project,_,_=project_access(db,pid,user,'files')
        query=select(FileObject).where(FileObject.id==fid,FileObject.project_id==project.id)
    else:
        identity=identify(request,db,'files:write')
        query=select(FileObject).where(FileObject.id==fid,FileObject.project_id==identity.project.id,FileObject.environment==identity.key.environment)
    file=db.scalar(query.with_for_update())
    if not file: raise PublicError('NOT_FOUND')
    return file


def begin(db,store,file):
    entry=db.get(MultipartUpload,file.id)
    if file.expires_at<=now(): raise PublicError('UPLOAD_NOT_READY')
    if entry and entry.state in ('uploading','assembled','complete') and file.state in ('pending','ready'):
        return entry
    if file.state!='pending': raise PublicError('UPLOAD_NOT_READY')
    if entry: raise PublicError('CONFLICT')
    provider_id=store.client.create_multipart_upload(Bucket=store.settings.r2_bucket,Key=file.object_key,ContentType=file.content_type)['UploadId'] if store.client else uid('multipart')
    entry=MultipartUpload(file_id=file.id,workspace_id=file.workspace_id,provider_id=provider_id,part_size=5*1024*1024,state='uploading')
    db.add(entry);db.flush();return entry


def parts(store,file,entry):
    if store.client:
        result=store.client.list_parts(Bucket=store.settings.r2_bucket,Key=file.object_key,UploadId=entry.provider_id)
        # The bounded 16 MB product cannot have >4 parts; never silently omit a page.
        if result.get('IsTruncated'): raise PublicError('INVALID_INPUT')
        return [{'number':p['PartNumber'],'etag':p['ETag'],'size':p['Size']} for p in result.get('Parts',[])]
    folder=store.path('multipart/'+entry.provider_id)
    return [{'number':int(p.name),'etag':hashlib.md5(p.read_bytes(),usedforsecurity=False).hexdigest(),'size':p.stat().st_size} for p in sorted(folder.glob('[0-9]*'),key=lambda x:int(x.name))] if folder.exists() else []


def session_view(store,file,entry):
    return {'file_id':file.id,'expected_size':file.expected_size,'expected_digest':file.expected_digest,'state':'complete' if file.state=='ready' else entry.state,'part_size':entry.part_size,'total_parts':math.ceil(file.expected_size/entry.part_size),
        'parts':parts(store,file,entry) if entry.state=='uploading' and file.state!='ready' else [],'expires_at':file.expires_at}


def sign_part(store,file,entry,number):
    count=math.ceil(file.expected_size/entry.part_size)
    if number<1 or number>count or entry.state!='uploading' or file.state!='pending' or file.expires_at<=now(): raise PublicError('INVALID_INPUT')
    expected=min(entry.part_size,file.expected_size-(number-1)*entry.part_size)
    if store.client:
        url=store.client.generate_presigned_url('upload_part',Params={'Bucket':store.settings.r2_bucket,'Key':file.object_key,'UploadId':entry.provider_id,'PartNumber':number},ExpiresIn=600)
    else:
        token=signed_token({'purpose':'multipart','id':file.id,'part':number,'upload':entry.provider_id,'exp':min(now()+600,file.expires_at)},store.settings)
        url=f'{store.settings.api_origin}/api/local-multipart/{file.id}/{number}?token={token}'
    return {'url':url,'method':'PUT','expected_size':expected,'expires_in':600}


def complete(db,store,file,entry):
    if file.state=='ready': return file_view(file)
    if file.state!='pending' or file.expires_at<=now() or entry.state not in ('uploading','assembled'): raise PublicError('UPLOAD_NOT_READY')
    if entry.state=='uploading':
        actual=parts(store,file,entry);expected=math.ceil(file.expected_size/entry.part_size)
        if len(actual)!=expected or [x['number'] for x in actual]!=list(range(1,expected+1)): raise PublicError('UPLOAD_NOT_READY')
        for item in actual:
            required=min(entry.part_size,file.expected_size-(item['number']-1)*entry.part_size)
            if item['size']!=required: raise PublicError('INVALID_INPUT')
        if store.client:
            store.client.complete_multipart_upload(Bucket=store.settings.r2_bucket,Key=file.object_key,UploadId=entry.provider_id,
                MultipartUpload={'Parts':[{'PartNumber':x['number'],'ETag':x['etag']} for x in actual]})
        else:
            target=store.path(file.object_key);target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('wb') as out:
                for part in actual:
                    with store.path(f'multipart/{entry.provider_id}/{part["number"]}').open('rb') as src: shutil.copyfileobj(src,out,1024*1024)
        entry.state='assembled';db.commit()
    result=finish_upload(db,store,file)
    entry.state='complete';db.commit()
    if not store.client: shutil.rmtree(store.path('multipart/'+entry.provider_id),ignore_errors=True)
    return file_view(result)


def cancel(db,store,file,entry):
    if entry.state=='aborted': return {'state':'aborted'}
    if file.state=='ready': raise PublicError('CONFLICT')
    if store.client and entry.state=='uploading':
        store.client.abort_multipart_upload(Bucket=store.settings.r2_bucket,Key=file.object_key,UploadId=entry.provider_id)
    elif not store.client: shutil.rmtree(store.path('multipart/'+entry.provider_id),ignore_errors=True)
    if entry.state=='assembled': store.delete(file.object_key)
    entry.state='aborted';file.state='deleted';db.commit();return {'state':'aborted'}


def register_routes(prefix,customer):
    router=console_router if customer else api_router
    # Register explicit signatures so OpenAPI exposes only the matching parameters.
    if customer:
        @router.post(prefix+'/{fid}/multipart')
        def start(pid:str,fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid,pid);entry=begin(db,request.app.state.store,f);db.commit();return session_view(request.app.state.store,f,entry)
        @router.post(prefix+'/{fid}/multipart/parts/{number}')
        def sign(pid:str,fid:str,number:int,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid,pid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return sign_part(request.app.state.store,f,entry,number)
        @router.post(prefix+'/{fid}/multipart/complete')
        def finish(pid:str,fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid,pid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return complete(db,request.app.state.store,f,entry)
        @router.delete(prefix+'/{fid}/multipart')
        def abort(pid:str,fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid,pid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return cancel(db,request.app.state.store,f,entry)
    else:
        @router.post(prefix+'/{fid}/multipart')
        def start_api(fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid);entry=begin(db,request.app.state.store,f);db.commit();return session_view(request.app.state.store,f,entry)
        @router.post(prefix+'/{fid}/multipart/parts/{number}')
        def sign_api(fid:str,number:int,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return sign_part(request.app.state.store,f,entry,number)
        @router.post(prefix+'/{fid}/multipart/complete')
        def finish_api(fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return complete(db,request.app.state.store,f,entry)
        @router.delete(prefix+'/{fid}/multipart')
        def abort_api(fid:str,request:Request,db=Depends(db_session)):
            f=file_access(request,db,fid);entry=db.get(MultipartUpload,fid)
            if not entry: raise PublicError('NOT_FOUND')
            return cancel(db,request.app.state.store,f,entry)

register_routes('/api/console/v1/projects/{pid}/files',True)
register_routes('/v1/files',False)
