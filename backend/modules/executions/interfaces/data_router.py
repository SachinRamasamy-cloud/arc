"""executions-owned data HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends, Header
from sqlalchemy import select
from foundation.errors.public import PublicError
from modules.executions.interfaces.schemas import Run
from modules.executions.public import Job
from foundation.database.dependencies import db_session
from modules.api_credentials.application.identity import identify
from modules.realtime_events.interfaces.streams import stream_response
from modules.executions.application.use_cases import admit, public_job

router=APIRouter(prefix='/v1',tags=['product API'])

@router.post('/jobs',status_code=202)
def submit(body:Run,request:Request,idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    identity=identify(request,db,'jobs:write')
    job,created=admit(db,request.app.state.settings,request.app.state.limiter,identity.project,identity.key.environment,body,idempotency_key,identity.key.id);db.commit()
    return {'job':public_job(job),'created':created}


@router.get('/jobs/{jid}')
def inspect(jid:str,request:Request,db=Depends(db_session)):
    identity=identify(request,db,'jobs:read')
    job=db.scalar(select(Job).where(Job.id==jid,Job.project_id==identity.project.id,Job.environment==identity.key.environment))
    if not job: raise PublicError('NOT_FOUND')
    db.commit();return {'job':public_job(job,True)}


@router.post('/workflows/{flowid}/run',status_code=202)
def run_workflow(flowid:str,body:Run,request:Request,idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    identity=identify(request,db,'jobs:write')
    body=body.model_copy(update={'operation':'workflow','workflow_id':flowid})
    job,created=admit(db,request.app.state.settings,request.app.state.limiter,identity.project,identity.key.environment,body,idempotency_key,identity.key.id);db.commit()
    return {'job':public_job(job),'created':created}

