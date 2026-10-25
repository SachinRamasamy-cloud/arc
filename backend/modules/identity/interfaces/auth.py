from fastapi import APIRouter,Request,Response,Depends
from sqlalchemy import select,update,delete
import base64,secrets,time
from urllib.parse import quote
from modules.identity.public import User, LoginSession, Token
from modules.tenancy.public import Membership, Workspace
from foundation.clock import now
from modules.identity.interfaces.schemas import Signup, Login, Email, TokenBody, Reset, Code, Preferences
from foundation.crypto.security import token, digest, password_hash, password_matches, csrf_token, seal, unseal, totp_step, keyed_digest
from modules.authorization.application.access import current_user
from modules.notifications.application.use_cases import queue_mail
from modules.audit.application.use_cases import audit
from foundation.errors.public import PublicError
from foundation.database.dependencies import db_session

def user_view(user):
    return {'id':user.id,'email':user.email,'name':user.name,'verified':user.verified,'mfa_enabled':bool(user.totp_secret),'preferences':user.preferences}

def issue_action(db,settings,user,purpose,path):
    raw=token()
    db.add(Token(id=digest(raw),user_id=user.id,purpose=purpose,payload={},expires_at=now()+(3600 if purpose=='reset' else 86400)))
    queue_mail(db,settings,user.email,'Reset your password' if purpose=='reset' else 'Verify your Arc account',settings.portal_origin+path+'?token='+raw+'\n\nThis link expires and can be used once. Do not share it.')

def consume_action(db,raw,purpose):
    action=db.get(Token,digest(raw))
    if not action or action.purpose!=purpose or action.consumed or action.expires_at<now(): raise PublicError('INVALID_TOKEN')
    claimed=db.execute(update(Token).where(Token.id==action.id,Token.consumed.is_(False),Token.expires_at>=now()).values(consumed=True))
    if claimed.rowcount!=1: raise PublicError('INVALID_TOKEN')
    return action

def verify_mfa(db,user,code,settings):
    if not user.totp_secret: return False
    secret=unseal(user.totp_secret,settings,'totp')
    step=totp_step(secret,code,user.last_totp_step)
    if step is not None:
        changed=db.execute(update(User).where(User.id==user.id,User.last_totp_step<step).values(last_totp_step=step))
        if changed.rowcount==1: return True
    recovery=keyed_digest(code,settings.secret_key)
    if recovery in (user.recovery_hashes or []):
        # Lock and re-read so recovery codes cannot be used twice by simultaneous requests.
        locked=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
        if recovery in locked.recovery_hashes:
            locked.recovery_hashes=[x for x in locked.recovery_hashes if x!=recovery]
            return True
    raise PublicError('INVALID_CODE')

def create_auth_router(audience='console'):
    router=APIRouter(prefix='/api/'+audience+'/v1/auth',tags=[audience+' identity'])
    @router.get('/csrf')
    def csrf(request:Request,response:Response):
        settings=request.app.state.settings
        value=csrf_token(settings,audience,request.cookies.get(settings.cookie(audience),''))
        response.set_cookie(settings.cookie(audience,'csrf'),value,secure=settings.secure_cookies,httponly=False,samesite='strict',max_age=3600,path='/')
        response.headers['Cache-Control']='no-store'
        return {'csrf_token':value}
    if audience=='console':
        @router.post('/signup',status_code=202)
        def signup(body:Signup,request:Request,db=Depends(db_session)):
            if not body.accept_terms: raise PublicError('INVALID_INPUT')
            settings=request.app.state.settings
            email=str(body.email).lower()
            request.app.state.limiter.check([('signup:'+request.state.client_hash,5)])
            existing=db.scalar(select(User).where(User.email==email))
            # Hash in both branches to reduce the easy account-enumeration timing difference.
            hashed=password_hash(body.password)
            if not existing:
                user=User(email=email,name=body.name.strip(),password_hash=hashed)
                db.add(user);db.flush();issue_action(db,settings,user,'verify','/verify-email');db.commit()
            return {'message':'Check your email for the next step.'}
        @router.post('/verify-email')
        def verify(body:TokenBody,db=Depends(db_session)):
            action=consume_action(db,body.token,'verify');user=db.get(User,action.user_id)
            if not user: raise PublicError('INVALID_TOKEN')
            user.verified=True;db.commit();return {'message':'Email verified. You can sign in.'}
        @router.post('/resend-verification',status_code=202)
        def resend(body:Email,request:Request,db=Depends(db_session)):
            request.app.state.limiter.check([('verify:'+request.state.client_hash,3)])
            user=db.scalar(select(User).where(User.email==str(body.email).lower()))
            if user and not user.verified: issue_action(db,request.app.state.settings,user,'verify','/verify-email');db.commit()
            return {'message':'Check your email for the next step.'}
        @router.post('/forgot-password',status_code=202)
        def forgot(body:Email,request:Request,db=Depends(db_session)):
            request.app.state.limiter.check([('reset:'+request.state.client_hash,3)])
            user=db.scalar(select(User).where(User.email==str(body.email).lower(),User.staff.is_(False)))
            if user and user.verified: issue_action(db,request.app.state.settings,user,'reset','/reset-password');db.commit()
            return {'message':'If an eligible account exists, a reset link has been sent.'}
        @router.post('/reset-password')
        def reset(body:Reset,request:Request,db=Depends(db_session)):
            action=consume_action(db,body.token,'reset');user=db.get(User,action.user_id)
            if not user: raise PublicError('INVALID_TOKEN')
            user.password_hash=password_hash(body.password)
            db.execute(delete(LoginSession).where(LoginSession.user_id==user.id))
            queue_mail(db,request.app.state.settings,user.email,'Your password was changed','Your sessions have been signed out. Contact support if you did not make this change.')
            db.commit();return {'message':'Password changed. Sign in again.'}
    @router.post('/login')
    def login(body:Login,request:Request,response:Response,db=Depends(db_session)):
        settings=request.app.state.settings
        key=keyed_digest(str(body.email).lower(),settings.secret_key)
        request.app.state.limiter.check([('loginip:'+request.state.client_hash,20),('loginuser:'+key,8)])
        user=db.scalar(select(User).where(User.email==str(body.email).lower()))
        valid=password_matches(user.password_hash if user else None,body.password)
        if not valid or not user or user.disabled or (audience=='operator' and not user.staff): raise PublicError('INVALID_CREDENTIALS')
        if not user.verified: raise PublicError('EMAIL_UNVERIFIED')
        if audience=='operator' and not user.totp_secret: raise PublicError('MFA_REQUIRED')
        if user.totp_secret and not body.code: raise PublicError('MFA_REQUIRED')
        mfa=verify_mfa(db,user,body.code,settings) if user.totp_secret else False
        raw=token();session=LoginSession(id=digest(raw),user_id=user.id,audience=audience,mfa=mfa,expires_at=now()+settings.session_seconds)
        old=request.cookies.get(settings.cookie(audience))
        if old: db.execute(delete(LoginSession).where(LoginSession.id==digest(old),LoginSession.audience==audience))
        db.add(session);audit(db,user.id,'session.created',session.id[:12]);db.commit()
        response.set_cookie(settings.cookie(audience),raw,max_age=settings.session_seconds,secure=settings.secure_cookies,httponly=True,samesite='lax',path='/')
        # Rotate and bind the CSRF token to the newly created session.
        csrf_value=csrf_token(settings,audience,raw)
        response.set_cookie(settings.cookie(audience,'csrf'),csrf_value,max_age=3600,secure=settings.secure_cookies,httponly=False,samesite='strict',path='/')
        return {'user':user_view(user),'csrf_token':csrf_value}
    @router.get('/me')
    def me(request:Request,db=Depends(db_session)):
        user,session=current_user(request,db,audience)
        return {'user':user_view(user),'mfa_verified':session.mfa,'audience':audience}
    @router.post('/logout')
    def logout(request:Request,response:Response,db=Depends(db_session)):
        user,session=current_user(request,db,audience)
        db.delete(session);db.commit()
        settings=request.app.state.settings
        response.delete_cookie(settings.cookie(audience),path='/');response.delete_cookie(settings.cookie(audience,'csrf'),path='/')
        return {'message':'Signed out.'}
    @router.get('/sessions')
    def sessions(request:Request,db=Depends(db_session)):
        user,current=current_user(request,db,audience)
        return {'items':[{'id':s.id,'created_at':s.created_at,'expires_at':s.expires_at,'current':s.id==current.id} for s in db.scalars(select(LoginSession).where(LoginSession.user_id==user.id,LoginSession.audience==audience,LoginSession.expires_at>now()))]}
    @router.delete('/sessions/{session_id}')
    def revoke_session(session_id:str,request:Request,db=Depends(db_session)):
        user,current=current_user(request,db,audience)
        target=db.scalar(select(LoginSession).where(LoginSession.id==session_id,LoginSession.user_id==user.id,LoginSession.audience==audience))
        if not target: raise PublicError('NOT_FOUND')
        db.delete(target);audit(db,user.id,'session.revoked',target.id[:12]);db.commit();return {'message':'Session revoked.'}
    @router.patch('/preferences')
    def preferences(body:Preferences,request:Request,db=Depends(db_session)):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        try: ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError: raise PublicError('INVALID_INPUT')
        user,session=current_user(request,db,audience);user.preferences=body.model_dump();db.commit();return user_view(user)
    if audience=='console':
        @router.post('/mfa/setup')
        def mfa_setup(request:Request,db=Depends(db_session)):
            user,session=current_user(request,db,audience)
            if user.totp_secret: raise PublicError('CONFLICT')
            secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
            user.totp_pending=seal(secret,request.app.state.settings,'totp');db.commit()
            return {'secret':secret,'uri':'otpauth://totp/Arc:'+quote(user.email)+'?secret='+secret+'&issuer=Arc','message':'Save the setup key in your authenticator, then enter its current code.'}
        @router.post('/mfa/confirm')
        def mfa_confirm(body:Code,request:Request,db=Depends(db_session)):
            user,session=current_user(request,db,audience);settings=request.app.state.settings
            if not user.totp_pending or user.totp_secret: raise PublicError('CONFLICT')
            secret=unseal(user.totp_pending,settings,'totp');step=totp_step(secret,body.code)
            if step is None: raise PublicError('INVALID_CODE')
            codes=[secrets.token_hex(8) for _ in range(8)]
            user.totp_secret=user.totp_pending;user.totp_pending=None;user.last_totp_step=step
            user.recovery_hashes=[keyed_digest(c,settings.secret_key) for c in codes];session.mfa=True
            audit(db,user.id,'mfa.enabled',user.id);db.commit()
            return {'recovery_codes':codes,'message':'Save these recovery codes. Each can be used once.'}
    return router
