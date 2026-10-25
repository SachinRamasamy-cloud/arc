"""Customer application's Bearer-key SSE endpoint."""
from fastapi import APIRouter, Request
from modules.realtime_events.interfaces.streams import stream_response
router=APIRouter(prefix='/v1',tags=['live events'])
@router.get('/jobs/{jid}/events')
def subscribe(jid:str,request:Request):
    return stream_response(request,jid,public=True)
