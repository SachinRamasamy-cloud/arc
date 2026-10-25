"""platform_operations-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func
from foundation.clock import now
from modules.executions.public import Job
from modules.notifications.public import Mail
from modules.tenancy.public import Workspace
from modules.identity.public import User
from modules.webhooks.public import WebhookDelivery
from modules.support.public import SupportTicket
from foundation.database.dependencies import db_session
from modules.authorization.public import staff

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/overview')
def overview(request:Request,db=Depends(db_session)):
    user=staff(request,db)
    return {'customers':db.scalar(select(func.count(Workspace.id))),'accounts':db.scalar(select(func.count(User.id)).where(User.staff.is_(False))),
            'jobs':dict(db.execute(select(Job.state,func.count(Job.id)).group_by(Job.state)).all()),
            'support_open':db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.state=='open')),
            'pending_mail':db.scalar(select(func.count(Mail.id)).where(Mail.state=='pending')),
            'failed_deliveries':db.scalar(select(func.count(WebhookDelivery.id)).where(WebhookDelivery.state=='failed')),
            'deployment':{'mode':request.app.state.settings.env,'live_enabled':request.app.state.settings.live_enabled,'storage':request.app.state.settings.storage_mode,'redis':bool(request.app.state.settings.redis_url)},'updated_at':now()}


@router.get('/release')
def release(request:Request,db=Depends(db_session)):
    staff(request,db);s=request.app.state.settings
    return {'checks':[
        {'name':'Approved legal documents','passed':s.legal_approved},
        {'name':'Approved pricing','passed':s.pricing_approved},
        {'name':'Security deployment qualification','passed':s.security_qualified},
        {'name':'Backup restoration qualification','passed':s.backup_qualified},
        {'name':'PostgreSQL','passed':s.database_url.startswith('postgresql')},
        {'name':'Redis','passed':bool(s.redis_url)},
        {'name':'Private R2 configured','passed':s.storage_mode=='r2'},
        {'name':'Transactional email configured','passed':s.mail_mode=='smtp'},
        {'name':'Stripe signing secret configured','passed':bool(s.stripe_webhook_secret)},
        {'name':'Live API access','passed':s.live_enabled}],
        'message':'Configuration checks do not substitute for the documented release tests.'}

