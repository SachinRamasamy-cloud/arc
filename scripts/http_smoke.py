"""Exercise a fresh migrated database and real HTTP/native execution without mocks.
No user data is modified. Prints no passwords, API keys, payload tokens or signed URLs.
"""
from pathlib import Path
import json,os,socket,subprocess,sys,tempfile,time,hashlib
import httpx
ROOT=Path(__file__).resolve().parents[1]

def main():
    from cryptography.fernet import Fernet
    import secrets
    with tempfile.TemporaryDirectory(prefix='arc-http-smoke-') as folder:
        with socket.socket() as candidate:
            candidate.bind(('127.0.0.1',0));port=candidate.getsockname()[1]
        origin=f'http://127.0.0.1:{port}'
        env={**os.environ,'PYTHONPATH':str(ROOT/'backend/src'),'ARC_ENV':'test','ARC_DATABASE_URL':'sqlite:///'+folder+'/db.sqlite','ARC_SECRET_KEY':secrets.token_urlsafe(48),'ARC_ENCRYPTION_KEY':Fernet.generate_key().decode(),'ARC_API_ORIGIN':origin,'ARC_NATIVE_PATH':str(ROOT/'native/build/arc-engine'),'ARC_STORAGE_MODE':'local','ARC_STORAGE_DIR':folder+'/objects','ARC_MAIL_MODE':'local','ARC_REDIS_URL':'','ARC_LIVE_ENABLED':'false'}
        def run(*args):return subprocess.run([sys.executable,*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30,check=True)
        run('-m','arc.cli','migrate')
        output=run('-m','arc.cli','demo','--email','smoke@example.com').stdout
        password=output.split('Generated password: ',1)[1].splitlines()[0].strip()
        with open(Path(folder)/'server.log','w') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','arc.main:development','--factory','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=origin,timeout=20) as client:
                    for _ in range(80):
                        try:
                            if client.get('/health/ready').status_code==200:break
                        except httpx.TransportError:pass
                        if process.poll() is not None:raise RuntimeError('Smoke API stopped before readiness.')
                        time.sleep(.1)
                    else:raise RuntimeError('Smoke API did not become ready.')
                    def post(path,body):
                        csrf=client.get('/api/console/v1/auth/csrf').json()['csrf_token']
                        response=client.post(path,json=body,headers={'X-CSRF-Token':csrf});response.raise_for_status();return response.json()
                    post('/api/console/v1/auth/login',{'email':'smoke@example.com','password':password})
                    workspaces=client.get('/api/console/v1/workspaces').json()['items'];wid=workspaces[0]['id']
                    pid=client.get('/api/console/v1/workspaces/'+wid+'/projects').json()['items'][0]['id']
                    key=post('/api/console/v1/projects/'+pid+'/keys',{'label':'Smoke','scopes':['jobs:read','jobs:write','files:write','files:read','data:read','data:write']})['secret']
                    headers={'Authorization':'Bearer '+key,'Idempotency-Key':'http-smoke-op'}
                    payload={'operation':'normalize','data':[{'email':' ADA@EXAMPLE.TEST '}],'lowercase':['email']}
                    submitted=client.post('/v1/jobs',json=payload,headers=headers);submitted.raise_for_status();jid=submitted.json()['job']['id']
                    second=client.post('/v1/jobs',json=payload,headers=headers);assert second.json()['job']['id']==jid
                    run('-c','from arc.config import Settings; from arc.db import Database; from arc.storage import ObjectStore; from arc.worker import process_one; s=Settings(); assert process_one(Database(s.database_url),s,ObjectStore(s))')
                    response=client.get('/v1/jobs/'+jid,headers=headers);response.raise_for_status();job=response.json()['job']
                    assert job['state']=='succeeded' and job['result']['output'][0]['email']=='ada@example.test'
                    assert job['charged_milli']>0
                    stream=client.get('/v1/jobs/'+jid+'/events',headers=headers);assert stream.status_code==200 and 'job.succeeded' in stream.text and 'stream.complete' in stream.text
                    assert client.get('/api/operator/v1/customers').status_code==401
                    data=client.get('/api/console/v1/workspaces/'+wid+'/billing').json()
                    wallet=next(w for w in data['wallets'] if w['environment']=='test')
                    assert wallet['balance_milli']==100_000-job['charged_milli'] and wallet['reserved_milli']==0
                    assert client.get('/v1/jobs/'+jid).status_code==401
                    # A different HTTP client has no console cookies; it represents
                    # the customer's backend consuming the public API.
                    with httpx.Client(base_url=origin,timeout=20) as external:
                        record_headers={'Authorization':'Bearer '+key,'Idempotency-Key':'record-over-http'}
                        created=external.put('/v1/data/contacts/alex',json={'data':{'name':'Alex'},'expected_version':0},headers=record_headers);created.raise_for_status()
                        repeat=external.put('/v1/data/contacts/alex',json={'data':{'name':'Alex'},'expected_version':0},headers=record_headers);assert repeat.json()['applied'] is False
                        read=external.get('/v1/data/contacts/alex',headers=record_headers);assert read.json()['record']['data']=={'name':'Alex'}
                        raw=b'column\nactual-upload\n'
                        auth=external.post('/v1/files',json={'name':'data.csv','content_type':'text/csv','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'purpose':'storage','retention_hours':168},headers=record_headers);auth.raise_for_status();upload=auth.json();fid=upload['file']['id']
                        transferred=external.put(upload['upload_url'],content=raw,headers=upload['headers']);transferred.raise_for_status()
                        ready=external.post('/v1/files/'+fid+'/complete',headers=record_headers);assert ready.json()['state']=='ready'
                        url=external.get('/v1/files/'+fid+'/download',headers=record_headers).json()['url']
                        assert external.get(url).content==raw
                        deleted=external.delete('/v1/files/'+fid,headers=record_headers);assert deleted.json()['state']=='deleted'
                        assert external.get('/v1/files/'+fid+'/download',headers=record_headers).status_code==404
                        record_headers['Idempotency-Key']='record-delete'
                        assert external.delete('/v1/data/contacts/alex?expected_version=1',headers=record_headers).status_code==200
                    bill=client.get('/api/console/v1/workspaces/'+wid+'/billing?environment=test').json()
                    assert bill['usage']['gross_milli']==job['charged_milli']+2
                    assert bill['usage']['included_milli']==0 and bill['usage']['prepaid_milli']==bill['usage']['gross_milli']
                    assert next(w for w in bill['wallets'] if w['environment']=='test')['balance_milli']==100_000-bill['usage']['gross_milli']
                    report=json.loads(run('-m','arc.cli','reconcile','--workspace',wid).stdout);assert report['balanced']

                    print(json.dumps({'status':'passed','database':'fresh SQLite via Alembic revisions 0001–0003','transport':'real loopback HTTP','native_engine':'actual compiled C++ process','checks':['migration','generated-account login','workspace/project discovery','scoped key creation','authenticated job submission','idempotency','native normalization','credit settlement','SSE terminal replay','staff isolation','unauthenticated denial','independent cookie-free API consumer','encrypted-record CRUD and idempotency','direct local-adapter upload/download/delete','monthly usage matches wallet','accounting reconciliation'],'result':{'email':'ada@example.test'},'limitations':['Not a browser/React test.','Not PostgreSQL/Redis/R2/Stripe qualification.']},indent=2))
            finally:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
