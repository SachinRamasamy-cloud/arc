import time
from sqlalchemy import select,func
import httpx
from arc.models import Workspace,Payment,Invoice,Allowance,now
from arc.payments import StripeGateway,handle_event
from arc.deliveries import reminders
from arc.models import Notification
from conftest import call


def live_owner(owner,monkeypatch):
    # This unit fixture bypasses only MFA; production routes keep require_live.
    monkeypatch.setattr('modules.payments.interfaces.customer_router.require_live',lambda *_:None)
    s=owner['settings'];s.live_enabled=True;s.stripe_secret_key='sk_test_fixture';s.stripe_plan_price_id='price_plan';s.stripe_credit_price_id='price_pack'
    with owner['db'].session() as db:
        db.get(Workspace,owner['wid']).stripe_customer='cus_billing';db.commit()
    return f"/api/console/v1/workspaces/{owner['wid']}/billing"


def test_checkout_retries_reuse_durable_attempt(owner,monkeypatch):
    base=live_owner(owner,monkeypatch);seen=[]
    def respond(request):
        if request.url.path=='/v1/prices/price_pack':return httpx.Response(200,json={'id':'price_pack','active':True,'currency':'usd','unit_amount':owner['settings'].stripe_credit_pack_minor})
        assert request.url.path=='/v1/checkout/sessions';seen.append(request.headers['Idempotency-Key'])
        if len(seen)==1:raise httpx.ConnectError('test timeout',request=request)
        return httpx.Response(200,json={'id':'cs_retry','url':'https://checkout.stripe.com/session','expires_at':now()+1800})
    owner['app'].state.stripe=StripeGateway(owner['settings'],httpx.MockTransport(respond))
    kwargs={'json':{'kind':'credits'},'headers':{'Idempotency-Key':'stable-attempt'}}
    assert call(owner['client'],'post',base+'/checkout',**kwargs).status_code==503
    ok=call(owner['client'],'post',base+'/checkout',**kwargs);assert ok.status_code==200,ok.text
    again=call(owner['client'],'post',base+'/checkout',**kwargs);assert again.json()['payment_id']==ok.json()['payment_id']
    assert len(seen)==2 and seen[0]==seen[1]
    with owner['db'].session() as db:assert db.scalar(select(func.count(Payment.id)))==1
    assert call(owner['client'],'post',base+'/checkout',json={'kind':'subscription'},headers={'Idempotency-Key':'stable-attempt'}).status_code==409


def test_parallel_subscription_attempts_block_duplicate_pending(owner,monkeypatch):
    base=live_owner(owner,monkeypatch)
    def respond(request):
        if request.url.path=='/v1/prices/price_plan':return httpx.Response(200,json={'id':'price_plan','active':True,'currency':'usd','unit_amount':owner['settings'].stripe_plan_minor,'recurring':{'interval':'month','interval_count':1}})
        return httpx.Response(200,json={'id':'cs_plan','url':'https://checkout.stripe.com/plan'})
    owner['app'].state.stripe=StripeGateway(owner['settings'],httpx.MockTransport(respond))
    assert call(owner['client'],'post',base+'/checkout',json={'kind':'subscription'},headers={'Idempotency-Key':'first'}).status_code==200
    assert call(owner['client'],'post',base+'/checkout',json={'kind':'subscription'},headers={'Idempotency-Key':'second'}).status_code==409


def test_invoice_mirror_and_paid_state_do_not_regress(owner,monkeypatch):
    base=live_owner(owner,monkeypatch);start=now()-100;end=now()+86400
    invoice={'id':'in_cycle','customer':'cus_billing','status':'paid','currency':'usd','amount_due':2900,'amount_paid':2900,
        'billing_reason':'subscription_cycle','parent':{'subscription_details':{'subscription':'sub_current'}},'period_start':start,'period_end':end,
        'hosted_invoice_url':'https://invoice.stripe.com/i/test','invoice_pdf':'https://evil.example/private',
        'lines':{'data':[{'pricing':{'price_details':{'price':'price_plan'}},'period':{'start':start,'end':end}}]}}
    with owner['db'].session() as db:
        for eventid in ('evt_paid_one','evt_paid_duplicate'):
            handle_event(db,owner['settings'],owner['app'].state.stripe,{'id':eventid,'type':'invoice.paid','livemode':False,'data':{'object':invoice}});db.commit()
        failed={**invoice,'status':'open','amount_paid':0}
        handle_event(db,owner['settings'],owner['app'].state.stripe,{'id':'evt_old_fail','type':'invoice.payment_failed','livemode':False,'data':{'object':failed}});db.commit()
        assert db.get(Invoice,'in_cycle').status=='paid'
        assert db.scalar(select(func.count(Allowance.id)))==1
    data=owner['client'].get(base+'?environment=live').json()
    assert data['invoices'][0]['amount_paid_minor']==2900
    assert data['invoices'][0]['pdf_url'] is None and data['subscription']['period_start']==start
    assert data['prices']['subscription']['interval']=='month'


def test_no_renewal_alert_when_canceling(owner):
    with owner['db'].session() as db:
        w=db.get(Workspace,owner['wid']);w.subscription_status='active';w.subscription_id='sub_cancel';w.period_end=now()+86400-50;w.cancel_at_period_end=True;db.commit()
    reminders(owner['db'],owner['settings'])
    with owner['db'].session() as db:assert db.scalar(select(func.count(Notification.id)))==0
