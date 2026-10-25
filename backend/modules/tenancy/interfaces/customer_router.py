"""tenancy-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, func
from foundation.clock import now
from foundation.errors.public import PublicError
from foundation.crypto.security import token, digest
from modules.tenancy.interfaces.schemas import Invite, Name
from modules.identity.interfaces.schemas import TokenBody
from modules.executions.public import Job
from modules.tenancy.public import Membership, Workspace
from modules.identity.public import Token, User
from modules.projects.public import Project
from modules.wallets.public import Allowance, Wallet
from modules.identity.interfaces.auth import consume_action
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor, project_view
from modules.audit.application.use_cases import audit
from modules.notifications.application.use_cases import queue_mail
from modules.wallets.application.use_cases import wallet, wallet_dict, grant
from modules.executions.application.use_cases import public_job

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces')
def workspaces(request:Request,db=Depends(db_session)):
    user=actor(request,db)
    rows=db.execute(select(Workspace,Membership.role).join(Membership,Workspace.id==Membership.workspace_id).where(Membership.user_id==user.id).order_by(Workspace.created_at)).all()
    return {'items':[{'id':w.id,'name':w.name,'status':w.status,'role':role} for w,role in rows]}


@router.post('/workspaces',status_code=201)
def create_workspace(body:Name,request:Request,db=Depends(db_session)):
    user=actor(request,db)
    if db.scalar(select(func.count(Membership.id)).where(Membership.user_id==user.id))>=5: raise PublicError('POLICY_LIMIT')
    workspace=Workspace(name=body.name.strip());db.add(workspace);db.flush()
    db.add(Membership(workspace_id=workspace.id,user_id=user.id,role='owner'))
    db.add_all([Wallet(workspace_id=workspace.id,environment='test'),Wallet(workspace_id=workspace.id,environment='live')]);db.flush()
    grant(db,workspace.id,'test',100_000,'sandbox:'+workspace.id,'Test credits — no cash value')
    audit(db,user.id,'workspace.created',workspace.id,workspace.id);db.commit()
    return {'id':workspace.id,'name':workspace.name,'role':'owner','status':workspace.status}


@router.patch('/workspaces/{wid}')
def rename_workspace(wid:str,body:Name,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace,member=workspace_access(db,wid,user,'team');workspace.name=body.name.strip()
    audit(db,user.id,'workspace.renamed',wid,wid);db.commit();return {'id':wid,'name':workspace.name}


@router.get('/workspaces/{wid}/overview')
def overview(wid:str,request:Request,environment:str='test',db=Depends(db_session)):
    user=actor(request,db);workspace,member=workspace_access(db,wid,user)
    if environment not in ('test','live'): raise PublicError('INVALID_INPUT')
    jobs=list(db.scalars(select(Job).where(Job.workspace_id==wid,Job.environment==environment).order_by(Job.created_at.desc()).limit(8)))
    totals=dict(db.execute(select(Job.state,func.count(Job.id)).where(Job.workspace_id==wid,Job.environment==environment).group_by(Job.state)).all())
    projects=list(db.scalars(select(Project).where(Project.workspace_id==wid,Project.archived.is_(False)).order_by(Project.created_at)))
    credit=wallet_dict(wallet(db,wid,environment)) if member.role in ('owner','admin','billing') else None
    if credit:
        credit['included_available_milli']=int(db.scalar(select(func.coalesce(func.sum(Allowance.balance_milli-Allowance.held_milli),0)).where(Allowance.workspace_id==wid,Allowance.expires_at>now())) or 0) if environment=='live' else 0
    return {'workspace':{'id':wid,'name':workspace.name,'role':member.role,'status':workspace.status},'environment':environment,'projects':[project_view(p) for p in projects],
            'totals':totals,'recent_jobs':[public_job(j) for j in jobs[:8]],'wallet':credit,'last_updated':now(),
            'latency_ms':{'p50':None,'p95':None,'p99':None},'onboarding':{'workspace':True,'project':bool(projects),'first_success':totals.get('succeeded',0)>0,'mfa':bool(user.totp_secret)}}


@router.get('/workspaces/{wid}/members')
def members(wid:str,request:Request,db=Depends(db_session)):
    workspace_access(db,wid,actor(request,db),'team')
    rows=db.execute(select(Membership,User).join(User,Membership.user_id==User.id).where(Membership.workspace_id==wid)).all()
    invites=list(db.scalars(select(Token).where(Token.purpose=='invite',Token.consumed.is_(False),Token.expires_at>now())))
    return {'items':[{'id':m.id,'user_id':u.id,'email':u.email,'name':u.name,'role':m.role} for m,u in rows], 'invites':[{'id':t.id[:12],'email':t.payload['email'],'role':t.payload['role'],'expires_at':t.expires_at} for t in invites if t.payload.get('workspace_id')==wid]}


@router.post('/workspaces/{wid}/members/invite',status_code=202)
def invite(wid:str,body:Invite,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace,member=workspace_access(db,wid,user,'team')
    if member.role!='owner' and body.role=='admin': raise PublicError('FORBIDDEN')
    email=str(body.email).lower();raw=token()
    db.add(Token(id=digest(raw),purpose='invite',payload={'workspace_id':wid,'email':email,'role':body.role},expires_at=now()+7*86400))
    queue_mail(db,request.app.state.settings,email,'You are invited to '+workspace.name,request.app.state.settings.portal_origin+'/accept-invite?token='+raw)
    audit(db,user.id,'member.invited',wid,wid);db.commit();return {'message':'Invitation sent.'}


@router.post('/invitations/accept')
def accept_invite(body:TokenBody,request:Request,db=Depends(db_session)):
    user=actor(request,db);action=consume_action(db,body.token,'invite')
    if action.payload.get('email')!=user.email: raise PublicError('FORBIDDEN')
    wid=action.payload['workspace_id']
    if db.scalar(select(Membership).where(Membership.workspace_id==wid,Membership.user_id==user.id)): raise PublicError('CONFLICT')
    db.add(Membership(workspace_id=wid,user_id=user.id,role=action.payload['role']));audit(db,user.id,'member.joined',wid,wid);db.commit();return {'workspace_id':wid}


@router.delete('/workspaces/{wid}/members/{mid}')
def remove_member(wid:str,mid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace,own=workspace_access(db,wid,user,'team')
    member=db.scalar(select(Membership).where(Membership.id==mid,Membership.workspace_id==wid))
    if not member: raise PublicError('NOT_FOUND')
    if member.role=='owner' or (member.role=='admin' and own.role!='owner'): raise PublicError('FORBIDDEN')
    db.delete(member);audit(db,user.id,'member.removed',mid,wid);db.commit();return {'message':'Member removed.'}

