import base64,hashlib,hmac,json,secrets,socket,time
import pytest
from arc.security import *
from arc.errors import PublicError
from arc.config import Settings
from arc.limits import Limiter,StreamGate
from conftest import call,account,PASSWORD

@pytest.mark.parametrize('password',['','short','x'*129])
def test_password_boundaries(password):
    with pytest.raises(PublicError): password_hash(password)

def test_password_hash_is_not_reversible_and_verifies():
    value=password_hash(PASSWORD)
    assert value.startswith('$argon2id$') and PASSWORD not in value
    assert password_matches(value,PASSWORD)
    assert not password_matches(value,'incorrect')
    assert not password_matches(None,'incorrect')

def test_rfc6238_vector():
    secret=base64.b32encode(b'12345678901234567890').decode()
    assert totp_code(secret,59,digits=8)=='94287082'
    assert totp_step(secret,totp_code(secret,90),last=3,at=90) is None

def test_encrypted_context_and_tamper(ctx):
    encrypted=seal('private-value',ctx['settings'],'totp')
    assert 'private-value' not in encrypted
    assert unseal(encrypted,ctx['settings'],'totp')=='private-value'
    with pytest.raises(PublicError): unseal(encrypted,ctx['settings'],'webhook')
    with pytest.raises(PublicError): unseal(encrypted[:-3]+'abc',ctx['settings'],'totp')

def test_signed_tokens_expire_and_are_scoped(ctx):
    value=signed_token({'purpose':'upload','exp':int(time.time())+30,'id':'a'},ctx['settings'])
    assert verify_signed(value,ctx['settings'],'upload')['id']=='a'
    for bad,purpose in [(value+'x','upload'),(value,'download'),(signed_token({'purpose':'upload','exp':1},ctx['settings']),'upload')]:
        with pytest.raises(PublicError): verify_signed(bad,ctx['settings'],purpose)

@pytest.mark.parametrize('url',['http://example.com','https://user:pass@example.com','https://example.com:444','https://example.com/#x','file:///etc/passwd','https://127.0.0.1','https://169.254.169.254','https://[::1]'])
def test_unsafe_webhooks_blocked(url):
    def resolver(host,port,**kw): return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(host if host in ('127.0.0.1','169.254.169.254','::1') else '93.184.216.34',port))]
    with pytest.raises(PublicError): validate_webhook_url(url,resolver=resolver)

def test_public_webhook_and_mixed_dns():
    parts,ips=validate_webhook_url('https://example.com/hook',resolver=lambda *a,**k:[(2,1,6,'',('93.184.216.34',443))])
    assert ips==['93.184.216.34']
    with pytest.raises(PublicError): validate_webhook_url('https://example.com',resolver=lambda *a,**k:[(2,1,6,'',('10.0.0.1',443)),(2,1,6,'',('93.184.216.34',443))])

def test_limiter_checks_all_before_consuming(ctx):
    limiter=Limiter(ctx['settings'])
    limiter.check([('parent',2),('child',1)],clock=0)
    with pytest.raises(PublicError): limiter.check([('parent',2),('child',1)],clock=1)
    assert limiter.buckets['parent'][0]==1
    limiter.check([('parent',2),('other',1)],clock=1)
    with pytest.raises(PublicError): limiter.check([('parent',2)],clock=2)
    limiter.check([('parent',2)],clock=61)

def test_stream_slot_released(ctx):
    gate=StreamGate(Limiter(ctx['settings']));gate.acquire('w','a',1)
    with pytest.raises(PublicError):gate.acquire('w','b',1)
    gate.release('w','a');gate.acquire('w','b',1)

def test_missing_csrf_and_wrong_origin(owner):
    c=owner['client']
    assert c.post('/api/console/v1/workspaces',json={'name':'Bad'}).json()['code']=='CSRF_FAILED'
    assert call(c,'post','/api/console/v1/workspaces',json={'name':'Bad'},headers={'Origin':'https://evil.example'}).json()['code']=='ORIGIN_BLOCKED'

def test_validation_does_not_echo_password(ctx):
    c=ctx['client'];secret='secret-sentinel'
    response=call(c,'post','/api/console/v1/auth/signup',json={'email':'invalid','name':'x','password':secret,'accept_terms':True,'connection':'postgres://secret'})
    assert response.status_code==422
    assert secret not in response.text and 'postgres://' not in response.text

def test_unknown_error_sanitized(ctx):
    @ctx['app'].get('/explode')
    def explode(): raise RuntimeError('postgresql://root:supersecret@private/db /home/operator/config')
    response=ctx['client'].get('/explode')
    assert response.status_code==500
    assert response.json()['code']=='INTERNAL_ERROR'
    assert 'supersecret' not in response.text and '/home' not in response.text

def test_redaction():
    raw='Bearer arc_live_abcdefghij sk_live_abcdefghij whsec_abcdefghij'
    value=redact_support(raw)
    assert 'abcdefghij' not in value

def test_production_fails_closed(ctx):
    data=ctx['settings'].model_dump();data['env']='production'
    with pytest.raises(ValueError,match='Production blocked'):Settings(_env_file=None,**data)
