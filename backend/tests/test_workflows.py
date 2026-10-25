import json,uuid,hashlib
from urllib.parse import urlsplit
from sqlalchemy import select,update,func
from conftest import call,account
from arc.models import Job,Wallet,Project,Allowance,Ledger,FileObject,RunEvent,now
from arc.worker import process_one,claim,event,recover_expired
from arc.services import validate_graph,settle
from arc.errors import PublicError
import pytest

def submit(o,body=None,key=None):
    return call(o['client'],'post',f"/api/console/v1/projects/{o['pid']}/jobs",json=body or {'operation':'normalize','data':[{'name':' Ada '}],'max_credits_milli':10000},headers={'Idempotency-Key':key or str(uuid.uuid4())})
def finish(o):
    return process_one(o['db'],o['settings'],o['app'].state.store)
def read_job(o,jid):
    return o['client'].get(f"/api/console/v1/projects/{o['pid']}/jobs/{jid}")
def graph():
    return {'nodes':[{'id':'input','data':{'kind':'input','format':'json'}},{'id':'clean','data':{'kind':'normalize','config':{'lowercase':['email']}}},{'id':'output','data':{'kind':'output'}}], 'edges':[{'source':'input','target':'clean'},{'source':'clean','target':'output'}]}

def test_real_job_reserved_then_settled(owner):
    response=submit(owner);assert response.status_code==202,response.text
    job=response.json()['job'];reserved=job['reserved_milli'];assert reserved>0
    with owner['db'].session() as db:
        wallet=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'))
        assert wallet.balance_milli==100000 and wallet.held_milli==reserved
    assert finish(owner)
    result=read_job(owner,job['id']).json()['job']
    assert result['state']=='succeeded' and result['result']['output']==[{'name':'Ada'}]
    assert result['charged_milli']==reserved and result['billing_state']=='settled'
    with owner['db'].session() as db:
        wallet=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'))
        assert wallet.balance_milli==100000-reserved and wallet.held_milli==0
        assert db.scalar(select(func.count(Ledger.id)).where(Ledger.reference=='settle:'+job['id']))==1

def test_submission_idempotency_and_fingerprint(owner):
    a=submit(owner,key='repeat');b=submit(owner,key='repeat')
    assert a.json()['job']['id']==b.json()['job']['id'] and b.json()['created'] is False
    c=submit(owner,{'operation':'validate','data':[{'other':1}]},'repeat');assert c.status_code==409

def test_invalid_native_input_releases_credits(owner):
    a=submit(owner,{'operation':'validate','data':[{'name':'Ada'}],'required_fields':['missing']});assert a.status_code==202
    assert finish(owner);result=read_job(owner,a.json()['job']['id']).json()['job']
    assert result['state']=='failed' and result['billing_state']=='released' and result['charged_milli']==0
    with owner['db'].session() as db:
        w=db.scalar(select(Wallet).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'));assert (w.balance_milli,w.held_milli)==(100000,0)

def test_cancel_queued_releases_once(owner):
    job=submit(owner).json()['job'];url=f"/api/console/v1/projects/{owner['pid']}/jobs/{job['id']}/cancel"
    assert call(owner['client'],'post',url).status_code==200
    assert call(owner['client'],'post',url).status_code==409
    assert not finish(owner)
    with owner['db'].session() as db: assert db.scalar(select(func.count(Ledger.id)).where(Ledger.reference=='settle:'+job['id']))==1

def test_budget_and_balance_rejections_leave_no_job(owner):
    assert submit(owner,{'operation':'validate','data':[],'max_credits_milli':0}).json()['code']=='BUDGET_EXCEEDED'
    with owner['db'].session() as db: db.execute(update(Wallet).where(Wallet.workspace_id==owner['wid']).values(balance_milli=0));db.commit()
    r=submit(owner);assert r.json()['code']=='INSUFFICIENT_CREDITS'
    with owner['db'].session() as db: assert db.scalar(select(func.count(Job.id)))==0

def test_concurrent_capacity_is_enforced(owner):
    with owner['db'].session() as db: db.get(Project,owner['pid']).concurrency=1;db.commit()
    assert submit(owner).status_code==202
    assert submit(owner).json()['code']=='CAPACITY_REACHED'

def test_sse_replays_real_history_and_stops(owner):
    job=submit(owner).json()['job'];finish(owner)
    events=read_job(owner,job['id']).json()['events'];cursor=events[0]['id']
    r=owner['client'].get(f"/api/console/v1/projects/{owner['pid']}/jobs/{job['id']}/events",headers={'Last-Event-ID':str(cursor)})
    assert r.status_code==200 and 'event: job.succeeded' in r.text and 'event: stream.complete' in r.text
    assert f'id: {cursor}\n' not in r.text

def test_sse_rejects_foreign_cursor(owner):
    a=submit(owner).json()['job'];finish(owner);b=submit(owner).json()['job'];finish(owner)
    cursor=read_job(owner,a['id']).json()['events'][0]['id']
    r=owner['client'].get(f"/api/console/v1/projects/{owner['pid']}/jobs/{b['id']}/events",headers={'Last-Event-ID':str(cursor)})
    assert r.status_code==409

def test_file_upload_verify_process_download(owner):
    raw=b'name,email\nAda,ada@example.test\n'
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}/files"
    created=call(c,'post',base,json={'name':'sample.csv','size':len(raw),'content_type':'text/csv'}).json()
    url=urlsplit(created['upload_url']);r=c.put(url.path+'?'+url.query,content=raw,headers=created['headers']);assert r.status_code==204,r.text
    fid=created['file']['id'];verified=call(c,'post',base+'/'+fid+'/complete');assert verified.status_code==200,verified.text
    assert verified.json()['digest']==hashlib.sha256(raw).hexdigest()
    # A still-valid upload URL cannot replace the canonical verified input.
    replaced=c.put(url.path+'?'+url.query,content=b'X'*len(raw),headers=created['headers']);assert replaced.status_code==409
    job=submit(owner,{'operation':'csv_to_json','file_id':fid}).json()['job'];finish(owner)
    assert read_job(owner,job['id']).json()['job']['result']['output']==[{'name':'Ada','email':'ada@example.test'}]
    dl=urlsplit(c.get(base+'/'+fid+'/download').json()['url']);assert c.get(dl.path+'?'+dl.query).content==raw
    assert call(c,'delete',base+'/'+fid).status_code==200
    assert c.get(dl.path+'?'+dl.query).status_code==404

def test_file_completion_rejects_size_mismatch(owner):
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}/files"
    r=call(c,'post',base,json={'name':'a.json','size':10,'content_type':'application/json'}).json();url=urlsplit(r['upload_url']);c.put(url.path+'?'+url.query,content=b'[]',headers=r['headers'])
    assert call(c,'post',base+'/'+r['file']['id']+'/complete').status_code==422

def test_cross_tenant_project_job_and_files(owner):
    other,_=account(owner,'other@example.com');job=submit(owner).json()['job']
    for suffix in ['keys','files','jobs','limits','workflows']:
        assert other.get(f"/api/console/v1/projects/{owner['pid']}/{suffix}").status_code in (403,404)
    assert other.get(f"/api/console/v1/projects/{owner['pid']}/jobs/{job['id']}").status_code in (403,404)
    assert other.get(f"/api/console/v1/projects/{owner['pid']}/jobs/{job['id']}/events").status_code in (403,404)

def test_viewer_cannot_mutate_or_see_output(owner):
    viewer,_=account(owner,'viewer@example.com',role='viewer',wid=owner['wid'])
    assert call(viewer,'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'illegal','scopes':['jobs:read']}).status_code==403
    job=submit(owner).json()['job'];finish(owner)
    result=viewer.get(f"/api/console/v1/projects/{owner['pid']}/jobs/{job['id']}").json();assert 'result' not in result['job']
    assert viewer.get(f"/api/console/v1/workspaces/{owner['wid']}/billing").status_code==403

def test_billing_role_cannot_read_jobs(owner):
    billing,_=account(owner,'billing@example.com',role='billing',wid=owner['wid'])
    assert billing.get(f"/api/console/v1/workspaces/{owner['wid']}/billing").status_code==200
    assert billing.get(f"/api/console/v1/projects/{owner['pid']}/jobs").status_code==403

def test_api_key_scopes_revocation_and_environment(owner):
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}/keys"
    key=call(c,'post',base,json={'label':'read only','scopes':['jobs:read']}).json()['secret'];headers={'Authorization':'Bearer '+key,'Idempotency-Key':'via-api'}
    assert c.post('/v1/jobs',json={'data':[]},headers=headers).status_code==403
    created=call(c,'post',base,json={'label':'writer','scopes':['jobs:read','jobs:write']}).json();headers['Authorization']='Bearer '+created['secret']
    r=c.post('/v1/jobs',json={'operation':'normalize','data':[{'name':' X '}]},headers=headers);assert r.status_code==202,r.text
    assert r.json()['job']['environment']=='test'
    assert 'secret' not in c.get(base).text
    assert call(c,'delete',base+'/'+created['id']).status_code==200
    assert c.get('/v1/jobs/'+r.json()['job']['id'],headers=headers).status_code==401

def test_live_key_rejected_before_activation(owner):
    r=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'live','scopes':['jobs:read'],'environment':'live'})
    assert r.json()['code']=='LIVE_UNAVAILABLE'

def test_workflow_versions_immutable_and_draft_conflict(owner):
    c=owner['client'];base=f"/api/console/v1/projects/{owner['pid']}/workflows"
    created=call(c,'post',base,json={'name':'Clean records','graph':graph()}).json();fid=created['id']
    published=call(c,'post',base+'/'+fid+'/publish');assert published.status_code==200,published.text
    modified=graph();modified['nodes'][1]['data']['config']={}
    saved=call(c,'patch',base+'/'+fid,json={'name':'Updated','graph':modified,'revision':1});assert saved.status_code==200
    assert call(c,'patch',base+'/'+fid,json={'name':'Old save','graph':graph(),'revision':1}).status_code==409
    result=submit(owner,{'operation':'workflow','workflow_id':fid,'data':[{'email':' A@EXAMPLE.TEST '}]}).json();assert 'job' in result,result
    finish(owner);assert read_job(owner,result['job']['id']).json()['job']['result']['output'][0]['email']=='a@example.test'

@pytest.mark.parametrize('mutate',[lambda g:g['edges'].append({'source':'output','target':'input'}),lambda g:g['nodes'][1]['data'].update(kind='python'),lambda g:g['nodes'].append(g['nodes'][0]),lambda g:g['edges'].clear(),lambda g:g['nodes'][0]['data'].update(format='csv')])
def test_graph_security(mutate):
    g=graph();mutate(g)
    with pytest.raises(PublicError):validate_graph(g)

def test_worker_recovery_and_fencing(owner):
    job=submit(owner).json()['job'];jobid,fence=claim(owner['db'],owner['settings'])
    with owner['db'].session() as db:db.get(Job,jobid).lease_until=now()-1;db.commit()
    assert recover_expired(owner['db'],owner['settings'])==1
    with pytest.raises(PublicError):event(owner['db'],jobid,fence,'node.completed',{})
    assert finish(owner);assert read_job(owner,jobid).json()['job']['state']=='succeeded'
