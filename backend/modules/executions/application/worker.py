"""Durable execution. PostgreSQL state is authoritative. This release polls the durable queue."""
import hashlib,json,time,secrets
from sqlalchemy import select,update,func
from modules.executions.public import Job
from modules.realtime_events.public import RunEvent
from modules.tenancy.public import Workspace
from modules.files.public import FileObject
from foundation.clock import now
from modules.wallets.application.use_cases import settle
from modules.executions.application.use_cases import completion_notifications
from modules.processing_capabilities.public import run_native
from foundation.errors.public import PublicError

def claim(database,settings):
    with database.session() as db:
        # Oldest queued job wins. Per-project admission limits bound noisy projects.
        # Weighted tenant scheduling remains a release qualification item.
        candidate=db.scalar(select(Job).where(Job.state=='queued').order_by(Job.created_at,Job.id).limit(1).with_for_update(skip_locked=True))
        if not candidate: return None
        fence=secrets.token_hex(16)
        result=db.execute(update(Job).where(Job.id==candidate.id,Job.state=='queued').values(state='running',lease_token=fence,lease_until=now()+settings.job_lease_seconds,attempt=Job.attempt+1,started_at=now()))
        if result.rowcount!=1: return None
        db.add(RunEvent(workspace_id=candidate.workspace_id,job_id=candidate.id,kind='job.running',payload={'state':'running'}))
        db.commit();return candidate.id,fence

def event(database,jobid,fence,kind,payload):
    with database.session() as db:
        job=db.scalar(select(Job).where(Job.id==jobid,Job.lease_token==fence,Job.state=='running').with_for_update())
        if not job or job.cancel_requested: raise PublicError('CONFLICT')
        job.lease_until=now()+90
        db.add(RunEvent(workspace_id=job.workspace_id,job_id=jobid,kind=kind,payload=payload));db.commit()

def process_one(database,settings,store):
    claimed=claim(database,settings)
    if not claimed: return False
    jobid,fence=claimed;result=None;failure=None
    try:
        with database.session() as db:
            job=db.get(Job,jobid);payload=job.input_data
            data=payload.get('data')
            if job.file_id:
                file=db.get(FileObject,job.file_id)
                if not file or file.state!='ready': raise PublicError('UPLOAD_NOT_READY')
                raw=store.read(file.object_key,settings.max_file_bytes)
                if hashlib.sha256(raw).hexdigest()!=file.digest: raise PublicError('PROCESSING_FAILED')
                first=(payload.get('compiled') or [{'operation':payload['operation']}])[0]['operation']
                try: data=raw.decode('utf-8-sig') if first=='csv_to_json' else json.loads(raw)
                except (ValueError,UnicodeError): raise PublicError('INVALID_INPUT')
            steps=payload.get('compiled') or [{key:payload[key] for key in ('operation','required_fields','mappings','lowercase') if key in payload}]
        for index,step in enumerate(steps):
            event(database,jobid,fence,'node.running',{'node_id':step.get('node_id',f'step-{index}'),'stage':index+1,'stages':len(steps),'operation':step['operation']})
            result=run_native(settings,{'data':data,**{key:value for key,value in step.items() if key!='node_id'}})
            data=result['output']
            event(database,jobid,fence,'node.completed',{'node_id':step.get('node_id',f'step-{index}'),'stage':index+1,'records':result['records']})
    except PublicError as exc: failure=exc.code
    except Exception: failure='PROCESSING_FAILED'
    with database.session() as db:
        candidate=db.get(Job,jobid)
        if not candidate: return True
        db.execute(update(Workspace).where(Workspace.id==candidate.workspace_id).values(name=Workspace.name))
        job=db.scalar(select(Job).where(Job.id==jobid).with_for_update().execution_options(populate_existing=True))
        if not job or job.lease_token!=fence or job.state!='running': return True
        db.execute(update(Workspace).where(Workspace.id==job.workspace_id).values(name=Workspace.name))
        if job.cancel_requested:
            job.state='canceled';failure='CONFLICT'
        elif failure: job.state='failed';job.error_code=failure if failure in ('INVALID_INPUT','PROCESSING_TIMEOUT','UPLOAD_NOT_READY') else 'PROCESSING_FAILED'
        else:
            job.state='succeeded';job.result=result
            job.result_digest=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        settle(db,settings,job,job.reserved_milli if job.state=='succeeded' else 0,job.state=='succeeded')
        job.completed_at=now();job.lease_until=None
        db.add(RunEvent(workspace_id=job.workspace_id,job_id=job.id,kind='job.'+job.state,payload={'state':job.state,'billing_state':job.billing_state,'charged_milli':job.charged_milli,'error_code':job.error_code}))
        completion_notifications(db,settings,job);db.commit()
    return True

def recover_expired(database,settings):
    count=0
    with database.session() as db:
        candidates=list(db.execute(select(Job.id,Job.workspace_id).where(Job.state=='running',Job.lease_until<now()).limit(100)))
    for jid,wid in candidates:
        with database.session() as db:
            db.execute(update(Workspace).where(Workspace.id==wid).values(name=Workspace.name))
            job=db.scalar(select(Job).where(Job.id==jid,Job.state=='running',Job.lease_until<now()).with_for_update(skip_locked=True))
            if not job: continue
            job.lease_token=None
            if job.attempt>=2 or job.cancel_requested:
                job.state='canceled' if job.cancel_requested else 'failed';job.error_code='PROCESSING_FAILED';job.completed_at=now()
                settle(db,settings,job,0,False);completion_notifications(db,settings,job)
            else: job.state='queued'
            db.add(RunEvent(workspace_id=job.workspace_id,job_id=job.id,kind='job.'+job.state,payload={'state':job.state,'recovered':True}))
            db.commit();count+=1
    return count
