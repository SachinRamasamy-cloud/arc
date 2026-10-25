"""Development-only multipart upload mock matching signed part permissions."""
import hashlib
from fastapi import APIRouter, Request
from fastapi.responses import Response
from modules.files.public import FileObject
from modules.uploads.public import MultipartUpload
from foundation.clock import now
from foundation.errors.public import PublicError
from foundation.crypto.security import verify_signed
router=APIRouter(tags=['local development multipart'])
@router.put('/api/local-multipart/{fid}/{part}')
async def local_part(fid:str,part:int,request:Request,token:str):
    settings=request.app.state.settings
    permission=verify_signed(token,settings,'multipart')
    if permission.get('id')!=fid or permission.get('part')!=part: raise PublicError('FORBIDDEN')
    body=await request.body()
    with request.app.state.database.session() as db:
        file=db.get(FileObject,fid);entry=db.get(MultipartUpload,fid)
        if not file or not entry or file.state!='pending' or entry.state!='uploading' or file.expires_at<=now() or permission.get('upload')!=entry.provider_id: raise PublicError('UPLOAD_NOT_READY')
        expected=min(entry.part_size,file.expected_size-(part-1)*entry.part_size)
        if expected<=0 or len(body)!=expected: raise PublicError('INVALID_INPUT')
        request.app.state.store.write(f'multipart/{entry.provider_id}/{part}',body,'application/octet-stream')
    return Response(status_code=200,headers={'ETag':hashlib.md5(body,usedforsecurity=False).hexdigest()})
