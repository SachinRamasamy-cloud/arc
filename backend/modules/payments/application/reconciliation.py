"""Bounded provider recovery plus read-only local accounting checks.

Provider reads happen before each accounting transaction. Does not automatically
refund disputes, overwrite balances or attempt card charges.
"""
import hashlib
import json
from sqlalchemy import select,func
from modules.tenancy.public import Workspace
from modules.wallets.public import Wallet, Ledger, Allowance, CreditAllocation
from modules.executions.public import Job
from modules.metering.public import UsageEvent
from modules.payments.public import Payment
from foundation.clock import now
from modules.metering.application.accounting import lock_workspace
from foundation.errors.public import PublicError
from modules.payments.application.payments import handle_event
from modules.audit.application.use_cases import audit


def accounting_report(db,workspace_id):
    lock_workspace(db,workspace_id)
    wallets=[]
    for wallet in db.scalars(select(Wallet).where(Wallet.workspace_id==workspace_id)):
        ledger_total=db.scalar(select(func.coalesce(func.sum(Ledger.amount_milli),0)).where(Ledger.workspace_id==workspace_id,Ledger.environment==wallet.environment))
        reserved=db.scalar(select(func.coalesce(func.sum(Job.reserved_paid_milli),0)).where(Job.workspace_id==workspace_id,Job.environment==wallet.environment,Job.billing_state=='reserved'))
        wallets.append({'environment':wallet.environment,'balance_milli':wallet.balance_milli,'ledger_milli':int(ledger_total),
            'held_milli':wallet.held_milli,'expected_held_milli':int(reserved),
            'balance_matches':wallet.balance_milli==ledger_total,'reservations_match':wallet.held_milli==reserved})
    missing=db.scalar(select(func.count(Job.id)).where(Job.workspace_id==workspace_id,Job.billing_state=='settled',Job.state=='succeeded',
        ~select(UsageEvent.id).where(UsageEvent.reference=='job:'+Job.id).exists()))
    bad_allowances=[]
    for allowance in db.scalars(select(Allowance).where(Allowance.workspace_id==workspace_id)):
        allocations=db.scalar(select(func.coalesce(func.sum(CreditAllocation.reserved_milli),0)).join(Job,Job.id==CreditAllocation.job_id).where(CreditAllocation.allowance_id==allowance.id,Job.billing_state=='reserved'))
        legacy=db.scalar(select(func.coalesce(func.sum(Job.reserved_allowance_milli),0)).where(Job.allowance_id==allowance.id,Job.billing_state=='reserved',~select(CreditAllocation.id).where(CreditAllocation.job_id==Job.id).exists()))
        if allowance.held_milli!=allocations+legacy:bad_allowances.append(allowance.id)
    return {'workspace_id':workspace_id,'wallets':wallets,'missing_processing_usage':missing,
        'allowance_reservation_mismatches':bad_allowances,'balanced':all(w['balance_matches'] and w['reservations_match'] for w in wallets) and not missing and not bad_allowances,
        'checked_at':now(),'policy':'Read-only diagnostic. Differences require investigation, not an automatic balance rewrite.'}


def reconcile_workspace(database,settings,gateway,workspace_id,max_pages=5):
    """Recover missing Checkout/invoice effects from authenticated Stripe reads.

    A bounded batch returns has_more when invoices exceed the scan budget. Operators
    must resolve that condition, not present partial reconciliation as complete.
    """
    if not 1<=max_pages<=20:raise PublicError('INVALID_INPUT')
    with database.session() as db:
        workspace=db.get(Workspace,workspace_id)
        if not workspace:raise PublicError('NOT_FOUND')
        customer,subscription=workspace.stripe_customer,workspace.subscription_id
        attempts=list(db.execute(select(Payment.id,Payment.checkout_id).where(Payment.workspace_id==workspace_id,Payment.checkout_id.is_not(None),Payment.state.in_(['created','pending','unpaid','expired'])).limit(100)))
    if not customer:raise PublicError('INTEGRATION_UNAVAILABLE')
    count=0
    def apply(kind,obj):
        nonlocal count
        if obj.get('customer')!=customer:raise PublicError('INVALID_INPUT')
        event={'id':'evt_reconcile_'+hashlib.sha256((kind+json.dumps(obj,sort_keys=True,separators=(',',':'))).encode()).hexdigest(),
               'type':kind,'livemode':bool(obj.get('livemode',settings.stripe_secret_key.startswith('sk_live_'))),'data':{'object':obj}}
        # Reuse a freshly retrieved subscription rather than making provider calls
        # while holding the database's workspace/accounting lock.
        class Snapshot:
            def request(self,method,path,*args,**kwargs):
                if kind.startswith('customer.subscription.') and method=='GET' and path=='/v1/subscriptions/'+obj['id']:return obj
                raise PublicError('INTERNAL_ERROR')
        with database.session() as db:
            if handle_event(db,settings,Snapshot(),event):count+=1
            db.commit()
    if subscription:
        obj=gateway.request('GET','/v1/subscriptions/'+subscription);apply('customer.subscription.updated',obj)
    for payment_id,checkout_id in attempts:
        obj=gateway.request('GET','/v1/checkout/sessions/'+checkout_id)
        if obj.get('client_reference_id')!=payment_id:raise PublicError('INVALID_INPUT')
        if obj.get('payment_status')=='paid':apply('checkout.session.completed',obj)
        elif obj.get('status')=='expired':
            with database.session() as db:
                lock_workspace(db,workspace_id);payment=db.get(Payment,payment_id)
                if payment.state in ('created','pending','unpaid'):payment.state='expired'
                db.commit()
    after=None;more=False;scanned=0
    for _ in range(max_pages):
        params={'customer':customer,'limit':100}
        if after:params['starting_after']=after
        result=gateway.request('GET','/v1/invoices',params)
        rows=result.get('data',[]);more=bool(result.get('has_more'))
        if more and not rows:raise PublicError('SERVICE_UNAVAILABLE')
        for obj in rows:
            scanned+=1
            if obj.get('status')=='paid':apply('invoice.paid',obj)
            else:
                if obj.get('customer')!=customer:raise PublicError('INVALID_INPUT')
                from modules.invoices.application.billing_views import sync_invoice
                with database.session() as db:
                    lock_workspace(db,workspace_id);sync_invoice(db,db.get(Workspace,workspace_id),obj);db.commit()
        if not more:break
        after=rows[-1]['id']
    with database.session() as db:
        audit(db,'system','billing.reconciled',workspace_id,workspace_id,reason=f'{count} effects; {scanned} invoices; has_more={more}')
        report=accounting_report(db,workspace_id);db.commit()
    return {'effects_applied':count,'invoices_scanned':scanned,'has_more':more,'local_accounting':report,
       'limitation':'Only recorded Checkout sessions and bounded invoice history. Missing local attempt links and refund/dispute adjustments require operator review.'}
