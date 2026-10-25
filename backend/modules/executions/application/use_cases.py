"""executions application use cases. Existing v0.2 behavior retained."""
import hashlib,json,math,secrets,time
from datetime import datetime,timezone
from sqlalchemy import select,update,func
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import seal
from foundation.errors.public import PublicError
from modules.wallets.public import Allowance, CreditAllocation, Wallet
from modules.workflows.public import Workflow, WorkflowVersion
from modules.webhooks.public import WebhookDelivery, WebhookEndpoint
from modules.realtime_events.public import RunEvent
from modules.executions.public import Job
from modules.files.public import FileObject
from modules.tenancy.public import Workspace
from modules.audit.application.use_cases import audit
from modules.notifications.application.use_cases import notify
from modules.wallets.application.use_cases import wallet
from modules.pricing.application.use_cases import quote_cost

def prepare_request(db,project,env,body,settings=None):
    payload=body.model_dump(exclude={'max_credits_milli'})
    steps=[]
    if body.operation=='workflow':
        flow=db.scalar(select(Workflow).where(Workflow.id==body.workflow_id,Workflow.project_id==project.id))
        if not flow: raise PublicError('NOT_FOUND')
        version=body.version or flow.active_version
        entry=db.scalar(select(WorkflowVersion).where(WorkflowVersion.workflow_id==flow.id,WorkflowVersion.number==version))
        if not entry: raise PublicError('NOT_FOUND')
        payload['compiled']=entry.compiled
        payload['version']=entry.number
        steps=entry.compiled
    else: steps=[{'operation':body.operation}]
    if body.file_id:
        file=db.scalar(select(FileObject).where(FileObject.id==body.file_id,FileObject.project_id==project.id,FileObject.environment==env))
        if not file: raise PublicError('NOT_FOUND')
        if file.state!='ready' or file.expires_at<now(): raise PublicError('UPLOAD_NOT_READY')
        size=file.size
        payload['data']=None
    else:
        if body.data is None: raise PublicError('INVALID_INPUT')
        try: raw=json.dumps(body.data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
        except (ValueError,TypeError,RecursionError): raise PublicError('INVALID_INPUT')
        if len(raw)>1_500_000: raise PublicError('PAYLOAD_TOO_LARGE')
        size=len(raw)
    return payload,quote_cost(size,len(steps),settings),size


def admit(db,settings,limiter,project,env,body,idem,actor):
    if env not in ('test','live'): raise PublicError('INVALID_INPUT')
    if env=='live' and not settings.live_enabled: raise PublicError('LIVE_UNAVAILABLE')
    if not idem or len(idem)>128: raise PublicError('INVALID_INPUT')
    # Serialize admissions at the parent wallet, not at individual keys.
    db.execute(update(Workspace).where(Workspace.id==project.workspace_id).values(name=Workspace.name))
    payload,cost,size=prepare_request(db,project,env,body,settings)
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    existing=db.scalar(select(Job).where(Job.project_id==project.id,Job.environment==env,Job.idempotency_key==idem))
    if existing:
        if existing.fingerprint!=fingerprint: raise PublicError('CONFLICT')
        return existing,False
    from modules.pricing.application.pricing import ensure_price
    ensure_price(db,settings)
    if body.max_credits_milli<cost: raise PublicError('BUDGET_EXCEEDED')
    wid=project.workspace_id
    limiter.check([(f'lim:{{{wid}}}:all',600),(f'lim:{{{wid}}}:{project.id}',project.rpm)])
    active=db.scalar(select(func.count(Job.id)).where(Job.project_id==project.id,Job.environment==env,Job.state.in_(['queued','running'])))
    if active>=project.concurrency: raise PublicError('CAPACITY_REACHED')
    from modules.metering.application.accounting import check_project_budget
    check_project_budget(db,project,env,cost)
    allowance=None;included=0;allocations=[]
    value=wallet(db,wid,env)
    if value.frozen: raise PublicError('FORBIDDEN')
    if env=='live':
        for candidate in db.scalars(select(Allowance).where(Allowance.workspace_id==wid,Allowance.expires_at>now(),Allowance.balance_milli>Allowance.held_milli).order_by(Allowance.expires_at,Allowance.id).execution_options(populate_existing=True)):
            take=min(cost-included,candidate.balance_milli-candidate.held_milli)
            if take:
                candidate.held_milli+=take;included+=take;allocations.append((candidate.id,take))
                if allowance is None: allowance=candidate
            if included==cost: break
    paid=cost-included
    result=db.execute(update(Wallet).where(Wallet.workspace_id==wid,Wallet.environment==env,Wallet.frozen.is_(False),Wallet.balance_milli-Wallet.held_milli>=paid).values(held_milli=Wallet.held_milli+paid))
    if result.rowcount!=1: raise PublicError('INSUFFICIENT_CREDITS')
    job=Job(workspace_id=wid,project_id=project.id,environment=env,operation=body.operation,idempotency_key=idem,fingerprint=fingerprint,input_data=payload,file_id=body.file_id,reserved_milli=cost,reserved_paid_milli=paid,reserved_allowance_milli=included,allowance_id=allowance.id if allowance else None)
    job.price_version=settings.price_version
    job.input_bytes=size
    job.price_snapshot={'base_milli':settings.processing_base_milli,'kib_milli':settings.processing_kib_milli,'steps':len(payload.get('compiled') or [1])}
    db.add(job);db.flush()
    for allowance_id, reserved in allocations:
        db.add(CreditAllocation(job_id=job.id,allowance_id=allowance_id,reserved_milli=reserved))
    db.add(RunEvent(workspace_id=wid,job_id=job.id,kind='job.queued',payload={'state':'queued','reserved_milli':cost}))
    audit(db,actor,'job.created',job.id,wid)
    return job,True


def public_job(job,include_result=False):
    d={k:getattr(job,k) for k in ('id','project_id','environment','operation','state','billing_state','reserved_milli','charged_milli','created_at','started_at','completed_at','error_code','attempt','result_digest','price_version','input_bytes')}
    if include_result: d['result']=job.result
    return d


def completion_notifications(db,settings,job):
    notify(db,settings,job.workspace_id,'processing','Processing '+job.state,'Your '+job.environment+' execution '+job.id+' is '+job.state+'.','run:'+job.id,'executions')
    for endpoint in db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.project_id==job.project_id,WebhookEndpoint.environment==job.environment,WebhookEndpoint.enabled.is_(True))):
        db.add(WebhookDelivery(workspace_id=job.workspace_id,endpoint_id=endpoint.id,event_id='evt_'+job.id,payload={'id':'evt_'+job.id,'type':'job.'+job.state,'created_at':now(),'data':public_job(job)}))

