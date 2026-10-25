"""support-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from foundation.errors.public import PublicError
from foundation.crypto.security import redact_support
from modules.support.interfaces.schemas import Reply
from modules.support.public import SupportTicket
from foundation.database.dependencies import db_session
from modules.authorization.public import staff
from modules.audit.application.use_cases import audit
from modules.notifications.application.use_cases import queue_mail

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/support')
def support(request:Request,db=Depends(db_session)):
    user=staff(request,db)
    audit(db,user.id,'operator.support_listed','support');db.commit()
    return {'items':[{k:getattr(t,k) for k in ('id','email','subject','message','state','reply','created_at')} for t in db.scalars(select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(100))]}


@router.patch('/support/{tid}')
def reply(tid:str,body:Reply,request:Request,db=Depends(db_session)):
    user=staff(request,db);ticket=db.get(SupportTicket,tid)
    if not ticket: raise PublicError('NOT_FOUND')
    from foundation.crypto.security import redact_support
    ticket.reply=redact_support(body.reply);ticket.state=body.state
    queue_mail(db,request.app.state.settings,ticket.email,'Reply to support request '+tid,ticket.reply)
    audit(db,user.id,'operator.support_replied',tid,ticket.workspace_id);db.commit();return {'state':ticket.state}

