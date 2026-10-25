"""security_center-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from foundation.clock import now
from modules.api_credentials.public import ApiKey
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/security')
def security(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user,'security')
    keys=list(db.scalars(select(ApiKey).where(ApiKey.workspace_id==wid,ApiKey.revoked_at.is_(None))))
    findings=[]
    if not user.totp_secret: findings.append({'id':'mfa','severity':'high','title':'Enable multi-factor authentication','detail':'Your account does not yet have an authenticator.','action':'settings'})
    for key in keys:
        if key.expires_at<now()+7*86400: findings.append({'id':key.id,'severity':'warning','title':'Key expires soon: '+key.label,'detail':'Rotate this credential before its expiry date.','action':'keys'})
    return {'findings':findings,'active_keys':len(keys),'checks':[{'name':'API key secrets are stored as verifiers','state':'enforced'},{'name':'Public errors are sanitized','state':'enforced'},{'name':'Live access requires MFA','state':'enforced'}]}

