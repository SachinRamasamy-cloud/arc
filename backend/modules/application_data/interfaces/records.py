"""Project-scoped application records. No arbitrary SQL or database credentials.

Payloads and short-lived idempotency receipts are encrypted. Indexed keys and
collection names are operational metadata and must not contain secrets.
"""
import hashlib
import json
import re
from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import Field
from sqlalchemy import select, func
from foundation.http.schemas import Body
from modules.application_data.public import CustomerRecord, MutationReceipt
from foundation.clock import now
from foundation.crypto.security import seal, unseal, signed_token, verify_signed
from foundation.errors.public import PublicError
from foundation.database.dependencies import db_session
from modules.authorization.application.access import current_user, project_access
from modules.api_credentials.application.identity import identify
from modules.metering.application.accounting import lock_workspace, bill_record_operation
from modules.audit.application.use_cases import audit

api_router = APIRouter(prefix='/v1/data', tags=['application data'])
console_router = APIRouter(prefix='/api/console/v1/projects', tags=['customer data management'])


class RecordBody(Body):
    data: dict
    expected_version: int = Field(default=0, ge=0)


def names(collection: str, key: str | None = None):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', collection):
        raise PublicError('INVALID_INPUT')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', key):
        raise PublicError('INVALID_INPUT')


def context(record):
    return f'record:{record.workspace_id}:{record.project_id}:{record.environment}:{record.collection}:{record.record_key}'


def view(record, settings):
    return {'key':record.record_key, 'collection':record.collection, 'version':record.version,
        'data':json.loads(unseal(record.encrypted_data,settings,context(record))),
        'size_bytes':record.size_bytes, 'created_at':record.created_at, 'updated_at':record.updated_at}


def lookup(db, project, env, collection, key):
    names(collection,key)
    return db.scalar(select(CustomerRecord).where(CustomerRecord.project_id==project.id,
        CustomerRecord.environment==env,CustomerRecord.collection==collection,CustomerRecord.record_key==key))


def mutate(db,settings,project,env,collection,key,body,idem,actor,*,delete=False,bill=True):
    names(collection,key)
    if not idem or len(idem)>128 or env not in ('test','live'): raise PublicError('INVALID_INPUT')
    lock_workspace(db,project.workspace_id)
    try:
        canonical=json.dumps({'delete':delete,'collection':collection,'key':key,**body.model_dump()},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
        serialized=json.dumps(body.data,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError,RecursionError): raise PublicError('INVALID_INPUT')
    size=len(serialized.encode())
    if size>settings.record_max_bytes: raise PublicError('PAYLOAD_TOO_LARGE')
    receipt_id=hashlib.sha256(f'{project.id}:{env}:{idem}'.encode()).hexdigest()
    fingerprint=hashlib.sha256(canonical.encode()).hexdigest()
    receipt=db.get(MutationReceipt,receipt_id)
    if receipt:
        if receipt.fingerprint!=fingerprint or receipt.expires_at<now(): raise PublicError('CONFLICT')
        return json.loads(unseal(receipt.response_encrypted,settings,'receipt:'+receipt_id)),False
    record=lookup(db,project,env,collection,key)
    if delete and not record: raise PublicError('NOT_FOUND')
    if (record.version if record else 0)!=body.expected_version: raise PublicError('CONFLICT')
    if not delete:
        count,stored=db.execute(select(func.count(CustomerRecord.id),func.coalesce(func.sum(CustomerRecord.size_bytes),0)).where(CustomerRecord.workspace_id==project.workspace_id,CustomerRecord.environment==env)).one()
        if count+(0 if record else 1)>settings.records_quota_count or stored-(record.size_bytes if record else 0)+size>settings.records_quota_bytes:
            raise PublicError('POLICY_LIMIT')
    if bill and not delete: bill_record_operation(db,settings,project,env,'record:'+receipt_id,'delete' if delete else 'write')
    if delete:
        result={'key':key,'collection':collection,'deleted':True,'version':record.version}
        db.delete(record)
    else:
        if not record:
            record=CustomerRecord(workspace_id=project.workspace_id,project_id=project.id,environment=env,
                collection=collection,record_key=key,version=1,created_at=now(),updated_at=now())
            db.add(record)
        else: record.version+=1;record.updated_at=now()
        record.size_bytes=size;record.encrypted_data=seal(serialized,settings,context(record))
        result=view(record,settings)
    encrypted_response=seal(json.dumps(result),settings,'receipt:'+receipt_id)
    if not delete:
        receipt_count,receipt_bytes=db.execute(select(func.count(MutationReceipt.id),func.coalesce(func.sum(MutationReceipt.response_bytes),0)).where(MutationReceipt.workspace_id==project.workspace_id,MutationReceipt.environment==env,MutationReceipt.expires_at>now())).one()
        if receipt_count>=settings.receipt_quota_count or receipt_bytes+len(encrypted_response)>settings.receipt_quota_bytes:raise PublicError('POLICY_LIMIT')
    # Deletes retain only a small receipt and remain possible when funds/quota are exhausted.
    db.add(MutationReceipt(id=receipt_id,workspace_id=project.workspace_id,project_id=project.id,environment=env,
        fingerprint=fingerprint,response_encrypted=encrypted_response,response_bytes=len(encrypted_response),expires_at=now()+86400))
    audit(db,actor,'application_data.deleted' if delete else 'application_data.saved',key,project.workspace_id)
    db.flush()
    return result,True


def list_records(db,settings,project,env,collection,limit=25,cursor=None):
    names(collection)
    query=select(CustomerRecord).where(CustomerRecord.project_id==project.id,CustomerRecord.environment==env,CustomerRecord.collection==collection)
    if cursor:
        value=verify_signed(cursor,settings,'records_cursor')
        if (value.get('pid'),value.get('env'),value.get('collection'))!=(project.id,env,collection): raise PublicError('INVALID_INPUT')
        query=query.where(CustomerRecord.record_key>value['after'])
    rows=list(db.scalars(query.order_by(CustomerRecord.record_key).limit(limit+1)))
    next_cursor=signed_token({'purpose':'records_cursor','pid':project.id,'env':env,'collection':collection,'after':rows[limit-1].record_key,'exp':now()+1800},settings) if len(rows)>limit else None
    return {'items':[view(row,settings) for row in rows[:limit]],'next_cursor':next_cursor}


def identified(request,db,scope):
    identity=identify(request,db,scope)
    request.app.state.limiter.check([(f'data:{{{identity.workspace.id}}}:all',600),(f'data:{{{identity.workspace.id}}}:{identity.project.id}',identity.project.rpm)])
    return identity


@api_router.put('/{collection}/{key}')
def put_record(collection:str,key:str,body:RecordBody,request:Request,idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    i=identified(request,db,'data:write')
    result,created=mutate(db,request.app.state.settings,i.project,i.key.environment,collection,key,body,idempotency_key,i.key.id)
    db.commit();return {'record':result,'applied':created}


@api_router.get('/{collection}/{key}')
def get_record(collection:str,key:str,request:Request,db=Depends(db_session)):
    i=identified(request,db,'data:read');settings=request.app.state.settings
    record=lookup(db,i.project,i.key.environment,collection,key)
    if not record: raise PublicError('NOT_FOUND')
    result=view(record,settings)
    bill_record_operation(db,settings,i.project,i.key.environment,'read:'+request.state.request_id,'read')
    db.commit();return {'record':result}


@api_router.get('/{collection}')
def scan_records(collection:str,request:Request,limit:int=Query(25,ge=1,le=100),cursor:str|None=None,db=Depends(db_session)):
    i=identified(request,db,'data:read');settings=request.app.state.settings
    result=list_records(db,settings,i.project,i.key.environment,collection,limit,cursor)
    bill_record_operation(db,settings,i.project,i.key.environment,'read:'+request.state.request_id,'list')
    db.commit();return result


@api_router.delete('/{collection}/{key}')
def remove_record(collection:str,key:str,request:Request,expected_version:int=Query(ge=1),idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    i=identified(request,db,'data:write')
    result,created=mutate(db,request.app.state.settings,i.project,i.key.environment,collection,key,RecordBody(data={},expected_version=expected_version),idempotency_key,i.key.id,delete=True)
    db.commit();return {'record':result,'applied':created}


@console_router.get('/{pid}/data')
def collections(pid:str,request:Request,environment:str='test',db=Depends(db_session)):
    user,_=current_user(request,db);project,_,_=project_access(db,pid,user,'build')
    if environment not in ('test','live'): raise PublicError('INVALID_INPUT')
    rows=db.execute(select(CustomerRecord.collection,func.count(CustomerRecord.id),func.sum(CustomerRecord.size_bytes)).where(CustomerRecord.project_id==pid,CustomerRecord.environment==environment).group_by(CustomerRecord.collection)).all()
    return {'collections':[{'name':r[0],'records':r[1],'size_bytes':r[2]} for r in rows],
        'limits':{'record_bytes':request.app.state.settings.record_max_bytes,'workspace_bytes':request.app.state.settings.records_quota_bytes,'workspace_records':request.app.state.settings.records_quota_count},
        'storage':'Managed application records, encrypted before database persistence. Not arbitrary SQL hosting or an identity service.'}


@console_router.get('/{pid}/data/{collection}')
def preview_records(pid:str,collection:str,request:Request,environment:str='test',limit:int=Query(25,ge=1,le=100),cursor:str|None=None,db=Depends(db_session)):
    user,_=current_user(request,db);project,_,_=project_access(db,pid,user,'build')
    if environment not in ('test','live'): raise PublicError('INVALID_INPUT')
    result=list_records(db,request.app.state.settings,project,environment,collection,limit,cursor)
    audit(db,user.id,'application_data.inspected',collection,project.workspace_id);db.commit();return result
