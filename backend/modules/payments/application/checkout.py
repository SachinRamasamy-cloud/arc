"""Durable Stripe checkout admission and provider retry reconciliation."""
from sqlalchemy import select
from urllib.parse import urlparse
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.payments.public import Payment
from modules.metering.application.accounting import lock_workspace
from modules.payments.domain.checkout_policy import checkout_request_key

def create_checkout(db,settings,stripe,workspace,kind,idempotency_key):
    wid=workspace.id
    request_key=checkout_request_key(wid,idempotency_key)
    lock_workspace(db,wid)
    payment=db.scalar(select(Payment).where(Payment.request_key==request_key))
    if payment:
        if payment.kind!=kind: raise PublicError('CONFLICT')
        if payment.state=='paid': return {'payment_id':payment.id,'state':'paid','url':None}
        if payment.state in ('review_required','failed','expired'): return {'payment_id':payment.id,'state':payment.state,'url':None}
        if payment.checkout_url and (payment.checkout_expires_at or 0)>now():
            return {'url':payment.checkout_url,'payment_id':payment.id,'state':payment.state}
        if payment.checkout_id:
            payment.state='expired';db.commit();return {'payment_id':payment.id,'state':'expired','url':None}
    else:
        if kind=='subscription':
            if workspace.subscription_status in ('active','trialing','past_due','incomplete','unpaid','paused'): raise PublicError('CONFLICT')
            pending=db.scalar(select(Payment.id).where(Payment.workspace_id==wid,Payment.kind=='subscription',Payment.state.in_(['created','pending']),Payment.checkout_expires_at>now()))
            if pending: raise PublicError('CONFLICT')
        if kind=='subscription':
            from modules.invoices.application.billing_views import plan_snapshot
            plan_snapshot(db,settings)
        payment=Payment(workspace_id=wid,kind=kind,request_key=request_key,
            price_id=settings.stripe_credit_price_id if kind=='credits' else settings.stripe_plan_price_id,
            currency=settings.currency,amount_minor=settings.stripe_credit_pack_minor if kind=='credits' else settings.stripe_plan_minor,
            credit_milli=settings.stripe_credit_pack_milli if kind=='credits' else 0,checkout_expires_at=now()+1800)
        db.add(payment);db.flush()
    # Durable attempt BEFORE provider IO. Retrying this key reuses the same Stripe request.
    db.commit()
    stripe.validate_price(payment)
    stripe.ensure_customer(db,workspace)
    result=stripe.checkout(workspace,payment)
    url=result.get('url','');host=urlparse(url)
    if host.scheme!='https' or host.hostname!='checkout.stripe.com' or not str(result.get('id','')).startswith('cs_'): raise PublicError('SERVICE_UNAVAILABLE')
    lock_workspace(db,wid);db.refresh(payment)
    payment.checkout_id=result['id'];payment.checkout_url=url;payment.checkout_expires_at=result.get('expires_at') or now()+1800
    if payment.state=='created': payment.state='pending'
    db.commit();return {'url':url,'payment_id':payment.id,'state':payment.state}

