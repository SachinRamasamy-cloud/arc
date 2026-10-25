"""Public contact; rate-limited and redacted before persistence."""
from fastapi import APIRouter, Request, Depends
from modules.support.interfaces.schemas import Ticket
from modules.support.public import SupportTicket
from foundation.database.dependencies import db_session
from foundation.crypto.security import redact_support
router=APIRouter(prefix='/api/public',tags=['public contact'])
@router.post('/contact',status_code=201)
def contact(body:Ticket,request:Request,db=Depends(db_session)):
    request.app.state.limiter.check([('contact:'+request.state.client_hash,3)])
    ticket=SupportTicket(email=str(body.email),subject=redact_support(body.subject),message=redact_support(body.message))
    db.add(ticket);db.commit()
    return {'reference':ticket.id,'message':'Your message has been received.'}
