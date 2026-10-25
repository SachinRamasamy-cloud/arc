import hashlib,json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import httpx,pytest
from sqlalchemy import select,func
from arc.models import Workspace,Wallet,Payment,PlanPrice,Allowance,UsageEvent,CustomerRecord,StorageInterval,StorageStatement,FileObject,now
from arc.billing_views import plan_snapshot
from arc.payments import StripeGateway,handle_event
from arc.accounting import meter_storage,meter_storage_batch,month_bounds
from arc.reconciliation import accounting_report,reconcile_workspace
from arc.records import mutate,RecordBody
from arc.models import Project
from arc.errors import PublicError
from conftest import call
from test_v02_records import credential
from test_v02_checkout import live_owner


def test_configured_stripe_price_mismatch_blocks_checkout(owner,monkeypatch):
    base=live_owner(owner,monkeypatch);seen=[]
    def response(request):
        seen.append(request.url.path)
        return httpx.Response(200,json={'id':'price_pack','active':True,'currency':'usd','unit_amount':1})
    owner['app'].state.stripe=StripeGateway(owner['settings'],httpx.MockTransport(response))
    r=call(owner['client'],'post',base+'/checkout',json={'kind':'credits'},headers={'Idempotency-Key':'badprice'})
    assert r.status_code==503 and seen==['/v1/prices/price_pack']
    with owner['db'].session() as db:assert db.scalar(select(Wallet.balance_milli).where(Wallet.environment=='live'))==0


def test_known_expired_checkout_returns_recoverable_state(owner,monkeypatch):
    base=live_owner(owner,monkeypatch)
    with owner['db'].session() as db:
        db.add(Payment(workspace_id=owner['wid'],kind='credits',request_key=hashlib.sha256((owner['wid']+':old').encode()).hexdigest(),checkout_id='cs_expired',checkout_url='https://checkout.stripe.com/expired',checkout_expires_at=now()-10,currency='usd',amount_minor=1000,state='pending'));db.commit()
    r=call(owner['client'],'post',base+'/checkout',json={'kind':'credits'},headers={'Idempotency-Key':'old'})
    assert r.status_code==200 and r.json()['state']=='expired' and r.json()['url'] is None


def test_monthly_price_and_allowance_remain_pinned_after_new_offer(owner):
    s=owner['settings'];s.stripe_plan_price_id='price_original';s.stripe_secret_key='sk_test_fixture'
    with owner['db'].session() as db:
        plan_snapshot(db,s);w=db.get(Workspace,owner['wid']);w.stripe_customer='cus_snapshot';w.subscription_id='sub_snapshot';w.subscription_price='price_original';db.commit()
        s.stripe_plan_price_id='price_new';s.stripe_plan_minor=9900;s.stripe_plan_allowance_milli=990000
        start=now();end=now()+86400
        invoice={'id':'in_original','status':'paid','customer':'cus_snapshot','currency':'usd','amount_paid':2900,'billing_reason':'subscription_cycle','subscription':'sub_snapshot','lines':{'data':[{'price':{'id':'price_original'},'period':{'start':start,'end':end}}]}}
        handle_event(db,s,owner['app'].state.stripe,{'id':'evt_snapshot','type':'invoice.paid','livemode':False,'data':{'object':invoice}});db.commit()
        assert db.scalar(select(Allowance.balance_milli))==300000
    v=owner['client'].get(f"/api/console/v1/workspaces/{owner['wid']}/billing?environment=live").json()
    assert v['current_plan']['amount_minor']==2900 and v['prices']['subscription']['amount_minor']==9900


def test_existing_price_id_cannot_silently_change_its_allowance(owner):
    s=owner['settings'];s.stripe_plan_price_id='price_fixed'
    with owner['db'].session() as db:
        plan_snapshot(db,s);db.commit();s.stripe_plan_allowance_milli+=1
        with pytest.raises(PublicError):plan_snapshot(db,s)


def test_concurrent_record_writes_never_overspend(owner):
    s=owner['settings'];s.records_per_1000_milli=1000
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.environment=='test'));w.balance_milli=7;db.commit()
    def write(i):
        with owner['db'].session() as db:
            try:
                mutate(db,s,db.get(Project,owner['pid']),'test','parallel',str(i),RecordBody(data={'i':i}),'concurrent-'+str(i),'test');db.commit();return True
            except PublicError as e:assert e.code=='INSUFFICIENT_CREDITS';return False
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(write,range(25)))
    assert sum(results)==7
    with owner['db'].session() as db:
        assert db.scalar(select(Wallet.balance_milli).where(Wallet.environment=='test'))==0
        assert db.scalar(select(func.count(CustomerRecord.id)))==7
        assert db.scalar(select(func.sum(UsageEvent.gross_milli)))==7


def test_free_delete_works_without_remaining_credit(owner):
    h=credential(owner);h['Idempotency-Key']='create';c=owner['client']
    assert c.put('/v1/data/test/a',json={'data':{'x':1}},headers=h).status_code==200
    with owner['db'].session() as db:db.scalar(select(Wallet).where(Wallet.environment=='test')).balance_milli=0;db.commit()
    h['Idempotency-Key']='delete'
    assert c.delete('/v1/data/test/a?expected_version=1',headers=h).status_code==200
    with owner['db'].session() as db:assert db.scalar(select(func.count(UsageEvent.id)))==1


def test_storage_stops_at_expiry_even_when_cleanup_delayed(owner):
    start,end=month_bounds('2026-04')
    with owner['db'].session() as db:
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='large',content_type='text/plain',expected_size=1_000_000_000,size=1_000_000_000,object_key='expiry',state='ready',expires_at=start+86400)
        db.add(f);db.flush();db.add(StorageInterval(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',file_id=f.id,size_bytes=f.size,opened_at=start));db.commit()
        stmt=meter_storage(db,owner['settings'],owner['wid'],'test','2026-04',end);db.commit()
        assert stmt.byte_seconds==1_000_000_000*86400 and stmt.settled_milli==34


def test_storage_sweeper_recovers_old_arrears_and_is_throttled(owner,monkeypatch):
    start,end=month_bounds('2026-04');may_start,may_end=month_bounds('2026-05');fixed=may_start+86400
    monkeypatch.setattr('arc.accounting.now',lambda:fixed)
    with owner['db'].session() as db:
        wallet=db.scalar(select(Wallet).where(Wallet.environment=='test'));wallet.balance_milli=0
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='old',content_type='text/plain',expected_size=1000,size=1000,object_key='sweep',state='ready',expires_at=end)
        db.add(f);db.flush();db.add(StorageInterval(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',file_id=f.id,size_bytes=f.size,opened_at=start));db.commit()
        assert meter_storage(db,owner['settings'],owner['wid'],'test','2026-04').state=='payment_required'
        meter_storage(db,owner['settings'],owner['wid'],'test','2026-05',may_end);db.commit()
        wallet.balance_milli=100;db.commit()
    assert meter_storage_batch(owner['db'],owner['settings'])==1
    assert meter_storage_batch(owner['db'],owner['settings'])==0
    with owner['db'].session() as db:
        assert db.scalar(select(StorageStatement.state).where(StorageStatement.period_start==start))=='closed'
        assert db.scalar(select(func.count(UsageEvent.id)))==1


def test_accounting_diagnostic_detects_drift_without_rewriting(owner):
    with owner['db'].session() as db:
        assert accounting_report(db,owner['wid'])['balanced']
        wallet=db.scalar(select(Wallet).where(Wallet.environment=='test'));wallet.balance_milli+=1;db.commit()
        assert not accounting_report(db,owner['wid'])['balanced']
        assert wallet.balance_milli==100001


def test_stripe_recovery_reads_verified_state_once(owner):
    s=owner['settings'];s.stripe_secret_key='sk_test_fixture'
    with owner['db'].session() as db:
        db.get(Workspace,owner['wid']).stripe_customer='cus_recover'
        p=Payment(workspace_id=owner['wid'],kind='credits',checkout_id='cs_recover',state='pending',currency='usd',amount_minor=1000,credit_milli=100000);db.add(p);db.commit();pid=p.id
    def response(request):
        if request.url.path=='/v1/checkout/sessions/cs_recover':return httpx.Response(200,json={'id':'cs_recover','customer':'cus_recover','client_reference_id':pid,'payment_status':'paid','currency':'usd','amount_subtotal':1000,'metadata':{'workspace_id':owner['wid']},'livemode':False})
        assert request.url.path=='/v1/invoices' and request.url.params['customer']=='cus_recover'
        return httpx.Response(200,json={'data':[],'has_more':False})
    gateway=StripeGateway(s,httpx.MockTransport(response))
    first=reconcile_workspace(owner['db'],s,gateway,owner['wid']);second=reconcile_workspace(owner['db'],s,gateway,owner['wid'])
    assert first['effects_applied']==1 and second['effects_applied']==0 and first['local_accounting']['balanced']
    with owner['db'].session() as db:assert db.scalar(select(Wallet.balance_milli).where(Wallet.environment=='live'))==100000


def test_provider_reconciliation_rejects_foreign_customer(owner):
    s=owner['settings'];s.stripe_secret_key='sk_test_fixture'
    with owner['db'].session() as db:db.get(Workspace,owner['wid']).stripe_customer='cus_ours';db.commit()
    gateway=StripeGateway(s,httpx.MockTransport(lambda _:httpx.Response(200,json={'data':[{'id':'in_other','customer':'cus_other','status':'paid'}],'has_more':False})))
    with pytest.raises(PublicError):reconcile_workspace(owner['db'],s,gateway,owner['wid'])


def test_idempotency_receipt_quota_rolls_back_write_and_charge(owner):
    s=owner['settings'];s.receipt_quota_count=1;h=credential(owner);c=owner['client']
    h['Idempotency-Key']='first';assert c.put('/v1/data/bounded/a',json={'data':{'v':1}},headers=h).status_code==200
    h['Idempotency-Key']='second';assert c.put('/v1/data/bounded/b',json={'data':{'v':2}},headers=h).status_code==422
    with owner['db'].session() as db:
        assert db.scalar(select(func.count(CustomerRecord.id)))==1
        assert db.scalar(select(func.count(UsageEvent.id)))==1
        assert db.scalar(select(Wallet.balance_milli).where(Wallet.environment=='test'))==99999
    h['Idempotency-Key']='cleanup';assert c.delete('/v1/data/bounded/a?expected_version=1',headers=h).status_code==200


def test_scope_quota_queries_use_covering_indexes(owner):
    from sqlalchemy import text
    with owner['db'].engine.connect() as con:
        plan=con.execute(text("EXPLAIN QUERY PLAN SELECT count(id),sum(size_bytes) FROM customer_records WHERE workspace_id=:w AND environment='test'"),{'w':owner['wid']}).all()
        assert any('ix_records_workspace_quota' in str(row) for row in plan)
        plan=con.execute(text("EXPLAIN QUERY PLAN SELECT sum(gross_milli) FROM usage_events WHERE workspace_id=:w AND environment='test' AND occurred_at>=0"),{'w':owner['wid']}).all()
        assert any('ix_usage_workspace_period' in str(row) for row in plan)


def test_usage_price_version_cannot_change_in_place(owner):
    from arc.pricing import ensure_price
    with owner['db'].session() as db:
        ensure_price(db,owner['settings']);db.commit()
        owner['settings'].records_per_1000_milli+=1000
        with pytest.raises(PublicError):ensure_price(db,owner['settings'])
        db.rollback();owner['settings'].price_version='reviewed-new-version'
        assert ensure_price(db,owner['settings']).records_per_1000_milli==2000
        db.commit()
