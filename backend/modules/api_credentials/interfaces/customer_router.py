"""api_credentials-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func
from foundation.clock import now
from foundation.errors.public import PublicError
from foundation.crypto.security import token, keyed_digest
from modules.api_credentials.interfaces.schemas import CreateKey
from modules.api_credentials.public import ApiKey
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor, env_guard
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/projects/{pid}/keys')
def keys(pid:str,request:Request,environment:str='test',db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'keys')
    return {'items':[{k:getattr(key,k) for k in ('id','label','prefix','environment','scopes','expires_at','revoked_at','last_used_at','created_at')} for key in db.scalars(select(ApiKey).where(ApiKey.project_id==pid,ApiKey.environment==environment).order_by(ApiKey.created_at.desc()))]}


@router.post('/projects/{pid}/keys',status_code=201)
def create_key(pid:str,body:CreateKey,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'keys');env_guard(request,db,user,body.environment)
    if db.scalar(select(func.count(ApiKey.id)).where(ApiKey.project_id==pid,ApiKey.revoked_at.is_(None)))>=20: raise PublicError('POLICY_LIMIT')
    raw='arc_'+body.environment+'_'+token();key=ApiKey(workspace_id=project.workspace_id,project_id=pid,label=body.label,prefix=raw[:18],digest=keyed_digest(raw,request.app.state.settings.secret_key),environment=body.environment,scopes=sorted(set(body.scopes)),expires_at=now()+body.expires_days*86400)
    db.add(key);db.flush();audit(db,user.id,'key.created',key.id,project.workspace_id);db.commit()
    return {'id':key.id,'secret':raw,'prefix':key.prefix,'message':'Save this secret now. It will not be displayed again.'}


@router.delete('/projects/{pid}/keys/{keyid}')
def revoke_key(pid:str,keyid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'keys')
    key=db.scalar(select(ApiKey).where(ApiKey.id==keyid,ApiKey.project_id==pid))
    if not key: raise PublicError('NOT_FOUND')
    key.revoked_at=now();audit(db,user.id,'key.revoked',key.id,project.workspace_id);db.commit();return {'message':'Key revoked.'}

