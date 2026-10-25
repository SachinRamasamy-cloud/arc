"""Durable notifications and bounded HTTPS delivery. Do not log payloads or secrets."""
import json,time,smtplib,ssl
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlunsplit
import httpx
from sqlalchemy import select
from modules.notifications.public import Mail
from modules.webhooks.public import WebhookEndpoint, WebhookDelivery
from modules.tenancy.public import Workspace
from modules.projects.public import Project
from modules.files.public import FileObject
from modules.executions.public import Job
from modules.uploads.public import MultipartUpload
from modules.application_data.public import MutationReceipt
from foundation.clock import now
from foundation.crypto.security import unseal, validate_webhook_url, webhook_signature
from modules.notifications.application.use_cases import notify

def deliver_mail(database,settings):
    with database.session() as db:
        mail=db.scalar(select(Mail).where(Mail.state=='pending',Mail.due_at<=now()).order_by(Mail.created_at).limit(1).with_for_update(skip_locked=True))
        if not mail: return False
        mail.attempts+=1
        try:
            body=unseal(mail.body_encrypted,settings,'mail')
            message=EmailMessage();message['To']=mail.recipient;message['From']=settings.mail_from or 'local@arc.example';message['Subject']=mail.subject;message.set_content(body)
            if settings.mail_mode=='local':
                folder=Path('.local/mail');folder.mkdir(parents=True,exist_ok=True)
                path=folder/(mail.id+'.eml');path.write_text(str(message));path.chmod(0o600)
                mail.state='saved_locally'
            else:
                with smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    if settings.smtp_user: smtp.login(settings.smtp_user,settings.smtp_password)
                    smtp.send_message(message)
                mail.state='accepted' # Accepted by SMTP, not proof that the user received/read it.
        except Exception:
            mail.state='failed' if mail.attempts>=5 else 'pending';mail.due_at=now()+min(3600,30*2**mail.attempts)
        db.commit();return True

def deliver_webhook(database,settings,transport=None):
    with database.session() as db:
        delivery=db.scalar(select(WebhookDelivery).where(WebhookDelivery.state=='pending',WebhookDelivery.due_at<=now()).order_by(WebhookDelivery.due_at).limit(1).with_for_update(skip_locked=True))
        if not delivery: return False
        endpoint=db.get(WebhookEndpoint,delivery.endpoint_id)
        if not endpoint or not endpoint.enabled:
            delivery.state='disabled';db.commit();return True
        delivery.attempts+=1
        try:
            parts,addresses=validate_webhook_url(endpoint.url,settings.allow_local_webhooks)
            address=addresses[0];host='['+address+']' if ':' in address else address
            target=urlunsplit(('https',host,parts.path or '/',parts.query,''))
            body=json.dumps(delivery.payload,separators=(',',':')).encode();stamp=now()
            signature=webhook_signature(unseal(endpoint.encrypted_secret,settings,'webhook'),body,stamp)
            # Pin the validated IP. SNI and certificate verification remain bound to original hostname.
            with httpx.Client(timeout=10,follow_redirects=False,transport=transport,trust_env=False) as client:
                with client.stream('POST',target,content=body,headers={'Host':parts.hostname,'Content-Type':'application/json','Arc-Signature':signature,'Arc-Event-ID':delivery.event_id},extensions={'sni_hostname':parts.hostname}) as response:
                    delivery.status_code=response.status_code
                    # Never persist an untrusted response body. Read at most a small diagnostic budget.
                    read=0
                    for chunk in response.iter_bytes():
                        read+=len(chunk)
                        if read>=4096: break
                    if 200<=response.status_code<300: delivery.state='delivered'
                    else: raise ValueError('delivery rejected')
        except Exception:
            delivery.state='failed' if delivery.attempts>=5 else 'pending'
            delivery.due_at=now()+min(3600,15*2**delivery.attempts)
        db.commit();return True

def reminders(database,settings):
    with database.session() as db:
        for workspace in db.scalars(select(Workspace).where(Workspace.period_end>now(),Workspace.subscription_status.in_(['active','trialing']),Workspace.cancel_at_period_end.is_(False))):
            remaining=workspace.period_end-now()
            for days in (7,1):
                if (days-1)*86400<remaining<=days*86400:
                    notify(db,settings,workspace.id,'billing','Upcoming subscription renewal',f'Your subscription renews in approximately {days} day(s). Open Billing to review your plan and payment method.',f'renew:{workspace.subscription_id}:{workspace.period_end}:{days}','billing')
        db.commit()

def cleanup_expired(database,settings,store):
    with database.session() as db:
        from sqlalchemy import delete
        db.execute(delete(MutationReceipt).where(MutationReceipt.expires_at<now()))
        files=list(db.scalars(select(FileObject).where(FileObject.expires_at<now(),FileObject.state.in_(['pending','ready'])).limit(100)))
        for file in files:
            active=db.scalar(select(Job.id).where(Job.file_id==file.id,Job.state.in_(['queued','running'])).limit(1))
            if active: continue
            try:
                from modules.metering.application.accounting import close_storage_interval
                multipart=db.get(MultipartUpload,file.id)
                if multipart and multipart.state=='uploading':
                    if store.client: store.client.abort_multipart_upload(Bucket=settings.r2_bucket,Key=file.object_key,UploadId=multipart.provider_id)
                    else:
                        import shutil
                        shutil.rmtree(store.path('multipart/'+multipart.provider_id),ignore_errors=True)
                    multipart.state='aborted'
                store.delete(file.object_key);file.state='expired';close_storage_interval(db,file.id)
            except Exception: continue
        # Inline output records are transient; erase output payload, preserve minimal usage/evidence metadata.
        # Include failed/canceled input payloads too; failure must not bypass retention.
        for job in db.scalars(select(Job).join(Project,Project.id==Job.project_id).where(Job.completed_at.is_not(None),Job.payload_deleted_at.is_(None),Job.completed_at+Project.retention_hours*3600<now(),Job.state.in_(['succeeded','failed','canceled'])).limit(100)):
            job.result=None;job.input_data={};job.payload_deleted_at=now()
        db.commit()
