import hashlib,hmac,json,time,uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,update,func
from fastapi.testclient import TestClient
from conftest import call,account,PASSWORD
from arc.models import Wallet,Project,Job,User,LoginSession,Workspace,Notification,Mail,WebhookEndpoint,WebhookDelivery,FileObject,now
from arc.security import seal,unseal,totp_code,digest
from arc.deliveries import reminders,deliver_webhook,deliver_mail,cleanup_expired
from arc.worker import process_one
import httpx,pytest

def test_parallel_requests_cannot_overspend(owner):
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}"
    key=call(c,'post',base+'/keys',json={'label':'parallel test','scopes':['jobs:read','jobs:write']}).json()['secret']
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'));w.balance_milli=1000
        db.get(Project,owner['pid']).concurrency=10;db.commit()
    def attempt(i):
        with TestClient(owner['app'],raise_server_exceptions=False) as local:
            r=local.post('/v1/jobs',json={'operation':'validate','data':[{'id':i}]},headers={'Authorization':'Bearer '+key,'Idempotency-Key':'parallel-'+str(i)})
            return r.status_code,r.json()
    with ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(attempt,range(6)))
    accepted=[r for code,r in results if code==202]
    assert len(accepted)==1,results
    assert all(code in (202,402) for code,_ in results),results
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'))
        assert 0<=w.held_milli<=w.balance_milli==1000

def test_nonfinite_input_is_rejected(owner):
    key=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'numeric','scopes':['jobs:write']}).json()['secret']
    r=owner['client'].post('/v1/jobs',content=b'{"operation":"validate","data":[{"x":NaN}]}',headers={'Authorization':'Bearer '+key,'Idempotency-Key':'nan','Content-Type':'application/json'})
    assert r.status_code==422 and r.json()['code']=='INVALID_INPUT'

def test_public_schema_excludes_admin_and_credentials(owner):
    paths=owner['client'].get('/v1/openapi.json').json()['paths']
    assert '/v1/jobs' in paths and all(p.startswith('/v1/') for p in paths)
    assert 'operator' not in json.dumps(paths) and '/api/console' not in json.dumps(paths)

def test_operator_session_is_separate_and_requires_mfa(owner):
    assert owner['client'].get('/api/operator/v1/customers').status_code==401
    secret='JBSWY3DPEHPK3PXP';staff,uid=account(owner,'staff@example.com',staff=True,totp=seal(secret,owner['settings'],'totp'))
    r=call(staff,'post','/api/operator/v1/auth/login',json={'email':'staff@example.com','password':PASSWORD,'code':totp_code(secret,int(time.time()))})
    assert r.status_code==200,r.text
    assert staff.get('/api/operator/v1/customers').status_code==200
    assert staff.get('/api/console/v1/workspaces').status_code==401
    assert call(owner['client'],'post','/api/operator/v1/auth/signup',json={}).status_code==404

def test_staff_status_change_requires_reason(owner):
    secret='JBSWY3DPEHPK3PXP';staff,uid=account(owner,'staff2@example.com',staff=True,totp=seal(secret,owner['settings'],'totp'))
    call(staff,'post','/api/operator/v1/auth/login',json={'email':'staff2@example.com','password':PASSWORD,'code':totp_code(secret,int(time.time()))})
    r=call(staff,'patch',f"/api/operator/v1/customers/{owner['wid']}",json={'status':'suspended','reason':'x'});assert r.status_code==422
    r=call(staff,'patch',f"/api/operator/v1/customers/{owner['wid']}",json={'status':'suspended','reason':'Confirmed policy violation review'});assert r.status_code==200
    r=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'denied','scopes':['jobs:write']});assert r.status_code==403
    assert owner['client'].get(f"/api/console/v1/workspaces/{owner['wid']}/billing").status_code==200

def test_mfa_setup_confirm_and_recovery_one_use(owner):
    c=owner['client'];setup=call(c,'post','/api/console/v1/auth/mfa/setup').json();code=totp_code(setup['secret'],int(time.time()))
    confirm=call(c,'post','/api/console/v1/auth/mfa/confirm',json={'code':code});assert confirm.status_code==200,confirm.text
    recovery=confirm.json()['recovery_codes'][0];call(c,'post','/api/console/v1/auth/logout')
    r=call(c,'post','/api/console/v1/auth/login',json={'email':'owner@example.com','password':PASSWORD,'code':recovery});assert r.status_code==200
    call(c,'post','/api/console/v1/auth/logout')
    r=call(c,'post','/api/console/v1/auth/login',json={'email':'owner@example.com','password':PASSWORD,'code':recovery});assert r.status_code==401

def test_renewal_notifications_are_deduplicated(owner):
    with owner['db'].session() as db:
        w=db.get(Workspace,owner['wid']);w.subscription_id='sub_reminder';w.subscription_status='active';w.period_end=now()+6*86400+100;db.commit()
    reminders(owner['db'],owner['settings']);reminders(owner['db'],owner['settings'])
    with owner['db'].session() as db:
        assert db.scalar(select(func.count(Notification.id)).where(Notification.workspace_id==owner['wid'],Notification.category=='billing'))==1

def test_webhook_delivery_revalidates_and_signs(owner,monkeypatch):
    from urllib.parse import urlsplit
    from arc.security import webhook_signature
    monkeypatch.setattr('arc.deliveries.validate_webhook_url',lambda *_:(urlsplit('https://hooks.example.com/callback'),['93.184.216.34']))
    secret='whsec_internal_fixture'
    with owner['db'].session() as db:
        endpoint=WebhookEndpoint(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',url='https://hooks.example.com/callback',encrypted_secret=seal(secret,owner['settings'],'webhook'))
        db.add(endpoint);db.flush();delivery=WebhookDelivery(workspace_id=owner['wid'],endpoint_id=endpoint.id,event_id='evt_fixture',payload={'id':'evt_fixture','type':'job.succeeded'})
        db.add(delivery);db.commit();did=delivery.id
    def callback(request):
        assert request.headers['Host']=='hooks.example.com' and request.url.host=='93.184.216.34'
        sig=request.headers['Arc-Signature'];parts=dict(x.split('=',1) for x in sig.split(','));assert sig==webhook_signature(secret,request.content,int(parts['t']))
        return httpx.Response(204)
    assert deliver_webhook(owner['db'],owner['settings'],httpx.MockTransport(callback))
    with owner['db'].session() as db:assert db.get(WebhookDelivery,did).state=='delivered'

def test_expired_public_download_denied(owner):
    key=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'files','scopes':['files:read']}).json()['secret']
    with owner['db'].session() as db:
        f=FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='old.json',content_type='application/json',expected_size=2,size=2,object_key='old/file',state='ready',expires_at=now()-1)
        db.add(f);db.commit();fid=f.id
    assert owner['client'].get('/v1/files/'+fid+'/download',headers={'Authorization':'Bearer '+key}).status_code==404

def test_retention_erases_failed_job_inputs_and_honors_project(owner):
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}"
    job=call(c,'post',base+'/jobs',json={'operation':'validate','data':[{'private':'input'}],'required_fields':['missing']},headers={'Idempotency-Key':'retention'}).json()['job']
    assert process_one(owner['db'],owner['settings'],owner['app'].state.store)
    with owner['db'].session() as db:
        row=db.get(Job,job['id']);assert row.state=='failed';row.completed_at=now()-7200
        db.get(Project,owner['pid']).retention_hours=1;db.commit()
    cleanup_expired(owner['db'],owner['settings'],owner['app'].state.store)
    with owner['db'].session() as db:
        row=db.get(Job,job['id']);assert row.input_data=={} and row.result is None and row.state=='failed'
