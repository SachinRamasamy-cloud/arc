"""webhooks-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func
from foundation.clock import now
from foundation.ids import uid
from foundation.errors.public import PublicError
from foundation.crypto.security import token, seal, validate_webhook_url
from modules.webhooks.interfaces.schemas import Hook
from modules.webhooks.public import WebhookDelivery, WebhookEndpoint
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor, env_guard
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/projects/{pid}/webhooks')
def webhooks(pid:str,request:Request,environment:str='test',db=Depends(db_session)):
    project,_,_=project_access(db,pid,actor(request,db),'build')
    endpoints=list(db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.project_id==pid,WebhookEndpoint.environment==environment)))
    return {'items':[{'id':e.id,'url':e.url,'enabled':e.enabled,'created_at':e.created_at} for e in endpoints],
            'deliveries':[{'id':d.id,'endpoint_id':d.endpoint_id,'state':d.state,'attempts':d.attempts,'status_code':d.status_code,'created_at':d.created_at,'event_id':d.event_id} for d in db.scalars(select(WebhookDelivery).where(WebhookDelivery.endpoint_id.in_([e.id for e in endpoints])).order_by(WebhookDelivery.created_at.desc()).limit(100))]}


@router.post('/projects/{pid}/webhooks',status_code=201)
def add_webhook(pid:str,body:Hook,request:Request,environment:str='test',db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build');env_guard(request,db,user,environment)
    validate_webhook_url(body.url,request.app.state.settings.allow_local_webhooks)
    if db.scalar(select(func.count(WebhookEndpoint.id)).where(WebhookEndpoint.project_id==pid))>=10: raise PublicError('POLICY_LIMIT')
    secret='whsec_'+token();endpoint=WebhookEndpoint(workspace_id=project.workspace_id,project_id=pid,environment=environment,url=body.url,encrypted_secret=seal(secret,request.app.state.settings,'webhook'))
    db.add(endpoint);db.flush();audit(db,user.id,'webhook.created',endpoint.id,project.workspace_id);db.commit();return {'id':endpoint.id,'secret':secret}


@router.post('/projects/{pid}/webhooks/{eid}/test')
def test_webhook(pid:str,eid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    endpoint=db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id==eid,WebhookEndpoint.project_id==pid,WebhookEndpoint.enabled.is_(True)))
    if not endpoint: raise PublicError('NOT_FOUND')
    eventid=uid('evt');delivery=WebhookDelivery(workspace_id=project.workspace_id,endpoint_id=eid,event_id=eventid,payload={'id':eventid,'type':'endpoint.test','created_at':now(),'data':{'test':True}})
    db.add(delivery);db.commit();return {'message':'Test delivery queued.'}


@router.delete('/projects/{pid}/webhooks/{eid}')
def disable_webhook(pid:str,eid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    endpoint=db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id==eid,WebhookEndpoint.project_id==pid))
    if not endpoint: raise PublicError('NOT_FOUND')
    endpoint.enabled=False;audit(db,user.id,'webhook.disabled',eid,project.workspace_id);db.commit();return {'message':'Endpoint disabled.'}


@router.post('/projects/{pid}/deliveries/{did}/replay')
def replay_webhook(pid:str,did:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    delivery=db.scalar(select(WebhookDelivery).join(WebhookEndpoint,WebhookDelivery.endpoint_id==WebhookEndpoint.id).where(WebhookDelivery.id==did,WebhookEndpoint.project_id==pid,WebhookEndpoint.enabled.is_(True)))
    if not delivery: raise PublicError('NOT_FOUND')
    if delivery.state in ('pending','sending'): raise PublicError('CONFLICT')
    delivery.state='pending';delivery.attempts=0;delivery.due_at=now();audit(db,user.id,'webhook.replayed',did,project.workspace_id);db.commit();return {'message':'Replay queued; event identity is unchanged.'}

