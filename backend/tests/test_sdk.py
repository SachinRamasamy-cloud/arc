import sys,json,hmac,hashlib
from pathlib import Path
import httpx,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'sdk/python'))
from arc_client import ArcClient,ArcAPIError,verify_webhook
from conftest import call
from arc.worker import process_one

def test_sdk_real_processing(owner):
    key=call(owner['client'],'post',f"/api/console/v1/projects/{owner['pid']}/keys",json={'label':'SDK','scopes':['jobs:write','jobs:read']}).json()['secret']
    def route(request):
        response=owner['client'].request(request.method,str(request.url),content=request.content,headers=dict(request.headers))
        return httpx.Response(response.status_code,content=response.content,headers=response.headers)
    with ArcClient('http://testserver',key,transport=httpx.MockTransport(route)) as sdk:
        first=sdk.run(operation='normalize',data=[{'email':' A@EXAMPLE.TEST '}],lowercase=['email'],idempotency_key='sdk-real')
        again=sdk.run(operation='normalize',data=[{'email':' A@EXAMPLE.TEST '}],lowercase=['email'],idempotency_key='sdk-real')
        assert first['job']['id']==again['job']['id']
        assert process_one(owner['db'],owner['settings'],owner['app'].state.store)
        result=sdk.wait(first['job']['id'],timeout=2)
        assert result['job']['state']=='succeeded'
        assert 'a@example.test' in json.dumps(result)
        with pytest.raises(ValueError):sdk.wait(first['job']['id'],interval=0)
        with pytest.raises(ValueError):sdk.job('../other-tenant')
        with pytest.raises(ValueError):sdk.run(operation='validate',data=[],idempotency_key='')

def test_sdk_safe_errors():
    def response(_):return httpx.Response(500,json={'code':'/secret/db-password','detail':'postgres://secret'})
    with ArcClient('https://api.example.test','test',transport=httpx.MockTransport(response)) as sdk:
        with pytest.raises(ArcAPIError) as exc:sdk.job('run_123')
        assert exc.value.code=='INTERNAL_ERROR' and 'postgres' not in str(exc.value)
    with pytest.raises(ValueError):ArcClient('https://api.example.test','')

def test_sdk_signature():
    raw=b'{"id":"evt_123","type":"job.succeeded"}';stamp=1000;secret='private'
    signature='t=1000,v1='+hmac.new(secret.encode(),b'1000.'+raw,hashlib.sha256).hexdigest()
    assert verify_webhook(raw,signature,secret,clock=stamp)['id']=='evt_123'
    for body,header,clock in [(raw+b' ',signature,stamp),(raw,signature,1400),(raw,'bad',stamp)]:
        with pytest.raises(ValueError):verify_webhook(body,header,secret,clock=clock)
