"""Private storage adapter. Local uploads are development only; R2 uploads are direct."""
from pathlib import Path
import hashlib,json,os
from sqlalchemy import select,func,update
from modules.files.public import FileObject, StorageInterval, StorageStatement
from modules.tenancy.public import Workspace
from modules.executions.public import Job
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import signed_token, verify_signed
from foundation.errors.public import PublicError

class ObjectStore:
    def __init__(self,settings):
        self.settings=settings
        self.root=Path(settings.storage_dir).resolve()
        self.client=None
        if settings.storage_mode=='r2':
            import boto3
            from botocore.config import Config
            self.client=boto3.client('s3',endpoint_url=settings.r2_endpoint,aws_access_key_id=settings.r2_access_key,aws_secret_access_key=settings.r2_secret_key,region_name='auto',config=Config(signature_version='s3v4',connect_timeout=5,read_timeout=15,retries={'max_attempts':2}))
        else: self.root.mkdir(parents=True,exist_ok=True)
    def path(self,key):
        path=(self.root/key).resolve()
        if self.root not in path.parents: raise PublicError('FORBIDDEN')
        return path
    def write(self,key,body,content_type):
        if self.client: self.client.put_object(Bucket=self.settings.r2_bucket,Key=key,Body=body,ContentType=content_type)
        else:
            target=self.path(key);target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_suffix('.'+uid('part'))
            with open(temporary,'xb') as handle: handle.write(body)
            os.replace(temporary,target)
    def read(self,key,maximum):
        if self.client:
            head=self.client.head_object(Bucket=self.settings.r2_bucket,Key=key)
            if head['ContentLength']>maximum: raise PublicError('PAYLOAD_TOO_LARGE')
            response=self.client.get_object(Bucket=self.settings.r2_bucket,Key=key,IfMatch=head['ETag'])
            try: body=response['Body'].read(maximum+1)
            finally: response['Body'].close()
        else:
            target=self.path(key)
            if not target.exists(): raise PublicError('UPLOAD_NOT_READY')
            with open(target,'rb') as handle: body=handle.read(maximum+1)
        if len(body)>maximum: raise PublicError('PAYLOAD_TOO_LARGE')
        return body
    def delete(self,key):
        if self.client: self.client.delete_object(Bucket=self.settings.r2_bucket,Key=key)
        else: self.path(key).unlink(missing_ok=True)
    def upload_url(self,file):
        if self.client:
            return self.client.generate_presigned_url('put_object',Params={'Bucket':self.settings.r2_bucket,'Key':file.object_key,'ContentType':file.content_type},ExpiresIn=600)
        permission=signed_token({'purpose':'upload','id':file.id,'exp':now()+600},self.settings)
        return self.settings.api_origin+'/api/local-storage/'+file.id+'?token='+permission
    def download_url(self,file):
        if self.client:
            return self.client.generate_presigned_url('get_object',Params={'Bucket':self.settings.r2_bucket,'Key':file.object_key,'ResponseContentDisposition':'attachment'},ExpiresIn=120)
        permission=signed_token({'purpose':'download','id':file.id,'exp':now()+120},self.settings)
        return self.settings.api_origin+'/api/local-storage/'+file.id+'?token='+permission

def start_upload(db,settings,store,project,environment,body):
    db.execute(update(Workspace).where(Workspace.id==project.workspace_id).values(name=Workspace.name))
    usage=db.scalar(select(func.coalesce(func.sum(FileObject.expected_size),0)).where(FileObject.workspace_id==project.workspace_id,FileObject.state.in_(['pending','ready'])))
    count=db.scalar(select(func.count(FileObject.id)).where(FileObject.workspace_id==project.workspace_id,FileObject.state=='pending'))
    if usage+body.size>settings.storage_quota_bytes or count>=10: raise PublicError('POLICY_LIMIT')
    if db.scalar(select(StorageStatement.id).where(StorageStatement.workspace_id==project.workspace_id,StorageStatement.environment==environment,StorageStatement.state=='payment_required')): raise PublicError('INSUFFICIENT_CREDITS')
    if body.size>settings.max_file_bytes or '\x00' in body.name or '/' in body.name or '\\' in body.name: raise PublicError('INVALID_INPUT')
    file=FileObject(workspace_id=project.workspace_id,project_id=project.id,environment=environment,name=body.name,content_type=body.content_type,expected_size=body.size,expected_digest=body.sha256,purpose=body.purpose,retention_hours=body.retention_hours,object_key=project.workspace_id+'/staging/'+uid('object'),expires_at=now()+3600)
    db.add(file);db.flush()
    return file,store.upload_url(file)

def finish_upload(db,store,file):
    file=db.scalar(select(FileObject).where(FileObject.id==file.id).with_for_update().execution_options(populate_existing=True))
    if not file: raise PublicError('NOT_FOUND')
    if file.state=='ready': return file
    if file.state!='pending' or file.expires_at<now(): raise PublicError('UPLOAD_NOT_READY')
    data=store.read(file.object_key,file.expected_size)
    if len(data)!=file.expected_size: raise PublicError('INVALID_INPUT')
    # Only UTF-8 JSON/CSV is supported. Arbitrary binary archives/executables are never admitted.
    try:
        text=data.decode('utf-8-sig')
        if '\x00' in text: raise ValueError()
        if file.content_type=='application/json': json.loads(text)
    except (UnicodeError,ValueError): raise PublicError('INVALID_INPUT')
    checksum=hashlib.sha256(data).hexdigest()
    if file.expected_digest and checksum!=file.expected_digest: raise PublicError('INVALID_INPUT')
    old_key=file.object_key
    new_key=file.workspace_id+'/verified/'+uid('object')
    store.write(new_key,data,file.content_type)
    file.digest=hashlib.sha256(data).hexdigest();file.size=len(data);file.state='ready';file.object_key=new_key;file.expires_at=now()+file.retention_hours*3600
    db.add(StorageInterval(workspace_id=file.workspace_id,project_id=file.project_id,environment=file.environment,file_id=file.id,size_bytes=file.size,opened_at=now()))
    # Commit pointer BEFORE cleanup. A crash leaves a garbage object, never a trusted mutable staging input.
    db.commit()
    try: store.delete(old_key)
    except Exception: pass  # lifecycle cleanup is the bounded secondary mechanism
    return file

def file_view(file):
    return {k:getattr(file,k) for k in ('id','name','content_type','expected_size','size','state','digest','expires_at','created_at','environment','purpose','retention_hours')}
