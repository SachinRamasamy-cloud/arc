import re
from sqlalchemy import select
from arc.models import Mail,User,Token
from arc.security import unseal
from conftest import call,PASSWORD

def action(ctx,subject):
    with ctx['db'].session() as db:
        message=db.scalar(select(Mail).where(Mail.subject==subject).order_by(Mail.created_at.desc()))
        return re.search(r'token=([A-Za-z0-9_-]+)',unseal(message.body_encrypted,ctx['settings'],'mail')).group(1)

def test_signup_verify_login_single_use(ctx):
    c=ctx['client'];body={'email':'new@example.com','name':'New developer','password':PASSWORD,'accept_terms':True}
    assert call(c,'post','/api/console/v1/auth/signup',json=body).status_code==202
    r=call(c,'post','/api/console/v1/auth/login',json={'email':body['email'],'password':PASSWORD});assert r.json()['code']=='EMAIL_UNVERIFIED'
    token=action(ctx,'Verify your Arc account')
    assert call(c,'post','/api/console/v1/auth/verify-email',json={'token':token}).status_code==200
    assert call(c,'post','/api/console/v1/auth/verify-email',json={'token':token}).status_code==400
    assert call(c,'post','/api/console/v1/auth/login',json={'email':body['email'],'password':PASSWORD}).status_code==200
    assert c.get('/api/console/v1/auth/me').json()['user']['verified']

def test_password_reset_revokes_sessions(owner):
    c=owner['client'];new_password='new-test-only-password-543'
    assert call(c,'post','/api/console/v1/auth/forgot-password',json={'email':'owner@example.com'}).status_code==202
    token=action(owner,'Reset your password')
    assert call(c,'post','/api/console/v1/auth/reset-password',json={'token':token,'password':new_password}).status_code==200
    assert c.get('/api/console/v1/auth/me').status_code==401
    assert call(c,'post','/api/console/v1/auth/reset-password',json={'token':token,'password':new_password}).status_code==400
    assert call(c,'post','/api/console/v1/auth/login',json={'email':'owner@example.com','password':PASSWORD}).status_code==401
    assert call(c,'post','/api/console/v1/auth/login',json={'email':'owner@example.com','password':new_password}).status_code==200

def test_signup_existing_and_unknown_reset_do_not_reveal_accounts(owner):
    c=owner['client'];body={'email':'owner@example.com','name':'Someone','password':PASSWORD,'accept_terms':True}
    assert call(c,'post','/api/console/v1/auth/signup',json=body).json()=={'message':'Check your email for the next step.'}
    missing=call(c,'post','/api/console/v1/auth/forgot-password',json={'email':'missing@example.com'}).json()
    known=call(c,'post','/api/console/v1/auth/forgot-password',json={'email':'owner@example.com'}).json()
    assert missing==known

def test_timezone_validation(owner):
    good=call(owner['client'],'patch','/api/console/v1/auth/preferences',json={'timezone':'Asia/Kolkata'})
    assert good.status_code==200
    bad=call(owner['client'],'patch','/api/console/v1/auth/preferences',json={'timezone':'private/path'})
    assert bad.status_code==422
