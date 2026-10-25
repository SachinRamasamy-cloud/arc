from pathlib import Path
import secrets
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from arc.config import Settings
from arc.db import Database
from arc.main import create_app
from arc.models import User,Token,Membership,Workspace,Wallet,now
from arc.security import password_hash,token,digest

ROOT=Path(__file__).resolve().parents[2]
PASSWORD='a-test-only-password-123'

@pytest.fixture
def ctx(tmp_path):
    settings=Settings(_env_file=None,env='test',database_url='sqlite:///'+str(tmp_path/'db.sqlite'),secret_key=secrets.token_urlsafe(48),encryption_key=Fernet.generate_key().decode(),storage_dir=str(tmp_path/'objects'),native_path=str(ROOT/'native/build/arc-engine'))
    database=Database(settings.database_url);database.create_test_schema();app=create_app(settings,database)
    client=TestClient(app,raise_server_exceptions=False)
    yield {'settings':settings,'db':database,'app':app,'client':client}
    client.close();database.engine.dispose()

def csrf(client,audience='console'):
    return {'X-CSRF-Token':client.get('/api/'+audience+'/v1/auth/csrf').json()['csrf_token']}

def call(client,method,path,**kwargs):
    audience='operator' if path.startswith('/api/operator') else 'console'
    headers={**csrf(client,audience),**kwargs.pop('headers',{})}
    return getattr(client,method)(path,headers=headers,**kwargs)

def account(ctx,email='owner@example.com',role='owner',wid=None,staff=False,totp=None):
    with ctx['db'].session() as db:
        user=User(email=email,name='Test Developer',password_hash=password_hash(PASSWORD),verified=True,staff=staff,totp_secret=totp)
        db.add(user);db.flush();uid=user.id
        if wid: db.add(Membership(workspace_id=wid,user_id=uid,role=role))
        db.commit()
    client=TestClient(ctx['app'],raise_server_exceptions=False)
    if not staff:
        response=call(client,'post','/api/console/v1/auth/login',json={'email':email,'password':PASSWORD})
        assert response.status_code==200,response.text
    return client,uid

@pytest.fixture
def owner(ctx):
    client,uid=account(ctx)
    r=call(client,'post','/api/console/v1/workspaces',json={'name':'Test workspace'});assert r.status_code==201,r.text
    wid=r.json()['id']
    r=call(client,'post',f'/api/console/v1/workspaces/{wid}/projects',json={'name':'Test API'});assert r.status_code==201,r.text
    return {**ctx,'client':client,'user_id':uid,'wid':wid,'pid':r.json()['id']}
