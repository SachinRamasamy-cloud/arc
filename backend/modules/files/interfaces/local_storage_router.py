"""Development-only local object access behind scoped signed URLs."""
from fastapi import APIRouter, Request
from fastapi.responses import Response
from modules.files.public import FileObject
from foundation.clock import now
from foundation.errors.public import PublicError
from foundation.crypto.security import verify_signed
router=APIRouter(tags=['local development storage'])
@router.put('/api/local-storage/{fid}')
async def local_upload(fid:str,request:Request,token:str):
    settings=request.app.state.settings
    permission=verify_signed(token,settings,'upload')
    if permission.get('id')!=fid: raise PublicError('FORBIDDEN')
    body=await request.body()
    with request.app.state.database.session() as db:
        file=db.get(FileObject,fid)
        if not file or file.state!='pending' or file.expires_at<now(): raise PublicError('UPLOAD_NOT_READY')
        if len(body)>file.expected_size: raise PublicError('PAYLOAD_TOO_LARGE')
        if request.headers.get('content-type')!=file.content_type: raise PublicError('INVALID_INPUT')
        request.app.state.store.write(file.object_key,body,file.content_type)
    return Response(status_code=204)
@router.get('/api/local-storage/{fid}')
def local_download(fid:str,request:Request,token:str):
    settings=request.app.state.settings
    permission=verify_signed(token,settings,'download')
    if permission.get('id')!=fid: raise PublicError('FORBIDDEN')
    with request.app.state.database.session() as db:
        file=db.get(FileObject,fid)
        if not file or file.state!='ready' or file.expires_at<now(): raise PublicError('NOT_FOUND')
        body=request.app.state.store.read(file.object_key,settings.max_file_bytes)
        return Response(body,media_type=file.content_type,headers={'Content-Disposition':'attachment; filename="download"'})
