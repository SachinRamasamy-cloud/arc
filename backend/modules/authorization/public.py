"""Cross-domain authorization interface."""
from .application.access import current_user, workspace_access, project_access, require_live, api_identity
from .application.customer_context import actor,env_guard,project_view
from .application.staff_context import staff
