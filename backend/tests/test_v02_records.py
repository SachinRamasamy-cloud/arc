import json
from sqlalchemy import select,func
from arc.models import CustomerRecord,MutationReceipt,UsageEvent,Wallet
from conftest import call,account


def credential(owner,scopes=None):
    r=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'Data client','scopes':scopes or ['data:read','data:write']})
    assert r.status_code==201,r.text
    return {'Authorization':'Bearer '+r.json()['secret']}


def test_record_crud_encrypted_optimistic_and_idempotent(owner):
    c=owner['client'];h=credential(owner);h['Idempotency-Key']='create-one'
    body={'data':{'name':'Ada','secret':'private_customer_content'},'expected_version':0}
    a=c.put('/v1/data/contacts/ada',json=body,headers=h);assert a.status_code==200,a.text
    again=c.put('/v1/data/contacts/ada',json=body,headers=h);assert again.json()['applied'] is False
    with owner['db'].session() as db:
        row=db.scalar(select(CustomerRecord));receipt=db.scalar(select(MutationReceipt))
        assert 'private_customer_content' not in row.encrypted_data and 'private_customer_content' not in receipt.response_encrypted
        assert db.scalar(select(func.count(UsageEvent.id)))==1
    assert c.put('/v1/data/contacts/ada',json={'data':{'name':'wrong'}},headers=h).status_code==409
    h['Idempotency-Key']='stale';assert c.put('/v1/data/contacts/ada',json=body,headers=h).status_code==409
    h['Idempotency-Key']='update';r=c.put('/v1/data/contacts/ada',json={'data':{'name':'Ada 2'},'expected_version':1},headers=h)
    assert r.status_code==200 and r.json()['record']['version']==2
    assert c.get('/v1/data/contacts/ada',headers=h).json()['record']['data']=={'name':'Ada 2'}
    h['Idempotency-Key']='delete';r=c.delete('/v1/data/contacts/ada?expected_version=2',headers=h)
    assert r.status_code==200 and r.json()['record']['deleted']
    assert c.delete('/v1/data/contacts/ada?expected_version=2',headers=h).json()['applied'] is False
    assert c.get('/v1/data/contacts/ada',headers=h).status_code==404


def test_scope_and_project_isolation(owner):
    c=owner['client'];h=credential(owner);h['Idempotency-Key']='mine'
    assert c.put('/v1/data/profiles/user',json={'data':{'name':'private'}},headers=h).status_code==200
    readonly=credential(owner,['data:read']);readonly['Idempotency-Key']='nope'
    assert c.put('/v1/data/profiles/new',json={'data':{}},headers=readonly).status_code==403
    other=call(c,'post',f"/api/console/v1/workspaces/{owner['wid']}/projects",json={'name':'Different app'}).json()['id']
    key=call(c,'post',f'/api/console/v1/projects/{other}/keys',json={'label':'Other key','scopes':['data:read']}).json()['secret']
    assert c.get('/v1/data/profiles/user',headers={'Authorization':'Bearer '+key}).status_code==404
    assert c.get('/v1/data/profiles/user').status_code==401


def test_pagination_scope_and_quota(owner):
    c=owner['client'];h=credential(owner)
    for key in ('a','b','c'):
        h['Idempotency-Key']=key
        assert c.put('/v1/data/items/'+key,json={'data':{'value':key}},headers=h).status_code==200
    first=c.get('/v1/data/items?limit=2',headers=h).json();assert [r['key'] for r in first['items']]==['a','b']
    nxt=c.get('/v1/data/items',params={'limit':2,'cursor':first['next_cursor']},headers=h).json()
    assert [r['key'] for r in nxt['items']]==['c'] and nxt['next_cursor'] is None
    assert c.get('/v1/data/other',params={'cursor':first['next_cursor']},headers=h).status_code==422
    owner['settings'].records_quota_count=3;h['Idempotency-Key']='over'
    assert c.put('/v1/data/items/d',json={'data':{}},headers=h).status_code==422
    with owner['db'].session() as db:assert db.scalar(select(func.count(CustomerRecord.id)))==3


def test_invalid_payload_and_unfunded_write_are_atomic(owner):
    c=owner['client'];h=credential(owner);h['Idempotency-Key']='bad'
    assert c.put('/v1/data/BAD/key',json={'data':{}},headers=h).status_code==422
    assert c.put('/v1/data/good/key',content=b'{"data":{"v":NaN}}',headers={**h,'Content-Type':'application/json'}).status_code==422
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'));w.balance_milli=0;db.commit()
    assert c.put('/v1/data/good/key',json={'data':{}},headers=h).status_code==402
    with owner['db'].session() as db:
        assert db.scalar(select(func.count(CustomerRecord.id)))==0
        assert db.scalar(select(func.count(UsageEvent.id)))==0


def test_console_reads_data_without_api_meter(owner):
    c=owner['client'];h=credential(owner);h['Idempotency-Key']='inspect'
    c.put('/v1/data/demo/row',json={'data':{'value':1}},headers=h)
    base=f"/api/console/v1/projects/{owner['pid']}/data"
    assert c.get(base).json()['collections'][0]['records']==1
    assert c.get(base+'/demo').json()['items'][0]['data']=={'value':1}
    with owner['db'].session() as db:assert db.scalar(select(func.count(UsageEvent.id)))==1
