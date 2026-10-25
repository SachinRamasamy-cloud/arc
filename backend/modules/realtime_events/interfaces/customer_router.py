"""Customer console subscriptions; session authorization is enforced by the stream service."""
from fastapi import APIRouter, Request
from modules.realtime_events.interfaces.streams import stream_response
router=APIRouter(prefix='/api/console/v1',tags=['live events'])
@router.get('/projects/{pid}/jobs/{jid}/events')
def subscribe(pid:str,jid:str,request:Request):
    return stream_response(request,jid,pid)
