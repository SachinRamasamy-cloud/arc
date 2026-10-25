"""support-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from foundation.crypto.security import redact_support
from modules.support.interfaces.schemas import Ticket
from modules.support.public import SupportTicket
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/support')
def tickets(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user)
    return {'items':[{k:getattr(t,k) for k in ('id','subject','message','state','reply','created_at')} for t in db.scalars(select(SupportTicket).where(SupportTicket.workspace_id==wid,SupportTicket.user_id==user.id).order_by(SupportTicket.created_at.desc()).limit(50))]}


@router.post('/workspaces/{wid}/support',status_code=201)
def create_ticket(wid:str,body:Ticket,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user)
    request.app.state.limiter.check([('ticket:'+user.id,5)])
    ticket=SupportTicket(workspace_id=wid,user_id=user.id,email=user.email,subject=redact_support(body.subject),message=redact_support(body.message));db.add(ticket);db.commit();return {'id':ticket.id,'state':'open'}

