"""notifications application use cases. Existing v0.2 behavior retained."""
import hashlib,json,math,secrets,time
from datetime import datetime,timezone
from sqlalchemy import select,update,func
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import seal
from foundation.errors.public import PublicError
from modules.identity.public import User
from modules.notifications.public import Mail, Notification
from modules.tenancy.public import Membership

def queue_mail(db,settings,email,subject,body):
    db.add(Mail(recipient=email,subject=subject,body_encrypted=seal(body,settings,'mail')))


def notify(db,settings,wid,category,title,message,reference,link='overview'):
    for member in db.scalars(select(Membership).where(Membership.workspace_id==wid)):
        if category=='billing' and member.role not in ('owner','admin','billing'): continue
        if category=='processing' and member.role=='billing': continue
        key=reference+':'+member.user_id
        if db.scalar(select(Notification.id).where(Notification.dedupe_key==key)): continue
        db.add(Notification(workspace_id=wid,user_id=member.user_id,category=category,title=title,message=message,dedupe_key=key,link=link))
        user=db.get(User,member.user_id)
        preferences=user.preferences or {}
        should_email=category in ('security','billing') or (category=='processing' and preferences.get('job_email',False)) or (category=='usage' and preferences.get('usage_email',True))
        if should_email: queue_mail(db,settings,user.email,title,message+'\n\nOpen your workspace: '+settings.portal_origin)
