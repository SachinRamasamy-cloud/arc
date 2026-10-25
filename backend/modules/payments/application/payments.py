import hashlib,hmac,json,time
import httpx
from sqlalchemy import select,update
from modules.tenancy.public import Workspace
from modules.payments.public import Payment, StripeEvent
from modules.wallets.public import Allowance, Wallet
from modules.pricing.public import PlanPrice
from foundation.clock import now
from modules.wallets.application.use_cases import grant
from modules.notifications.application.use_cases import notify
from modules.audit.application.use_cases import audit
from foundation.errors.public import PublicError
from modules.metering.application.accounting import lock_workspace
from modules.invoices.application.billing_views import sync_invoice

class StripeGateway:
    def __init__(self,settings,transport=None):
        self.settings=settings;self.transport=transport
    def request(self,method,path,data=None,idempotency_key=None):
        if not self.settings.stripe_secret_key: raise PublicError('INTEGRATION_UNAVAILABLE')
        headers={'Authorization':'Bearer '+self.settings.stripe_secret_key,'Stripe-Version':'2025-06-30.basil'}
        if idempotency_key: headers['Idempotency-Key']=idempotency_key
        try:
            with httpx.Client(timeout=15,transport=self.transport,follow_redirects=False) as client:
                response=client.request(method,'https://api.stripe.com'+path,headers=headers,**({'params':data} if method=='GET' else {'data':data}))
            if response.status_code>=400: raise PublicError('SERVICE_UNAVAILABLE')
            return response.json()
        except (httpx.HTTPError,ValueError): raise PublicError('SERVICE_UNAVAILABLE')
    def ensure_customer(self,db,workspace):
        """Commit the stable customer link before a checkout can emit invoice events."""
        if not workspace.stripe_customer:
            customer=self.request('POST','/v1/customers',{'metadata[workspace_id]':workspace.id},'customer:'+workspace.id)
            if not isinstance(customer.get('id'),str) or not customer['id'].startswith('cus_'):
                raise PublicError('SERVICE_UNAVAILABLE')
            workspace.stripe_customer=customer['id'];db.commit()
        return workspace.stripe_customer
    def checkout(self,workspace,payment):
        settings=self.settings
        price=payment.price_id or (settings.stripe_credit_price_id if payment.kind=='credits' else settings.stripe_plan_price_id)
        if not price: raise PublicError('INTEGRATION_UNAVAILABLE')
        # The server selects the price and grant size. The browser cannot supply amounts or workspace metadata.
        data={'mode':'payment' if payment.kind=='credits' else 'subscription','line_items[0][price]':price,'line_items[0][quantity]':'1','success_url':settings.portal_origin+'/billing?checkout=return','cancel_url':settings.portal_origin+'/billing?checkout=canceled','client_reference_id':payment.id,'metadata[payment_id]':payment.id,'metadata[workspace_id]':workspace.id}
        if workspace.stripe_customer: data['customer']=workspace.stripe_customer
        elif payment.kind=='credits': data['customer_creation']='always'
        if payment.kind=='subscription': data['subscription_data[metadata][workspace_id]']=workspace.id
        return self.request('POST','/v1/checkout/sessions',data,'checkout:'+payment.id)
    def validate_price(self,payment):
        price_id=payment.price_id
        if not price_id: raise PublicError('INTEGRATION_UNAVAILABLE')
        price=self.request('GET','/v1/prices/'+price_id)
        if price.get('id')!=price_id or not price.get('active') or price.get('currency')!=payment.currency or price.get('unit_amount')!=payment.amount_minor:
            raise PublicError('INTEGRATION_UNAVAILABLE')
        recurring=price.get('recurring')
        if payment.kind=='subscription':
            if not recurring or recurring.get('interval')!='month' or recurring.get('interval_count',1)!=1: raise PublicError('INTEGRATION_UNAVAILABLE')
        elif recurring: raise PublicError('INTEGRATION_UNAVAILABLE')
        return True

    def portal(self,workspace):
        if not workspace.stripe_customer: raise PublicError('CONFLICT')
        return self.request('POST','/v1/billing_portal/sessions',{'customer':workspace.stripe_customer,'return_url':self.settings.portal_origin+'/billing'})

def verify_event(raw,signature,secret,clock=None):
    if not secret: raise PublicError('INTEGRATION_UNAVAILABLE')
    try:
        parts={}
        for item in signature.split(','):
            key,value=item.split('=',1);parts.setdefault(key,[]).append(value)
        timestamp=int(parts['t'][0]);stamp=time.time() if clock is None else clock
        if abs(stamp-timestamp)>300: raise ValueError()
        expected=hmac.new(secret.encode(),str(timestamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(expected,v) for v in parts.get('v1',[])): raise ValueError()
        event=json.loads(raw)
        if not isinstance(event,dict) or not isinstance(event.get('id'),str) or not event['id'].startswith('evt_'): raise ValueError()
        return event
    except (ValueError,KeyError,TypeError,UnicodeError): raise PublicError('INVALID_INPUT')

def handle_event(db,settings,gateway,event):
    kind=event.get('type','');obj=event.get('data',{}).get('object',{})
    if not isinstance(obj,dict): raise PublicError('INVALID_INPUT')
    workspace=db.scalar(select(Workspace).where(Workspace.stripe_customer==obj.get('customer'))) if obj.get('customer') else None
    if not workspace and kind.startswith('checkout.session.'):
        payment=db.scalar(select(Payment).where(Payment.checkout_id==obj.get('id')))
        if payment: workspace=db.get(Workspace,payment.workspace_id)
    if workspace: lock_workspace(db,workspace.id)
    if db.get(StripeEvent,event['id']): return False
    # Event identity and financial effects share one transaction under the workspace lock.

    if bool(event.get('livemode',False))!=settings.stripe_secret_key.startswith('sk_live_'): raise PublicError('INVALID_INPUT')
    if kind in ('checkout.session.completed','checkout.session.async_payment_succeeded'):
        payment=db.scalar(select(Payment).where(Payment.checkout_id==obj.get('id')))
        if not payment:
            # A provider callback can beat the response that links checkout_id.
            payment=db.get(Payment,obj.get('client_reference_id',''))
            if not payment or payment.checkout_id not in (None,obj.get('id')): raise PublicError('INVALID_INPUT')
            lock_workspace(db,payment.workspace_id)
            payment.checkout_id=obj.get('id')

        if obj.get('client_reference_id')!=payment.id or obj.get('metadata',{}).get('workspace_id')!=payment.workspace_id: raise PublicError('INVALID_INPUT')
        db.execute(update(Workspace).where(Workspace.id==payment.workspace_id).values(name=Workspace.name))
        db.flush();db.refresh(payment)
        if payment.state in ('created','pending','unpaid','expired') and obj.get('payment_status')=='paid':
            if obj.get('currency')!=payment.currency or int(obj.get('amount_subtotal',-1))!=payment.amount_minor: raise PublicError('INVALID_INPUT')
            workspace=db.get(Workspace,payment.workspace_id)
            customer=obj.get('customer')
            if workspace.stripe_customer and customer!=workspace.stripe_customer: raise PublicError('INVALID_INPUT')
            if customer: workspace.stripe_customer=customer
            payment.state='paid';payment.payment_intent=obj.get('payment_intent')
            if payment.kind=='credits': grant(db,workspace.id,'live',payment.credit_milli,'stripe:'+payment.checkout_id,'Purchased credit pack')
            notify(db,settings,workspace.id,'billing','Payment confirmed','Your payment was verified. Open Billing for the details.','payment:'+payment.id,'billing')
    elif kind in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
        workspace=db.scalar(select(Workspace).where(Workspace.stripe_customer==obj.get('customer')))
        if workspace:
            # Fetch current state rather than assuming event delivery order is chronological.
            current=gateway.request('GET','/v1/subscriptions/'+obj['id'])
            if current.get('customer')!=workspace.stripe_customer: raise PublicError('INVALID_INPUT')
            workspace.subscription_id=current['id'];workspace.subscription_status=current['status']
            period=current.get('current_period_end')
            if not period:
                items=current.get('items',{}).get('data',[]);period=items[0].get('current_period_end') if items else None
            workspace.period_end=period
            items=current.get('items',{}).get('data',[])
            workspace.period_start=current.get('current_period_start') or (items[0].get('current_period_start') if items else None)
            workspace.cancel_at_period_end=bool(current.get('cancel_at_period_end',False))
            workspace.subscription_price=items[0].get('price',{}).get('id') if items else None

            notify(db,settings,workspace.id,'billing','Subscription updated','Your subscription status is '+workspace.subscription_status+'.','subscription:'+event['id'],'billing')
    elif kind=='invoice.paid':
        workspace=db.scalar(select(Workspace).where(Workspace.stripe_customer==obj.get('customer')))
        if workspace and obj.get('status')=='paid':
            sync_invoice(db,workspace,obj)
            lines=obj.get('lines',{}).get('data',[])
            # Legacy selected price can be registered once; historical rows never
            # adopt the allowance of a newly published price.
            from modules.invoices.application.billing_views import plan_snapshot
            if settings.stripe_plan_price_id and not db.get(PlanPrice,settings.stripe_plan_price_id): plan_snapshot(db,settings)
            eligible=[line for line in lines if db.get(PlanPrice,line.get('price',{}).get('id') or line.get('pricing',{}).get('price_details',{}).get('price') or '')]
            # A plan-change/proration invoice must not mint another full monthly allowance.
            eligible=[line for line in eligible if not line.get('proration',False) and not line.get('parent',{}).get('subscription_item_details',{}).get('proration',False)]
            if len(eligible)==1 and obj.get('billing_reason') in ('subscription_create','subscription_cycle'):
                period=eligible[0].get('period',{}).get('end')
                subscription=obj.get('subscription') or obj.get('parent',{}).get('subscription_details',{}).get('subscription')
                selected=eligible[0].get('price',{}).get('id') or eligible[0].get('pricing',{}).get('price_details',{}).get('price')
                price=db.get(PlanPrice,selected)
                if subscription and period and period>now() and workspace.subscription_id in (None,subscription):
                    db.execute(update(Workspace).where(Workspace.id==workspace.id).values(name=Workspace.name))
                    workspace.subscription_id=subscription
                    if period>=(workspace.period_end or 0):
                        workspace.period_start=eligible[0].get('period',{}).get('start') or workspace.period_start
                        workspace.period_end=period;workspace.subscription_price=selected
                    allowance_id='period:'+hashlib.sha256(f'{workspace.id}:{subscription}:{period}'.encode()).hexdigest()
                    if not db.get(Allowance,allowance_id): db.add(Allowance(id=allowance_id,workspace_id=workspace.id,balance_milli=price.included_milli,held_milli=0,expires_at=period))
            notify(db,settings,workspace.id,'billing','Invoice paid','Your paid invoice is available in the billing portal.','invoice:'+obj['id'],'billing')
    elif kind in ('invoice.payment_failed','invoice.payment_action_required'):
        workspace=db.scalar(select(Workspace).where(Workspace.stripe_customer==obj.get('customer')))
        if workspace:
            sync_invoice(db,workspace,obj)
            from modules.invoices.public import Invoice
            previous=db.get(Invoice,obj.get('id'))
            if previous and previous.status=='paid':
                db.add(StripeEvent(id=event['id'],kind=kind,state='processed'));return True
            notify(db,settings,workspace.id,'billing','Payment needs attention','Open Billing to review your payment method. Existing files follow the published retention policy.','invoice-failure:'+obj['id'],'billing')
    elif kind in ('charge.refunded','charge.dispute.created'):
        payment=db.scalar(select(Payment).where(Payment.payment_intent==obj.get('payment_intent')))
        if payment:
            db.execute(update(Wallet).where(Wallet.workspace_id==payment.workspace_id,Wallet.environment=='live').values(frozen=True))
            payment.state='review_required'
            notify(db,settings,payment.workspace_id,'billing','Billing review required','New paid work is paused while a payment adjustment is reviewed. Your ledger history is preserved.','adjustment:'+event['id'],'billing')
    db.add(StripeEvent(id=event['id'],kind=kind,state='processed'))
    return True
