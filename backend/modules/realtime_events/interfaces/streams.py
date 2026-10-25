import asyncio,json,time
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from modules.executions.public import Job
from modules.realtime_events.public import RunEvent
from foundation.ids import uid
from foundation.clock import now
from modules.authorization.application.access import current_user, project_access, api_identity
from foundation.errors.public import PublicError

def stream_response(request:Request,jobid:str,project_id=None,public=False):
    database=request.app.state.database
    def authorized(db):
        if public:
            identity=api_identity(request,db,'jobs:read')
            job=db.scalar(select(Job).where(Job.id==jobid,Job.project_id==identity.project.id,Job.environment==identity.key.environment))
        else:
            user,session=current_user(request,db)
            project,_,member=project_access(db,project_id,user)
            if member.role=='billing': raise PublicError('FORBIDDEN')
            job=db.scalar(select(Job).where(Job.id==jobid,Job.project_id==project.id))
        if not job: raise PublicError('NOT_FOUND')
        return job
    raw=request.headers.get('last-event-id') or request.query_params.get('cursor','0')
    try: cursor=int(raw)
    except ValueError: raise PublicError('INVALID_INPUT')
    if cursor<0: raise PublicError('INVALID_INPUT')
    with database.session() as db:
        job=authorized(db);wid=job.workspace_id
        if cursor and not db.scalar(select(RunEvent.id).where(RunEvent.id==cursor,RunEvent.job_id==jobid)): raise PublicError('EVENT_CURSOR_EXPIRED')
    slot=uid('sse');bucket='streams:{'+wid+'}'
    request.app.state.stream_gate.acquire(bucket,slot)
    def read_batch(after):
        with database.session() as db:
            job=authorized(db)
            events=[{'id':e.id,'kind':e.kind,'payload':e.payload} for e in db.scalars(select(RunEvent).where(RunEvent.job_id==jobid,RunEvent.id>after).order_by(RunEvent.id).limit(100))]
            return events,job.state
    async def generate():
        nonlocal cursor
        heartbeat=time.monotonic();started=heartbeat
        try:
            yield 'retry: 2000\n\n'
            while time.monotonic()-started<600:
                if await request.is_disconnected(): break
                try: events,state=await asyncio.to_thread(read_batch,cursor)
                except PublicError as exc:
                    yield 'event: stream.error\ndata: '+json.dumps({'code':exc.code})+'\n\n';break
                for entry in events:
                    cursor=entry['id']
                    yield f"id: {cursor}\nevent: {entry['kind']}\ndata: {json.dumps(entry['payload'],separators=(',',':'))}\n\n"
                if state in ('succeeded','failed','canceled') and len(events)<100:
                    yield 'event: stream.complete\ndata: {}\n\n';break
                if time.monotonic()-heartbeat>10:
                    request.app.state.stream_gate.renew(bucket,slot)
                    yield ': heartbeat\n\n';heartbeat=time.monotonic()
                await asyncio.sleep(0.5)
        finally: request.app.state.stream_gate.release(bucket,slot)
    return StreamingResponse(generate(),media_type='text/event-stream',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
