from dataclasses import dataclass
from sqlalchemy import select
from modules.identity.public import User, LoginSession
from modules.tenancy.public import Membership, Workspace
from modules.projects.public import Project
from modules.api_credentials.public import ApiKey
from foundation.clock import now
from foundation.crypto.security import digest, keyed_digest
from foundation.errors.public import PublicError
from foundation.database.session import tenant_context

PERMISSIONS={
 'owner':{'read','build','keys','files','finance','team','security','privacy'},
 'admin':{'read','build','keys','files','finance','team','security','privacy'},
 'developer':{'read','build','keys','files'},
 'billing':{'read','finance'},
 'viewer':{'read'},
}

def current_user(request,db,audience='console'):
    settings=request.app.state.settings
    value=request.cookies.get(settings.cookie(audience),'')
    session=db.get(LoginSession,digest(value)) if value else None
    if not session or session.audience!=audience or session.expires_at<now(): raise PublicError('UNAUTHORIZED')
    user=db.get(User,session.user_id)
    if not user or user.disabled: raise PublicError('UNAUTHORIZED')
    if audience=='operator' and (not user.staff or not session.mfa): raise PublicError('FORBIDDEN')
    if not user.verified: raise PublicError('EMAIL_UNVERIFIED')
    return user,session

def workspace_access(db,wid,user,permission='read'):
    membership=db.scalar(select(Membership).where(Membership.workspace_id==wid,Membership.user_id==user.id))
    if not membership: raise PublicError('NOT_FOUND')
    if permission not in PERMISSIONS.get(membership.role,set()): raise PublicError('FORBIDDEN')
    tenant_context(db,wid)
    workspace=db.get(Workspace,wid)
    if not workspace: raise PublicError('NOT_FOUND')
    if workspace.status!='active' and permission not in {'finance','read','privacy'}: raise PublicError('FORBIDDEN')
    return workspace,membership

def project_access(db,pid,user,permission='read'):
    project=db.get(Project,pid)
    if not project: raise PublicError('NOT_FOUND')
    workspace,membership=workspace_access(db,project.workspace_id,user,permission)
    if project.archived and permission in {'build','keys','files'}: raise PublicError('CONFLICT')
    return project,workspace,membership

def require_live(settings,user,session):
    if not settings.live_enabled: raise PublicError('LIVE_UNAVAILABLE')
    if not user.totp_secret or not session.mfa: raise PublicError('MFA_REQUIRED')

@dataclass
class ApiIdentity:
    project:Project
    key:ApiKey
    workspace:Workspace

def api_identity(request,db,scope):
    value=request.headers.get('authorization','')
    if not value.startswith('Bearer arc_'): raise PublicError('UNAUTHORIZED')
    raw=value[7:]
    key=db.scalar(select(ApiKey).where(ApiKey.digest==keyed_digest(raw,request.app.state.settings.secret_key)))
    if not key or key.revoked_at or key.expires_at<now(): raise PublicError('UNAUTHORIZED')
    if scope not in key.scopes: raise PublicError('FORBIDDEN')
    tenant_context(db,key.workspace_id)
    project=db.get(Project,key.project_id);workspace=db.get(Workspace,key.workspace_id)
    if not project or project.archived or workspace.status!='active': raise PublicError('FORBIDDEN')
    if key.environment=='live' and not request.app.state.settings.live_enabled: raise PublicError('LIVE_UNAVAILABLE')
    # Operational last-seen telemetry is supplied by indexed request logs. Do not
    # lock this one credential row on every read or long-lived stream.
    return ApiIdentity(project,key,workspace)
