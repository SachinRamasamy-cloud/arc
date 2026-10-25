from foundation.errors.public import PublicError
from modules.authorization.application.access import api_identity
def identify(request,db,scope):
    identity=api_identity(request,db,scope)
    request.state.key_id=identity.key.id
    request.state.workspace_id=identity.workspace.id;request.state.project_id=identity.project.id;request.state.environment=identity.key.environment
    return identity

