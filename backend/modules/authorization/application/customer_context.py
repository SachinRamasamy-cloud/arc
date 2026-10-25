"""Customer API context; app-layer authorization and project views."""
from foundation.errors.public import PublicError
from modules.authorization.application.access import current_user, require_live
def actor(request,db): return current_user(request,db)[0]


def env_guard(request,db,user,env):
    if env not in ('test','live'): raise PublicError('INVALID_INPUT')
    if env=='live': require_live(request.app.state.settings,user,current_user(request,db)[1])


def project_view(project):
    return {k:getattr(project,k) for k in ('id','workspace_id','name','description','archived','rpm','concurrency','monthly_cap_milli','retention_hours','created_at')}

