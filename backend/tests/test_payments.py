import json,time,hashlib,hmac,uuid
import httpx,pytest
from sqlalchemy import select,func,update
from arc.models import Payment,Workspace,Wallet,Ledger,StripeEvent,Allowance,Job,now
from arc.payments import verify_event,handle_event,StripeGateway
from arc.services import admit,settle
from arc.schemas import Run
from arc.errors import PublicError
from conftest import call

def payment_fixture(owner):
    owner['settings'].stripe_secret_key='sk_test_fixture';owner['settings'].stripe_webhook_secret='whsec_fixture'
    with owner['db'].session() as db:
        p=Payment(workspace_id=owner['wid'],kind='credits',currency='usd',amount_minor=1000,credit_milli=100000,checkout_id='cs_test_fixture')
        db.add(p);db.commit();pid=p.id
    return {'id':'evt_checkout','type':'checkout.session.completed','livemode':False,'data':{'object':{'id':'cs_test_fixture','client_reference_id':pid,'payment_status':'paid','amount_subtotal':1000,'currency':'usd','customer':'cus_fixture','payment_intent':'pi_fixture','metadata':{'workspace_id':owner['wid']}}}}

def apply(owner,event):
    with owner['db'].session() as db:
        result=handle_event(db,owner['settings'],owner['app'].state.stripe,event);db.commit();return result

def live_wallet(owner):
    with owner['db'].session() as db:
        from types import SimpleNamespace
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='live'))
        return SimpleNamespace(balance_milli=w.balance_milli,frozen=w.frozen)

def test_signature_exact_raw_bytes_and_timestamp():
    raw=b'{ "id": "evt_real", "data": {} }';stamp=int(time.time());secret='test-signing-secret'
    signature=hmac.new(secret.encode(),str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    header=f't={stamp},v1=invalid,v1={signature}'
    assert verify_event(raw,header,secret)['id']=='evt_real'
    with pytest.raises(PublicError):verify_event(json.dumps(json.loads(raw)).encode(),header,secret)
    with pytest.raises(PublicError):verify_event(raw,header,secret,clock=stamp+301)

@pytest.mark.parametrize('mutation',[lambda e:e['data']['object'].update(amount_subtotal=1),lambda e:e['data']['object'].update(currency='eur'),lambda e:e['data']['object'].update(client_reference_id='other'),lambda e:e['data']['object']['metadata'].update(workspace_id='other'),lambda e:e.update(livemode=True)])
def test_invalid_payment_never_grants(owner,mutation):
    e=payment_fixture(owner);mutation(e)
    with pytest.raises(PublicError):apply(owner,e)
    assert live_wallet(owner).balance_milli==0

def test_duplicate_checkout_events_one_effect(owner):
    event=payment_fixture(owner);assert apply(owner,event);assert not apply(owner,event)
    event['id']='evt_also_checkout';assert apply(owner,event)
    assert live_wallet(owner).balance_milli==100000
    with owner['db'].session() as db:assert db.scalar(select(func.count(Ledger.id)).where(Ledger.reference=='stripe:cs_test_fixture'))==1

def test_pending_payment_does_not_grant(owner):
    e=payment_fixture(owner);e['data']['object']['payment_status']='unpaid';apply(owner,e)
    assert live_wallet(owner).balance_milli==0
    e['id']='evt_payment_now_paid';e['type']='checkout.session.async_payment_succeeded';e['data']['object']['payment_status']='paid';apply(owner,e)
    assert live_wallet(owner).balance_milli==100000

def test_refund_freezes_without_rewriting_ledger(owner):
    e=payment_fixture(owner);apply(owner,e)
    adjustment={'id':'evt_refund','type':'charge.refunded','livemode':False,'data':{'object':{'payment_intent':'pi_fixture'}}};apply(owner,adjustment)
    assert live_wallet(owner).frozen and live_wallet(owner).balance_milli==100000

def test_subscription_fetches_current_state(owner):
    e=payment_fixture(owner);apply(owner,e)
    def response(request):
        assert str(request.url).endswith('/v1/subscriptions/sub_current')
        return httpx.Response(200,json={'id':'sub_current','customer':'cus_fixture','status':'active','items':{'data':[{'current_period_end':now()+86400}]}})
    gateway=StripeGateway(owner['settings'],httpx.MockTransport(response))
    with owner['db'].session() as db:
        handle_event(db,owner['settings'],gateway,{'id':'evt_old_update','type':'customer.subscription.updated','livemode':False,'data':{'object':{'id':'sub_current','customer':'cus_fixture','status':'past_due'}}});db.commit()
        assert db.get(Workspace,owner['wid']).subscription_status=='active'

def test_allowance_is_not_double_billed(owner):
    owner['settings'].live_enabled=True
    from arc.models import Project
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='live'));w.balance_milli=10000
        db.add(Allowance(id='in_included',workspace_id=owner['wid'],balance_milli=1000,held_milli=0,expires_at=now()+86400));db.commit()
        job,_=admit(db,owner['settings'],owner['app'].state.limiter,db.get(Project,owner['pid']),'live',Run(data=[{'id':1}]),'included',owner['user_id'])
        assert job.reserved_allowance_milli>0 and job.reserved_paid_milli==0
        settle(db,owner['settings'],job,job.reserved_milli,True);settle(db,owner['settings'],job,job.reserved_milli,True);db.commit()
        assert db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='live')).balance_milli==10000
        assert db.get(Allowance,'in_included').balance_milli==1000-job.reserved_milli

def test_checkout_uses_server_price_not_browser_value(owner):
    owner['settings'].stripe_secret_key='sk_test_fixture';owner['settings'].stripe_credit_price_id='price_fixed'
    def responder(request):
        from urllib.parse import parse_qs
        body=parse_qs(request.content.decode());assert body['line_items[0][price]']==['price_fixed'];assert body['customer_creation']==['always'];assert 'Authorization' in request.headers;assert 'Idempotency-Key' in request.headers
        return httpx.Response(200,json={'id':'cs_test_new','url':'https://checkout.stripe.com/test'})
    gateway=StripeGateway(owner['settings'],httpx.MockTransport(responder))
    with owner['db'].session() as db:
        p=Payment(id='payment_fixture',workspace_id=owner['wid'],kind='credits',currency='usd',amount_minor=1000,credit_milli=100000)
        assert gateway.checkout(db.get(Workspace,owner['wid']),p)['id']=='cs_test_new'

def test_public_stripe_webhook_verified_before_credit(owner):
    event=payment_fixture(owner);raw=json.dumps(event,separators=(',',':')).encode();stamp=int(time.time());signature=hmac.new(b'whsec_fixture',str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    assert owner['client'].post('/api/payments/stripe/webhook',content=raw,headers={'Stripe-Signature':'wrong'}).status_code==422
    assert live_wallet(owner).balance_milli==0
    response=owner['client'].post('/api/payments/stripe/webhook',content=raw,headers={'Stripe-Signature':f't={stamp},v1={signature}'})
    assert response.status_code==200,response.text
    assert live_wallet(owner).balance_milli==100000

def test_allowance_period_deduplicates_and_ignores_proration(owner):
    e=payment_fixture(owner);apply(owner,e);owner['settings'].stripe_plan_price_id='price_plan'
    period=now()+86400
    def invoice(i,reason='subscription_cycle',proration=False):
        return {'id':'evt_'+i,'type':'invoice.paid','livemode':False,'data':{'object':{'id':i,'customer':'cus_fixture','status':'paid','billing_reason':reason,'subscription':'sub_plan','lines':{'data':[{'price':{'id':'price_plan'},'period':{'end':period},'proration':proration}]}}}}
    apply(owner,invoice('in_proration','subscription_update',True))
    with owner['db'].session() as db:assert db.scalar(select(func.count(Allowance.id)))==0
    apply(owner,invoice('in_one'));apply(owner,invoice('in_duplicate_period'))
    with owner['db'].session() as db:
        assert db.scalar(select(func.count(Allowance.id)))==1
        assert db.scalar(select(Allowance)).balance_milli==owner['settings'].stripe_plan_allowance_milli

def test_customer_mapping_is_committed_before_checkout(owner):
    owner['settings'].stripe_secret_key='sk_test_fixture'
    requests=[]
    def response(request):
        requests.append(request);assert request.url.path=='/v1/customers'
        assert request.headers['Idempotency-Key']=='customer:'+owner['wid']
        return httpx.Response(200,json={'id':'cus_precreated'})
    gateway=StripeGateway(owner['settings'],httpx.MockTransport(response))
    with owner['db'].session() as db:
        workspace=db.get(Workspace,owner['wid']);gateway.ensure_customer(db,workspace);gateway.ensure_customer(db,workspace)
    assert len(requests)==1
    with owner['db'].session() as db:assert db.get(Workspace,owner['wid']).stripe_customer=='cus_precreated'
