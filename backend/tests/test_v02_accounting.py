import json
from datetime import datetime,timezone
from sqlalchemy import select,func,update
import pytest
from arc.accounting import month_bounds,bill_record_operation,meter_storage,usage_summary
from arc.models import (Workspace,Wallet,Allowance,Project,UsageEvent,StorageInterval,
                        StorageStatement,FileObject,Job,Ledger,Invoice,now)
from arc.services import admit,settle
from arc.schemas import Run
from arc.worker import process_one
from conftest import call

@pytest.mark.parametrize('month,days',[('2024-02',29),('2025-02',28),('2026-12',31),('2026-04',30)])
def test_calendar_periods(month,days):
    a,b=month_bounds(month);assert b-a==days*86400
    assert datetime.fromtimestamp(a,timezone.utc).strftime('%Y-%m')==month

@pytest.mark.parametrize('month',['today','2026-13','2026-1','1999-12','2026-01\n'])
def test_invalid_month(month):
    from arc.errors import PublicError
    with pytest.raises(PublicError):month_bounds(month)

def test_usage_event_settled_once_price_pinned(owner):
    s=owner['settings'];s.price_version='test-release';s.processing_base_milli=700;s.processing_kib_milli=200
    r=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/jobs",json={'data':[{'id':1}]},headers={'Idempotency-Key':'pin'})
    assert r.status_code==202,r.text
    jid=r.json()['job']['id'];s.processing_base_milli=2000
    assert process_one(owner['db'],s,owner['app'].state.store)
    with owner['db'].session() as db:
        j=db.get(Job,jid);assert j.charged_milli==900
        settle(db,s,j,j.charged_milli,True);db.commit()
        usage=db.scalar(select(UsageEvent));assert usage.gross_milli==usage.prepaid_milli==900 and usage.price_version=='test-release'
        assert db.scalar(select(func.count(UsageEvent.id)))==1

def test_reserve_across_multiple_allowances(owner):
    s=owner['settings'];s.live_enabled=True
    with owner['db'].session() as db:
        db.add_all([Allowance(id='one',workspace_id=owner['wid'],balance_milli=300,held_milli=0,expires_at=now()+900),Allowance(id='two',workspace_id=owner['wid'],balance_milli=500,held_milli=0,expires_at=now()+1800)])
        db.commit();j,_=admit(db,s,owner['app'].state.limiter,db.get(Project,owner['pid']),'live',Run(data=[]),'both',owner['user_id'])
        assert j.reserved_allowance_milli==600 and j.reserved_paid_milli==0
        settle(db,s,j,600,True);db.commit()
        assert db.get(Allowance,'one').balance_milli+db.get(Allowance,'two').balance_milli==200
        u=db.scalar(select(UsageEvent));assert u.gross_milli==600 and u.included_milli==600 and u.prepaid_milli==0

def test_per_thousand_rounding_is_cumulative(owner):
    owner['settings'].records_per_1000_milli=1501
    with owner['db'].session() as db:
        project=db.get(Project,owner['pid'])
        for i in range(50):bill_record_operation(db,owner['settings'],project,'test',f'op:{i}','read')
        # Duplicate operation reference does not add another charge or quantity.
        bill_record_operation(db,owner['settings'],project,'test','op:0','read');db.commit()
        assert db.scalar(select(func.sum(UsageEvent.gross_milli)))==(50*1501+999)//1000==76
        assert db.scalar(select(func.sum(UsageEvent.quantity)))==50

def test_month_filter_environment_and_full_aggregate(owner):
    start,end=month_bounds('2026-03')
    with owner['db'].session() as db:
        for i in range(130):db.add(UsageEvent(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',reference=f'x:{i}',service='records',operation='read',quantity=1,unit='request',price_version='test',gross_milli=2,included_milli=0,prepaid_milli=2,occurred_at=start+i))
        db.add_all([UsageEvent(workspace_id=owner['wid'],environment=env,reference=env,service='processing',operation='validate',unit='job',quantity=1,price_version='test',gross_milli=999,included_milli=0,prepaid_milli=999,occurred_at=t) for env,t in [('live',start),('test',end)]])
        db.add(Allowance(id='live-only',workspace_id=owner['wid'],balance_milli=1000,held_milli=0,expires_at=now()+1000));db.commit()
    base=f"/api/console/v1/workspaces/{owner['wid']}"
    r=owner['client'].get(base+'/billing?environment=test&month=2026-03');assert r.status_code==200,r.text
    d=r.json();assert d['usage']['gross_milli']==260 and d['usage']['events']==130
    assert d['included_available_milli']==0 and d['payments']==[] and d['invoices']==[]
    assert owner['client'].get(base+'/billing?environment=live&month=2026-03').json()['usage']['gross_milli']==999
    page=owner['client'].get(base+'/usage/events?environment=test&month=2026-03&limit=100').json()
    assert len(page['items'])==100 and page['next_cursor']
    second=owner['client'].get(base+'/usage/events',params={'month':'2026-03','cursor':page['next_cursor']}).json()
    assert len(second['items'])==30
    assert owner['client'].get(base+'/usage/events',params={'month':'2026-04','cursor':page['next_cursor']}).status_code==422

def test_storage_byte_time_idempotency_and_unfunded_state(owner):
    start,end=month_bounds('2026-04')
    with owner['db'].session() as db:
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='test.csv',content_type='text/csv',expected_size=1_000_000_000,size=1_000_000_000,object_key='test/object',state='ready',expires_at=end)
        db.add(f);db.flush()
        db.add(StorageInterval(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',file_id=f.id,size_bytes=f.size,opened_at=start,closed_at=start+15*86400));db.commit()
        a=meter_storage(db,owner['settings'],owner['wid'],'test','2026-04',end);db.commit()
        assert a.assessed_milli==a.settled_milli==500
        meter_storage(db,owner['settings'],owner['wid'],'test','2026-04',end);db.commit()
        assert db.scalar(select(func.sum(UsageEvent.prepaid_milli)))==500
        assert db.scalar(select(func.count(Ledger.id)).where(Ledger.kind=='usage'))==1
        with pytest.raises(Exception):meter_storage(db,owner['settings'],owner['wid'],'test','2027-01',start)

def test_storage_shortfall_does_not_make_wallet_negative(owner):
    start,end=month_bounds('2026-04')
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'));w.balance_milli=0
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='x',content_type='text/plain',expected_size=1000,size=1000,object_key='x/y',state='ready',expires_at=end)
        db.add(f);db.flush();db.add(StorageInterval(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',file_id=f.id,size_bytes=1000,opened_at=start));db.commit()
        st=meter_storage(db,owner['settings'],owner['wid'],'test','2026-04',end);db.commit()
        assert st.state=='payment_required' and st.settled_milli==0 and w.balance_milli==0
    r=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/files",json={'name':'x.json','size':2,'content_type':'application/json'})
    assert r.status_code==402

def test_unauthorized_billing_and_bad_environment(owner):
    from conftest import account
    stranger,_=account(owner,'stranger@example.com')
    assert stranger.get(f"/api/console/v1/workspaces/{owner['wid']}/billing").status_code==404
    assert owner['client'].get(f"/api/console/v1/workspaces/{owner['wid']}/billing?environment=other").status_code==422
