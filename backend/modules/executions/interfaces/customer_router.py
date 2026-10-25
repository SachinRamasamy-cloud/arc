"""executions-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter,Request,Depends,Query,Header
from sqlalchemy import select, update, func
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.executions.interfaces.schemas import Run
from modules.executions.public import Job
from modules.tenancy.public import Workspace
from modules.realtime_events.public import RunEvent
from foundation.database.dependencies import db_session
from modules.authorization.public import project_access, actor, env_guard
from modules.audit.application.use_cases import audit
from modules.wallets.application.use_cases import settle
from modules.executions.application.use_cases import prepare_request, admit, public_job

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.post('/projects/{pid}/quote')
def quote(pid:str,body:Run,request:Request,environment:str='test',db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build');env_guard(request,db,user,environment)
    _,cost,size=prepare_request(db,project,environment,body,request.app.state.settings)
    return {'estimated_milli':cost,'maximum_milli':cost,'input_bytes':size,'environment':environment,'price_version':request.app.state.settings.price_version,'is_test':environment=='test','message':'The server revalidates price and available capacity on submission.'}


@router.post('/projects/{pid}/jobs',status_code=202)
def create_job(pid:str,body:Run,request:Request,environment:str='test',idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build');env_guard(request,db,user,environment)
    job,created=admit(db,request.app.state.settings,request.app.state.limiter,project,environment,body,idempotency_key,user.id);db.commit()
    return {'job':public_job(job),'created':created}


@router.get('/projects/{pid}/jobs')
def jobs(pid:str,request:Request,environment:str='test',limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0,le=10000),db=Depends(db_session)):
    project,_,member=project_access(db,pid,actor(request,db))
    if member.role=='billing': raise PublicError('FORBIDDEN')
    query=select(Job).where(Job.project_id==pid,Job.environment==environment)
    total=db.scalar(select(func.count(Job.id)).where(Job.project_id==pid,Job.environment==environment))
    return {'items':[public_job(j) for j in db.scalars(query.order_by(Job.created_at.desc(),Job.id.desc()).offset(offset).limit(limit))],'total':total,'offset':offset,'limit':limit}


@router.get('/projects/{pid}/jobs/{jid}')
def job_details(pid:str,jid:str,request:Request,db=Depends(db_session)):
    project,_,member=project_access(db,pid,actor(request,db))
    if member.role=='billing': raise PublicError('FORBIDDEN')
    job=db.scalar(select(Job).where(Job.id==jid,Job.project_id==pid))
    if not job: raise PublicError('NOT_FOUND')
    return {'job':public_job(job,member.role in ('owner','admin','developer')),'events':[{'id':e.id,'type':e.kind,'data':e.payload,'created_at':e.created_at} for e in db.scalars(select(RunEvent).where(RunEvent.job_id==jid).order_by(RunEvent.id).limit(300))]}


@router.post('/projects/{pid}/jobs/{jid}/cancel')
def cancel_job(pid:str,jid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);project,_,_=project_access(db,pid,user,'build')
    db.execute(update(Workspace).where(Workspace.id==project.workspace_id).values(name=Workspace.name))
    job=db.scalar(select(Job).where(Job.id==jid,Job.project_id==pid).with_for_update())
    if not job: raise PublicError('NOT_FOUND')
    if job.state not in ('queued','running'): raise PublicError('CONFLICT')
    job.cancel_requested=True
    if job.state=='queued':
        job.state='canceled';job.completed_at=now();settle(db,request.app.state.settings,job,0,False)
        db.add(RunEvent(workspace_id=project.workspace_id,job_id=jid,kind='job.canceled',payload={'state':'canceled'}))
    audit(db,user.id,'job.cancel_requested',jid,project.workspace_id);db.commit();return {'job':public_job(job)}

